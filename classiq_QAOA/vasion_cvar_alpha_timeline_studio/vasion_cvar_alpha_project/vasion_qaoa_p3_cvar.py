#!/usr/bin/env python3
"""Noise-free CVaR-QAOA and known-target diagnostics for Vasion's 20 industries.

Run this script FROM THE SAME FOLDER as:
    vasion_classiq_qaoa_p3.py
    paper_phase_transition_baseline.py
    paper_phase_transition_20_industries.json

The existing Classiq p=3 QAOA circuit is never modified. For efficiency, SciPy
optimizes a local, *exact* 20-qubit statevector implementing the same cost/mixer
unitaries; the chosen angles are then independently tested by Classiq's SDK.

Commands:
    python -m pip install numpy scipy numba networkx classiq
    python vasion_qaoa_p3_cvar.py --year 2036 --mode cvar --restarts 2 --maxiter 100
    python vasion_qaoa_p3_cvar.py --year 2036 --mode target --restarts 2 --maxiter 100
    python vasion_qaoa_p3_cvar.py --year 2036 --mode both --restarts 2 --maxiter 100

Use --no-classiq to test the exact local simulator without launching Classiq.
CVaR is an Ising optimization method; target mode is *only a diagnostic* because
it explicitly tells the optimizer which output state it should amplify.
"""

import argparse
import csv
import json
import time
from pathlib import Path

import numpy as np
from numba import njit
from scipy.optimize import minimize
from paper_phase_transition_baseline import exact_ground_state

HERE = Path(__file__).resolve().parent
MODEL = HERE / "paper_phase_transition_20_industries.json"
N = 20
DIM = 1 << N
ANGLE_NAMES = ("gamma_1", "beta_1", "gamma_2", "beta_2", "gamma_3", "beta_3")

# The successfully verified p=3 angles from the earlier 2036 Classiq execution.
WARM_START = np.array([
    0.89815319, -0.84974349,
    1.18466274, -0.38947824,
    1.44434939, -0.23416914,
], dtype=np.float64)


def build_ising_energies(year: int) -> np.ndarray:
    """Exact diagonal of H_C, indexed by sum(bit_i * 2**i)."""
    model = json.loads(MODEL.read_text(encoding="utf-8"))
    industries = model["industries"]
    edges = model["edges"]
    assert len(industries) == N and len(edges) == 24, "Incorrect industry network"
    pressure = 0.07 * (year - 2026)
    indices = np.arange(DIM, dtype=np.uint32)
    energies = np.zeros(DIM, dtype=np.float64)
    for item in industries:
        bit = ((indices >> np.uint32(item["id"])) & 1).astype(np.int8)
        spin = 2 * bit - 1  # paper=-1, digital=+1
        energies -= (pressure - float(item["resistance"])) * spin
    for edge in edges:
        bit_i = ((indices >> np.uint32(edge["i"])) & 1).astype(np.int8)
        bit_j = ((indices >> np.uint32(edge["j"])) & 1).astype(np.int8)
        spin_i = 2 * bit_i - 1
        spin_j = 2 * bit_j - 1
        energies -= float(edge["J"]) * spin_i * spin_j
    return energies


@njit(cache=True)
def evolve_qaoa(energies: np.ndarray, angles: np.ndarray) -> np.ndarray:
    """Exact state after 3 cost/mixer layers, no sampling noise.

    Cost: exp(-i gamma * H_C) for diagonal H_C.
    Mixer: exp(-i beta * sum X_i), i.e. RX(2*beta) on each qubit.
    """
    size = energies.size
    state = np.empty(size, dtype=np.complex128)
    state[:] = 1.0 / np.sqrt(size)  # H on all 20 qubits
    for layer in range(3):
        gamma = angles[2 * layer]
        beta = angles[2 * layer + 1]
        for k in range(size):
            state[k] *= np.exp(-1j * gamma * energies[k])
        c = np.cos(beta)
        s = -1j * np.sin(beta)
        for qubit in range(N):
            step = 1 << qubit
            stride = 2 * step
            for start in range(0, size, stride):
                for off in range(step):
                    i = start + off
                    a = state[i]
                    b = state[i + step]
                    state[i] = c * a + s * b
                    state[i + step] = c * b + s * a
    return state


def exact_probabilities(energies: np.ndarray, angles: np.ndarray) -> np.ndarray:
    state = evolve_qaoa(energies, np.asarray(angles, dtype=np.float64))
    return state.real ** 2 + state.imag ** 2


