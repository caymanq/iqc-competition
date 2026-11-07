"""Render empirical benchmark data without fitting/extrapolating QAOA timings."""
from __future__ import annotations
import csv
import json
from collections import defaultdict
from pathlib import Path
import statistics
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent
rows = list(csv.DictReader((ROOT / "results" / "raw.csv").open()))
(ROOT / "results" / "raw.json").write_text(json.dumps(rows, indent=2) + "\n")
groups = defaultdict(list)
for row in rows:
    groups[(row["family"], int(row["n"]))].append(row)

def median(family, n, field):
    return statistics.median(float(r[field]) for r in groups[(family, n)])

common = sorted(n for family, n in groups if family == "common")
classical = sorted(n for family, n in groups if family in {"common", "classical_only"})
fig, ax = plt.subplots(figsize=(10, 6), facecolor="#101820")
ax.set_facecolor("#101820")
end_to_end = [median("common", n, "graph_build_s") + median("common", n, "energy_precompute_s") +
              median("common", n, "qaoa_optimizer_s") for n in common]
ax.plot(common, end_to_end, "o-", color="#2374ab", lw=2.5,
        label="ideal p=1 QAOA end-to-end: graph + precompute + 9-eval optimizer")
ax.plot(classical, [median("common" if n in common else "classical_only", n, "mincut_s") for n in classical],
        "o-", color="#4caf50", lw=2.5, label="exact ferromagnetic s–t min-cut")
ax.set_xscale("log", base=2); ax.set_yscale("log")
ax.set_xlabel("industries / qubits (n)", color="white")
ax.set_ylabel("wall-clock seconds (median of 3 repeats)", color="white")
ax.set_title("Empirical CPU benchmark: exact min-cut vs ideal statevector QAOA", color="white", weight="bold")
ax.tick_params(colors="white")
for spine in ax.spines.values(): spine.set_color("#9aa4ad")
ax.grid(True, color="#39505d", alpha=.55)
legend=ax.legend(facecolor="#17232c", edgecolor="#607d8b")
for text in legend.get_texts(): text.set_color("white")
ax.text(.02,.02, "QAOA points exist only at measured statevector sizes; no extrapolation to n=40…2000.\n"
                  "QAOA is an ideal CPU simulation, not hardware runtime or quantum advantage.",
        transform=ax.transAxes, color="#d4e1e8", fontsize=8, va="bottom")
fig.tight_layout()
fig.savefig(ROOT / "results" / "runtime_empirical.png", dpi=180, facecolor=fig.get_facecolor())
fig.savefig(ROOT / "results" / "runtime_empirical.svg", facecolor=fig.get_facecolor())

components, component_ax = plt.subplots(figsize=(10, 5), facecolor="#101820")
component_ax.set_facecolor("#101820")
component_ax.plot(common, [median("common", n, "energy_precompute_s") for n in common], "o-", color="#f0ad4e", label="energy precompute")
component_ax.plot(common, [median("common", n, "qaoa_one_eval_s") for n in common], "o-", color="#61c0bf", label="one p=1 circuit evaluation")
component_ax.plot(common, [median("common", n, "qaoa_optimizer_s") for n in common], "o-", color="#2374ab", label="nine-evaluation optimizer")
component_ax.set_xscale("log", base=2); component_ax.set_yscale("log")
component_ax.set(xlabel="qubits", ylabel="seconds (median; per-size repeat count in raw CSV)",
                 title="Measured ideal-statevector QAOA timing components")
component_ax.xaxis.label.set_color("white")
component_ax.yaxis.label.set_color("white")
component_ax.title.set_color("white")
component_ax.tick_params(colors="white")
for spine in component_ax.spines.values(): spine.set_color("#9aa4ad")
component_ax.grid(True, color="#39505d", alpha=.55)
legend=component_ax.legend(facecolor="#17232c", edgecolor="#607d8b", labelcolor="white")
for text in legend.get_texts(): text.set_color("white")
components.tight_layout()
components.savefig(ROOT / "results" / "qaoa_components.png", dpi=180, facecolor=components.get_facecolor())

with (ROOT / "results" / "summary.csv").open("w", newline="") as handle:
    writer=csv.writer(handle); writer.writerow(["family","n","repeat_count","mincut_median_s","qaoa_end_to_end_median_s","qaoa_optimizer_median_s","qaoa_one_eval_median_s","precompute_median_s","qaoa_expected_energy_gap_median","qaoa_ground_probability_median"])
    for n in classical:
        family="common" if n in common else "classical_only"
        repeated=groups[(family,n)]
        writer.writerow([family,n,len(repeated),median(family,n,"mincut_s"),
                         median("common",n,"graph_build_s") + median("common",n,"energy_precompute_s") + median("common",n,"qaoa_optimizer_s") if family=="common" else "",
                         median("common",n,"qaoa_optimizer_s") if family=="common" else "",
                         median("common",n,"qaoa_one_eval_s") if family=="common" else "",
                         median("common",n,"energy_precompute_s") if family=="common" else "",
                         median("common",n,"qaoa_expected_energy") - median("common",n,"exact_energy") if family=="common" else "",
                         median("common",n,"qaoa_ground_probability") if family=="common" else ""])
