#!/usr/bin/env python3
"""CVaR alpha sweep + 2026--2040 QAOA for the Vasion 20-industry Ising model.

THIS SCRIPT RUNS IN CLASSIQ STUDIO (Python terminal), NOT IN THE NATIVE QMOD EDITOR.

It reuses the validated Classiq p=3 QAOA circuit, optimizes a matching classical
20-qubit *exact statevector*, and can verify the chosen angles by taking actual
shots from the Classiq simulator. It does NOT claim quantum hardware speedup.

Keep these files together in the same folder:
    vasion_cvar_alpha_timeline.py        (this file)
    vasion_qaoa_p3_cvar.py               (existing exact simulator)
    vasion_classiq_qaoa_p3.py            (existing Classiq circuit)
    paper_phase_transition_baseline.py   (exact min-cut benchmark)
    paper_phase_transition_20_industries.json

Example commands (from that folder):
    python vasion_cvar_alpha_timeline.py --phase tune --maxiter 75 --restarts 2 --classiq
    python vasion_cvar_alpha_timeline.py --phase timeline --maxiter 40 --restarts 1 --classiq

Outputs go to a NEW subfolder called cvar_alpha_timeline_outputs.
"""

import argparse
import csv
import json
import time
from pathlib import Path

import numpy as np
from scipy.optimize import minimize

from paper_phase_transition_baseline import exact_ground_state
from vasion_qaoa_p3_cvar import (
    N, DIM, ANGLE_NAMES, WARM_START,
    build_ising_energies, exact_probabilities, exact_cvar,
)

HERE = Path(__file__).resolve().parent
OUT_DEFAULT = HERE / "cvar_alpha_timeline_outputs"


def save_csv(path, rows):
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def reference(year):
    e = build_ising_energies(year)
    bits, benchmark_min = exact_ground_state(year)
    exact_index = sum(int(b) << i for i, b in enumerate(bits))
    if not np.isclose(float(e[exact_index]), benchmark_min, atol=1e-8):
        raise ValueError("Classiq/model bit indexing mismatch in exact benchmark")
    if not np.isclose(float(e.min()), benchmark_min, atol=1e-8):
        raise ValueError("Statevector Hamiltonian disagrees with exact min cut")
    order = np.argsort(e, kind="stable")
    ground = np.flatnonzero(np.isclose(e, benchmark_min, rtol=0, atol=1e-8))
    return e, order, ground, exact_index, float(benchmark_min), bits


def summarize(energies, order, ground, angles, alpha):
    p = exact_probabilities(energies, np.asarray(angles, dtype=np.float64))
    i_top = int(np.argmax(p))
    i_ground = int(np.argmax(p[ground]))
    return {
        "mean_energy": float(np.dot(p, energies)),
        "cvar_energy": exact_cvar(energies, p, order, alpha),
        "ground_state_probability": float(np.sum(p[ground])),
        "most_likely_probability": float(p[i_top]),
        "most_likely_energy": float(energies[i_top]),
        "most_likely_qubit_order": format(i_top, f"0{N}b")[::-1],
        "most_likely_display_bits": format(i_top, f"0{N}b"),
        "most_likely_digital_count": int(i_top.bit_count()),
        "ground_state_degeneracy": len(ground),
        "most_probable_ground_bitstring": format(int(ground[i_ground]), f"0{N}b"),
    }


def angle_fields(x):
    return {name: float(value) for name, value in zip(ANGLE_NAMES, x)}


def optimize(energies, order, ground, year, alpha, starts, maxiter, seed, label):
    """COBYLA only sees CVaR energy; NOT the known ground-state bits."""
    rng = np.random.default_rng(seed)
    hist = []
    best = (float("inf"), None)
    t0 = time.perf_counter()

    def fun(x, restart):
        nonlocal best
        p = exact_probabilities(energies, x)
        obj = exact_cvar(energies, p, order, alpha)
        row = {
            "year": year, "alpha": alpha, "restart": restart,
            "evaluation": len(hist) + 1, "objective_cvar": obj,
            "mean_energy": float(np.dot(p, energies)),
            # Ground-state probability is RECORDED for later evaluation;
            # it is never passed to COBYLA or used by this objective.
            "ground_state_probability_diagnostic": float(np.sum(p[ground])),
            **angle_fields(x),
        }
        hist.append(row)
        if obj < best[0]:
            best = (float(obj), np.array(x, dtype=np.float64).copy())
        return obj

    for k, start in enumerate(starts, start=1):
        x0 = np.asarray(start, dtype=np.float64)
        if x0.shape != (6,):
            raise ValueError("p=3 requires exactly 6 angles")
        # Include the start itself, even if the optimizer later steps uphill.
        fun(x0, k)
        fit = minimize(
            lambda x: fun(x, k), x0, method="COBYLA",
            options={"maxiter": maxiter, "rhobeg": 0.25, "tol": 1e-4},
        )
        print(f"  {label} restart {k}/{len(starts)}: {fit.nfev} COBYLA calls; "
              f"best CVaR={best[0]:.5f}", flush=True)

    return best[1], hist, time.perf_counter() - t0