def exact_cvar(energies: np.ndarray, probs: np.ndarray,
               energy_order: np.ndarray, alpha: float) -> float:
    """Expected energy restricted to the lowest-energy alpha probability mass.

    Handles a partial probability weight at the alpha quantile boundary.
    energy_order is the once-per-year argsort of the fixed Ising energies.
    """
    p_sorted = probs[energy_order]
    cumulative = np.cumsum(p_sorted)
    end = int(np.searchsorted(cumulative, alpha, side="left"))
    if end >= len(p_sorted):
        raise RuntimeError("Invalid statevector normalization")
    mass_before = float(cumulative[end - 1]) if end else 0.0
    weighted = float(np.dot(p_sorted[:end], energies[energy_order[:end]]))
    weighted += (alpha - mass_before) * float(energies[energy_order[end]])
    return weighted / alpha


def save_csv(path: Path, rows: list[dict]):
    if not rows:
        return
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def run_optimization(mode: str, energies: np.ndarray, year: int,
                     alpha: float, restarts: int, maxiter: int,
                     seed: int) -> tuple[np.ndarray, list[dict]]:
    order = np.argsort(energies, kind="stable")
    rng = np.random.default_rng(seed)
    history = []
    best_score = float("inf")
    best_angles = WARM_START.copy()
    eval_id = 0

    def objective(x, restart_number):
        nonlocal best_score, best_angles, eval_id
        probs = exact_probabilities(energies, x)
        p_target = float(probs[-1])
        mean_energy = float(np.dot(probs, energies))
        if mode == "cvar":
            cvar = exact_cvar(energies, probs, order, alpha)
            score = cvar
        elif mode == "target":
            # Minimizing -log(P) is equivalent to maximizing P, but much
            # better scaled than minimizing -P when P is very small.
            cvar = float("nan")
            score = -float(np.log(max(p_target, 1e-15)))
        else:
            raise ValueError(mode)

        eval_id += 1
        row = {
            "year": year,
            "mode": mode,
            "restart": restart_number,
            "evaluation": eval_id,
            "objective": score,
            "exact_mean_energy": mean_energy,
            "exact_cvar_energy": cvar,
            "p_all_digital": p_target,
            **{key: float(value) for key, value in zip(ANGLE_NAMES, x)},
        }
        history.append(row)
        if score < best_score:
            best_score = score
            best_angles = np.array(x, dtype=np.float64).copy()
            print(f"  best {mode}: evaluation={eval_id}, "
                  f"meanE={mean_energy:.5f}, P(all digital)={p_target:.3%}, "
                  f"objective={score:.6f}", flush=True)
        return score

    for i in range(restarts):
        start = WARM_START.copy() if i == 0 else WARM_START + rng.normal(0, 0.35, 6)
        print(f"\n{mode.upper()} restart {i + 1}/{restarts}:", flush=True)
        # Evaluate the initial point even if COBYLA later doesn't return it.
        objective(start, i + 1)
        fit = minimize(lambda x: objective(x, i + 1), start,
                       method="COBYLA",
                       options={"maxiter": maxiter, "rhobeg": 0.25, "tol": 1e-4})
        print(f"  COBYLA: {fit.nfev} calls; {fit.message}", flush=True)

    return best_angles, history


def report_exact(mode: str, angles: np.ndarray, energies: np.ndarray,
                 order: np.ndarray, alpha: float, exact_min: float):
    probs = exact_probabilities(energies, angles)
    return {
        "mode": mode,
        "year": 2036,  # overwritten by caller
        "exact_classical_min_energy": exact_min,
        "statevector_mean_energy": float(np.dot(probs, energies)),
        "statevector_cvar_energy": exact_cvar(energies, probs, order, alpha),
        "statevector_p_all_digital": float(probs[-1]),
        "all_digital_expected_hits_per_4096": float(probs[-1]) * 4096,
        "alpha": alpha,
        **{key: float(value) for key, value in zip(ANGLE_NAMES, angles)},
    }


