"""One-command reproducible MVP runner."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import platform
import subprocess
import sys
import time
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from .model import load_model
from .exact import mincut, flip_intervals
from .solvers import simulated_annealing, dqa_aer, qaoa_aer
from .metrics import observed_flip_years, flip_comparison
from .scenarios import twelve_region, no_ties, resistance_influence


def _exact(model, years):
    return {year: mincut(model, year) for year in years}


def _write_figures(out: Path, model, years, exact, states, energy_rows, influence=None):
    figdir = out / "figures"
    figdir.mkdir(exist_ok=True)
    labels = ["Exact (paper-tie)", *states]
    matrices = [np.array([exact[y].paper_state for y in years]), *[np.array([states[m][y] for y in years]) for m in states]]
    fig, axes = plt.subplots(1, len(matrices), figsize=(5 * len(matrices), 7), sharey=True)
    axes = np.atleast_1d(axes)
    for ax, label, matrix in zip(axes, labels, matrices):
        ax.imshow(matrix.T, aspect="auto", cmap="RdYlGn", vmin=-1, vmax=1)
        ax.set_title(label)
        ax.set_xticks(range(0, len(years), 2), list(years)[::2], rotation=45)
        ax.set_yticks(range(model.n), model.names, fontsize=7)
    fig.suptitle("One-region states: paper (red) → digital (green); illustrative coefficients")
    fig.tight_layout()
    fig.savefig(figdir / "tipping_map.png", dpi=160)
    plt.close(fig)
    # Business-facing flip-year heatmap; -1 is explicitly censored/not observed in the window.
    flip_data = {}
    exact_intervals = flip_intervals(exact)
    flip_data["Exact (canonical)"] = exact_intervals["late"]
    for method, state in states.items():
        flip_data[method] = observed_flip_years(state)[0]
    fig, axes = plt.subplots(1, len(flip_data), figsize=(4 * len(flip_data), 7), sharey=True)
    axes = np.atleast_1d(axes)
    for ax, (label, values) in zip(axes, flip_data.items()):
        shown = np.where(values < 0, max(years) + 1, values)
        image = ax.imshow(shown[:, None], aspect="auto", cmap="viridis",
                          vmin=min(years), vmax=max(years) + 1)
        ax.set_title(label)
        ax.set_xticks([])
        ax.set_yticks(range(model.n), model.names, fontsize=7)
        for i, value in enumerate(values):
            if value < 0:
                ax.text(0, i, ">2040", ha="center", va="center", color="white", fontsize=6)
    fig.colorbar(image, ax=axes, label="first digital year; >2040 is censored")
    fig.suptitle("Tipping-point heatmap: illustrative one-region scenario")
    fig.tight_layout()
    fig.savefig(figdir / "flip_year_heatmap.png", dpi=160)
    plt.close(fig)
    df = pd.DataFrame(energy_rows)
    fig, ax = plt.subplots(figsize=(9, 4))
    for method, sub in df.groupby("method"):
        ax.plot(sub.year, sub.energy_error / model.unit, marker="o",
                linestyle="-" if len(sub) == len(years) else "None", label=method)
    ax.axhline(0, color="black", lw=.8)
    ax.set(title="Raw solver energy error vs exact min-cut", xlabel="Year", ylabel="ΔE (model units)")
    ax.legend()
    fig.tight_layout()
    fig.savefig(figdir / "energy_error.png", dpi=160)
    plt.close(fig)
    if influence is not None:
        fig, ax = plt.subplots(figsize=(8, 7))
        im = ax.imshow(influence, cmap="coolwarm_r", vmin=-4, vmax=4)
        ax.set(title="Resistance-perturbation scenario: Δ canonical flip year\n(row lowered by 0.10; negative means earlier)")
        ax.set_xticks(range(model.n), model.names, rotation=90, fontsize=6)
        ax.set_yticks(range(model.n), model.names, fontsize=6)
        fig.colorbar(im, ax=ax, label="years")
        fig.tight_layout()
        fig.savefig(figdir / "resistance_influence.png", dpi=160)
        plt.close(fig)


def run(args) -> int:
    model, years, config = load_model(args.config)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    exact = _exact(model, years)
    intervals = flip_intervals(exact)
    methods: dict[str, dict[int, np.ndarray]] = {}
    rows: list[dict] = []
    method_results = {}

    # Exact and SA are annual independent solves. SA raw best restart is its specified solver output.
    sa = {}
    for year in years:
        result = simulated_annealing(model, year, args.seed + year)
        sa[year] = result.state
        method_results.setdefault("sa", {})[year] = result
    methods["sa"] = sa

    # DQA is the primary free genuine quantum circuit path. If 20q is too costly,
    # --quantum-nodes intentionally creates and labels a prefix subset rather than mislabeling it.
    qmodel = model
    if args.quantum_nodes < model.n:
        n = args.quantum_nodes
        qmodel = type(model)(model.names[:n], model.resistance[:n], model.ties[:n, :n], model.pressure_step, model.unit)
    dqa = {}
    for year in years:
        result = dqa_aer(qmodel, year, args.seed + 1000 + year, shots=args.shots, p=args.dqa_p, total_time=args.dqa_time)
        dqa[year] = result.state
        method_results.setdefault("dqa_aer", {})[year] = result
    if qmodel.n == model.n:
        methods["dqa_aer"] = dqa
    # QAOA is tested only at representative years due to statevector grid-search cost.
    qaoa_years = [min(years), list(years)[len(years)//2], max(years)]
    qaoa_results = {}
    for year in qaoa_years:
        qaoa_results[year] = qaoa_aer(qmodel, year, args.seed + 2000 + year, shots=args.shots)
        method_results.setdefault("qaoa_aer", {})[year] = qaoa_results[year]

    for method, results in method_results.items():
        for year, result in results.items():
            truth = mincut(qmodel if qmodel.n != model.n else model, year)
            scope = ("CLASSICAL-1R" if method == "sa" else
                     ("QUANTUM-FULL-1R" if qmodel.n == model.n else f"QUANTUM-SUBSET-{qmodel.n}"))
            rows.append({"method": method, "year": year, "scope": scope,
                         "raw_energy": result.energy, "exact_energy": truth.energy, "energy_error": result.energy - truth.energy,
                         "is_ground": result.energy == truth.energy, "seconds": result.seconds, **result.meta})
    energy = pd.DataFrame(rows)
    energy.to_csv(out / "per_year_metrics.csv", index=False)
    flip_rows = []
    for method, state in methods.items():
        observed, flipback = observed_flip_years(state)
        for item, back in zip(flip_comparison(observed, intervals["early"], intervals["late"]), flipback):
            item.update(method=method, node_name=model.names[item["node"]], flipback=bool(back))
            flip_rows.append(item)
    pd.DataFrame(flip_rows).to_csv(out / "per_node_flip_metrics.csv", index=False)
    # Classical scale / theory scenario are exact; explicitly not quantum outputs.
    regional = twelve_region(model)
    begin = time.perf_counter()
    rresults = _exact(regional, years)
    regional_time = time.perf_counter() - begin
    pd.DataFrame({"node": regional.names, "early": flip_intervals(rresults)["early"], "late": flip_intervals(rresults)["late"]}).to_csv(out / "classical_12region_exact.csv", index=False)
    baseline = flip_intervals(_exact(no_ties(model), years))["late"]
    np.savetxt(out / "no_ties_canonical_flip_years.csv", baseline[None, :], fmt="%d", delimiter=",")
    influence = resistance_influence(model, years, round(.10 * model.unit))
    np.savetxt(out / "resistance_influence.csv", influence, delimiter=",")
    _write_figures(out, model, years, exact, methods, rows, influence)
    report = [
        "# Paper Phase Transition MVP results",
        "",
        "All coefficients are challenge-suggested illustrative scenarios, not empirical forecasts.",
        f"- Exact one-region min-cut: {model.n} nodes × {len(years)} years.",
        f"- Classical 12-region exact min-cut: {regional.n} nodes × {len(years)} years in {regional_time:.3f}s.",
        f"- Quantum scope: {'full one-region 20-node model' if qmodel.n == model.n else f'ONLY {qmodel.n}-node subset; full outputs are classical'}; Aer circuit simulation, not hardware.",
        "- DQA and QAOA results are raw modal measured bitstrings; no local search/polishing is applied.",
        "- `per_year_metrics.csv` reports raw energy errors and failure rates (`is_ground`). `per_node_flip_metrics.csv` reports business-relevant flip-year categories, censored values, and flip-backs.",
        "- Exact degeneracy is represented with [early, late] flip intervals. A small nonzero energy error remains an error even if it is fragile.",
        "- Ties are mutual-dependence assumptions, not causal evidence. Equilibrium years are not switching-delay dynamics.",
        "",
        "## Solver summary",
        energy.groupby("method").agg(runs=("year", "count"), ground_rate=("is_ground", "mean"), median_seconds=("seconds", "median"), mean_energy_error=("energy_error", "mean")).to_markdown(),
    ]
    (out / "RESULTS.md").write_text("\n".join(report) + "\n")
    meta = {"config": config, "python": sys.version, "platform": platform.platform(),
            "seed": args.seed, "quantum_nodes": qmodel.n, "shots": args.shots, "dqa_p": args.dqa_p,
            "dqa_time": args.dqa_time, "git_sha": subprocess.getoutput("git rev-parse HEAD")}
    (out / "run.json").write_text(json.dumps(meta, indent=2, default=str))
    print((out / "RESULTS.md").read_text())
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["all"])
    parser.add_argument("--config", default="configs/one_region.yaml")
    parser.add_argument("--out", default="results/mvp")
    parser.add_argument("--seed", type=int, default=20261106)
    parser.add_argument("--shots", type=int, default=1024)
    parser.add_argument("--dqa-p", type=int, default=3)
    parser.add_argument("--dqa-time", type=float, default=3.0)
    parser.add_argument("--quantum-nodes", type=int, default=20)
    return run(parser.parse_args())


if __name__ == "__main__":
    raise SystemExit(main())