def starts_for_tune(restarts, seed, warm=None):
    rng = np.random.default_rng(seed)
    base = WARM_START if warm is None else np.asarray(warm, dtype=np.float64)
    return [base.copy()] + [base + rng.normal(0, 0.35, 6) for _ in range(restarts - 1)]


class ClassiqVerifier:
    def __init__(self, enabled):
        self.enabled = enabled
        self.qp = None
        if enabled:
            from classiq import authenticate, synthesize
            from vasion_classiq_qaoa_p3 import main as classiq_circuit
            print("Authenticating and synthesizing existing Classiq p=3 circuit ONCE...", flush=True)
            authenticate()
            self.qp = synthesize(classiq_circuit)

    def verify(self, year, alpha, angles, shots, output_path):
        if not self.enabled:
            return {}
        from classiq import sample
        from vasion_classiq_qaoa_p3 import make_parameters, analyze
        print(f"  Verifying {year}, alpha={alpha:.2f} in Classiq "
              f"with {shots:,} shots...", flush=True)
        data = sample(self.qp, parameters=make_parameters(year, angles),
                      num_shots=shots, backend="simulator", verbose=False)
        result = analyze(data, year, angles)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        data.to_csv(output_path, index=False)
        return {
            "classiq_shots": shots,
            "classiq_mean_energy": result["qaoa_mean_energy"],
            "classiq_ground_state_frequency": result["exact_state_probability"],
            "classiq_best_sampled_energy": result["qaoa_best_sampled_energy"],
            "classiq_best_sampled_gap": result["qaoa_best_energy_gap"],
            "classiq_best_digital_count": result["qaoa_best_digital_count"],
            "classiq_unique_observed_states": result["unique_observed_states"],
        }


def tune(args, verifier, output):
    year = 2036
    energies, order, ground, ground_index, e_min, exact_bits = reference(year)
    print(f"Tuning CVaR alpha on {year}; classical ground E={e_min:.4f}, "
          f"{len(ground)} ground state(s).", flush=True)
    rows, history = [], []
    for j, alpha in enumerate(args.alphas):
        print(f"\nCVaR alpha={alpha:.2f}", flush=True)
        starts = starts_for_tune(args.restarts, args.seed)  # same starts for fair alpha comparison
        angles, log, duration = optimize(
            energies, order, ground, year, alpha, starts,
            args.maxiter, args.seed + 13 * j, f"alpha={alpha:.2f}",
        )
        history.extend(log)
        stats = summarize(energies, order, ground, angles, alpha)
        row = {"year": year, "alpha": alpha, "exact_min_energy": e_min,
               "optimizer_calls": len(log), "local_optimization_seconds": duration,
               **stats, **angle_fields(angles)}
        row.update(verifier.verify(
            year, alpha, angles, args.shots,
            output / f"tune_2036_alpha_{int(round(100*alpha)):02d}_classiq_measurements.csv"
        ))
        rows.append(row)
        save_csv(output / "cvar_alpha_2036_tuning.csv", rows)
        save_csv(output / "cvar_alpha_2036_history.csv", history)
        print(f"  meanE={stats['mean_energy']:.4f}, "
              f"P(exact ground)={stats['ground_state_probability']:.3%}, "
              f"CVaR={stats['cvar_energy']:.4f}", flush=True)

    # Default comparison metric is mean energy, not CVaR: comparing CVaR
    # numerical values ACROSS ALPHAS is invalid because the tail changes.
    # Optionally select based on exact ground-state probability, but this uses
    # knowledge of the answer and is explicitly marked as a diagnostic.
    if args.select_by == "mean":
        winner = min(rows, key=lambda r: r["mean_energy"])
    else:
        winner = max(rows, key=lambda r: r["ground_state_probability"])
    selection = {"selected_alpha": winner["alpha"],
                 "selection_method": args.select_by,
                 "selection_uses_ground_state_as_label": args.select_by == "probability",
                 "tuning_year": 2036,
                 "angles": [winner[k] for k in ANGLE_NAMES],
                 "mean_energy_2036": winner["mean_energy"],
                 "ground_state_probability_2036": winner["ground_state_probability"]}
    with (output / "selected_alpha.json").open("w", encoding="utf-8") as f:
        json.dump(selection, f, indent=2)
    print(f"\nSelected alpha={selection['selected_alpha']:.2f} by "
          f"{args.select_by} for 2036. Selection file: {output/'selected_alpha.json'}", flush=True)
    return selection