def main():
    parser = argparse.ArgumentParser(description="p=3 QAOA: CVaR and known-target diagnostic")
    parser.add_argument("--year", type=int, default=2036)
    parser.add_argument("--mode", choices=("cvar", "target", "both"), default="both")
    parser.add_argument("--alpha", type=float, default=0.10)
    parser.add_argument("--restarts", type=int, default=2)
    parser.add_argument("--maxiter", type=int, default=100)
    parser.add_argument("--shots", type=int, default=4096)
    parser.add_argument("--seed", type=int, default=2026)
    parser.add_argument("--no-classiq", action="store_true",
                        help="Skip final independent Classiq sampling")
    args = parser.parse_args()
    if not 2026 <= args.year <= 2040:
        parser.error("Year must be 2026..2040")
    if not 0 < args.alpha <= 1:
        parser.error("alpha must be in (0,1]")
    if args.restarts < 1 or args.maxiter < 1 or args.shots < 1:
        parser.error("restarts, maxiter and shots must be positive")

    energies = build_ising_energies(args.year)
    order = np.argsort(energies, kind="stable")
    exact_bits, exact_min = exact_ground_state(args.year)
    exact_index = sum(int(b) << i for i, b in enumerate(exact_bits))
    if abs(float(np.min(energies)) - float(exact_min)) > 1e-8:
        raise ValueError("Local energy diagonal disagrees with the classical benchmark")
    print(f"Year={args.year}, exact minimum={exact_min:.4f}, "
          f"20 digital is exact optimum: {exact_index == DIM - 1}")
    if args.mode in ("target", "both") and exact_index != DIM - 1:
        print("WARNING: all-digital is not the classical optimum for this year; "
              "target mode is still just a diagnostic.")

    # JIT warm-up and model consistency check.
    warm_probs = exact_probabilities(energies, WARM_START)
    warm_e = float(np.dot(warm_probs, energies))
    print(f"Starting p=3: exact mean energy={warm_e:.5f}, "
          f"P(all digital)={warm_probs[-1]:.3%}", flush=True)

    modes = ("cvar", "target") if args.mode == "both" else (args.mode,)
    results = []
    optimized = {}
    for mode in modes:
        started = time.perf_counter()
        angles, history = run_optimization(mode, energies, args.year,
                                           args.alpha, args.restarts,
                                           args.maxiter, args.seed)
        elapsed = time.perf_counter() - started
        out = report_exact(mode, angles, energies, order, args.alpha, exact_min)
        out["year"] = args.year
        out["optimization_seconds_local"] = elapsed
        out["optimizer_evaluations"] = len(history)
        optimized[mode] = (angles, out)
        save_csv(HERE / f"{mode}_{args.year}_history.csv", history)
        print(f"\n{mode.upper()} LOCAL RESULT: mean={out['statevector_mean_energy']:.5f}, "
              f"CVaR={out['statevector_cvar_energy']:.5f}, "
              f"P(all digital)={out['statevector_p_all_digital']:.3%}", flush=True)
        print("  angles:", np.array2string(angles, precision=8), flush=True)

    # Always write locally verified results first, even if Classiq login fails.
    save_csv(HERE / f"cvar_vs_target_{args.year}_local_summary.csv",
             [result for _, result in optimized.values()])

    # Cross-check chosen angles using the same Classiq SDK program that already
    # ran successfully in Studio. Do not synthesize on every evaluation.
    qp = None
    if not args.no_classiq:
        from classiq import authenticate, synthesize, sample
        from vasion_classiq_qaoa_p3 import main as classiq_main, make_parameters, analyze
        authenticate()
        print("\nSynthesizing the existing Classiq p=3 circuit once...", flush=True)
        qp = synthesize(classiq_main)

    for mode, (angles, out) in optimized.items():
        if qp is not None:
            print(f"Sampling {mode} in Classiq with {args.shots} shots...", flush=True)
            df = sample(qp, parameters=make_parameters(args.year, angles),
                        num_shots=args.shots, backend="simulator", verbose=False)
            classiq_result = analyze(df, args.year, angles)
            out["classiq_mean_energy"] = classiq_result["qaoa_mean_energy"]
            out["classiq_best_sampled_energy"] = classiq_result["qaoa_best_sampled_energy"]
            out["classiq_p_exact_ground_state"] = classiq_result["exact_state_probability"]
            out["classiq_unique_measured_states"] = classiq_result["unique_observed_states"]
            # Save all measured outcomes with their original Classiq columns.
            df.to_csv(HERE / f"{mode}_{args.year}_classiq_measurements.csv", index=False)
            print(f"  Classiq: mean={out['classiq_mean_energy']:.5f}, "
                  f"P(exact)={out['classiq_p_exact_ground_state']:.3%}, "
                  f"best sampled={out['classiq_best_sampled_energy']:.5f}", flush=True)
        results.append(out)

    save_csv(HERE / f"cvar_vs_target_{args.year}_summary.csv", results)
    print(f"\nSaved: {HERE / f'cvar_vs_target_{args.year}_summary.csv'}")
    print("Old p=2/p=3 results are unchanged.")


if __name__ == "__main__":
    main()