def read_selection(output):
    p = output / "selected_alpha.json"
    if not p.exists():
        raise FileNotFoundError(f"Missing {p}; run --phase tune first")
    return json.loads(p.read_text(encoding="utf-8"))


def load_old_p2_baseline():
    """Optional earlier p=2 Classiq 15-year CSV, for a fair before/after plot."""
    locations = [
        HERE / "vasion_qaoa_baseline_summary.csv",
        HERE.parent / "vasion_qaoa_baseline_summary.csv",
    ]
    for path in locations:
        if path.exists():
            try:
                with path.open(newline="", encoding="utf-8") as f:
                    data = {int(r["year"]): r for r in csv.DictReader(f)}
                if "qaoa_mean_energy" in next(iter(data.values())):
                    print(f"Found earlier p=2 unoptimized baseline: {path}", flush=True)
                    return data
            except (KeyError, ValueError, StopIteration):
                pass
    return {}


def timeline(args, verifier, output, selection):
    alpha = float(selection["selected_alpha"])
    tuned_2036 = np.asarray(selection["angles"], dtype=np.float64)
    rows, histories = [], []
    basename = f"cvar_timeline_{args.start_year}_{args.end_year}"
    prev = None
    old_p2 = load_old_p2_baseline()
    print(f"\nTimeline {args.start_year}..{args.end_year}, alpha={alpha}, "
          f"selection={selection['selection_method']}; "
          f"COBYLA CVaR at each year.\n", flush=True)
    for year in range(args.start_year, args.end_year + 1):
        energies, order, ground, gindex, e_min, exact_bits = reference(year)
        if prev is None:
            base = WARM_START.copy()
        else:
            base = prev.copy()
        # For 2036, use tuned angles as starting point. Other years are warm-
        # started with previous year's optimum, not the known ground state.
        if year == 2036:
            base = tuned_2036.copy()
        starts = starts_for_tune(args.restarts, args.seed + year, base)
        x, log, duration = optimize(
            energies, order, ground, year, alpha, starts, args.maxiter,
            args.seed + year, f"year={year}",
        )
        prev = x.copy()
        histories.extend(log)
        stats = summarize(energies, order, ground, x, alpha)
        row = {
            "year": year,
            "ai_pressure": 0.07*(year-2026),
            "alpha": alpha,
            "classical_min_energy": e_min,
            "classical_digital_count": int(sum(exact_bits)),
            "classical_bits_qubit_order": "".join(map(str, exact_bits)),
            "classical_bits_display_order": "".join(map(str, reversed(exact_bits))),
            "mean_energy_gap": stats["mean_energy"] - e_min,
            "optimizer_calls": len(log),
            "local_optimization_seconds": duration,
            **stats,
            **angle_fields(x),
        }
        if year in old_p2:
            row["old_p2_mean_energy"] = float(old_p2[year]["qaoa_mean_energy"])
            row["old_p2_ground_frequency"] = float(old_p2[year]["exact_state_probability"])
        else:
            row["old_p2_mean_energy"] = ""
            row["old_p2_ground_frequency"] = ""
        row.update(verifier.verify(
            year, alpha, x, args.shots,
            output / f"timeline_{year}_classiq_measurements.csv"
        ))
        rows.append(row)
        save_csv(output / f"{basename}.csv", rows)
        save_csv(output / f"{basename}_optimization_history.csv", histories)
        print(f"  {year}: classical E={e_min:.4f}, exact statevector "
              f"mean E={stats['mean_energy']:.4f}, P(ground)="
              f"{stats['ground_state_probability']:.3%}; "
              f"digital classical={sum(exact_bits)}/20", flush=True)

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        years = [r["year"] for r in rows]
        fig, ax = plt.subplots(figsize=(9, 5))
        ax.plot(years, [r["classical_min_energy"] for r in rows], "o-", label="Exact classical minimum")
        ax.plot(years, [r["mean_energy"] for r in rows], "s-", label="CVaR QAOA expected energy (statevector)")
        if old_p2 and all(r["year"] in old_p2 for r in rows):
            ax.plot(years, [r["old_p2_mean_energy"] for r in rows], "^--", label="Original p=2 QAOA mean (Classiq shots)")
        if verifier.enabled:
            ax.plot(years, [r["classiq_mean_energy"] for r in rows], ".--", label="CVaR QAOA mean (Classiq shots)")
        ax.set(xlabel="Year", ylabel="Ising energy", title="20-industry Ising: classical vs CVaR-QAOA")
        ax.legend()
        fig.tight_layout()
        fig.savefig(output / "energy_comparison.png", dpi=160)
        plt.close(fig)

        fig, ax = plt.subplots(figsize=(9, 5))
        ax.plot(years, [r["classical_digital_count"] for r in rows], "o-", label="Classical ground-state digital count")
        ax.plot(years, [r["most_likely_digital_count"] for r in rows], "s-", label="CVaR QAOA most-probable state digital count")
        ax.set(xlabel="Year", ylabel="Number of digital industries", ylim=(-0.5, 20.5),
               title="Digital adoption: exact ground state vs most-probable QAOA state")
        ax.legend()
        fig.tight_layout()
        fig.savefig(output / "digital_adoption_comparison.png", dpi=160)
        plt.close(fig)
        fig, ax = plt.subplots(figsize=(9, 5))
        ax.plot(years, [100*r["ground_state_probability"] for r in rows], "o-",
                label="p=3 CVaR QAOA (exact statevector)")
        if verifier.enabled:
            ax.plot(years, [100*r["classiq_ground_state_frequency"] for r in rows], "s--",
                    label="p=3 CVaR QAOA (Classiq measured frequency)")
        if old_p2 and all(r["year"] in old_p2 for r in rows):
            ax.plot(years, [100*r["old_p2_ground_frequency"] for r in rows], "^--",
                    label="Original p=2 QAOA (Classiq measured frequency)")
        ax.set(xlabel="Year", ylabel="Exact classical ground state probability (%)",
               title="Probability of sampling the correct industry configuration")
        ax.legend()
        fig.tight_layout()
        fig.savefig(output / "ground_state_probability.png", dpi=160)
        plt.close(fig)
        print("Saved three comparison PNG graphs.", flush=True)
    except Exception as exc:
        print(f"Plots skipped ({type(exc).__name__}: {exc}). CSV results are complete.")
    return rows


def main():
    p = argparse.ArgumentParser(description="CVaR alpha sweep and all-years Classiq comparison")
    p.add_argument("--phase", choices=("tune", "timeline", "both"), default="tune")
    p.add_argument("--alphas", nargs="+", type=float, default=[0.05, 0.10, 0.20])
    p.add_argument("--select-by", choices=("mean", "probability"), default="mean",
                   help="Use mean energy (fairer) or benchmark ground-state probability (diagnostic)")
    p.add_argument("--restarts", type=int, default=1)
    p.add_argument("--maxiter", type=int, default=50)
    p.add_argument("--shots", type=int, default=4096)
    p.add_argument("--start-year", type=int, default=2026)
    p.add_argument("--end-year", type=int, default=2040)
    p.add_argument("--seed", type=int, default=2026)
    p.add_argument("--classiq", action="store_true", help="Verify chosen angles by Classiq simulator shots")
    p.add_argument("--output", type=Path, default=OUT_DEFAULT)
    args = p.parse_args()
    if not (2026 <= args.start_year <= args.end_year <= 2040):
        p.error("Year range must lie within 2026..2040")
    if not (1 <= args.restarts <= 100 and args.maxiter >= 8 and args.shots >= 1):
        p.error("restarts and shots must be positive; COBYLA maxiter >= 8 for six parameters")
    if len(set(args.alphas)) != len(args.alphas) or not all(0 < a <= 1 for a in args.alphas):
        p.error("alphas must be unique fractions in (0,1]")
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    verifier = ClassiqVerifier(args.classiq)
    selection = tune(args, verifier, output) if args.phase in ("tune", "both") else read_selection(output)
    if args.phase in ("timeline", "both"):
        timeline(args, verifier, output, selection)
    print(f"\nFinished. Results folder: {output}", flush=True)


if __name__ == "__main__":
    main()
