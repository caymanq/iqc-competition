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
extension = ROOT / "results" / "classical_extension.csv"
if extension.exists():
    rows.extend(row for row in csv.DictReader(extension.open()) if row["status"] == "completed")
(ROOT / "results" / "raw.json").write_text(json.dumps(rows, indent=2) + "\n")
groups = defaultdict(list)
for row in rows:
    groups[(row["family"], int(row["n"]))].append(row)

def median(family, n, field):
    return statistics.median(float(r[field]) for r in groups[(family, n)])

common = sorted(n for family, n in groups if family == "common")
classical = sorted(n for family, n in groups if family in {"common", "classical_only", "classical_extension"})
fig, ax = plt.subplots(figsize=(10, 6), facecolor="#101820")
ax.set_facecolor("#101820")
end_to_end = [median("common", n, "graph_build_s") + median("common", n, "energy_precompute_s") +
              median("common", n, "qaoa_optimizer_s") for n in common]
ax.plot(common, end_to_end, "o-", color="#2374ab", lw=2.5,
        label="ideal p=1 QAOA end-to-end: graph + precompute + 9-eval optimizer")
def classical_family(n):
    return "common" if n in common else ("classical_only" if ("classical_only", n) in groups else "classical_extension")
ax.plot(classical, [median(classical_family(n), n, "graph_build_s") + median(classical_family(n), n, "mincut_s") for n in classical],
        "o-", color="#4caf50", lw=2.5, label="exact min-cut end-to-end: instance + residual network + max-flow")
ax.set_xscale("log", base=2); ax.set_yscale("log")
ax.set_xlabel("industries / qubits (n)", color="white")
ax.set_ylabel("wall-clock seconds", color="white")
ax.set_title("Empirical CPU benchmark: exact min-cut vs ideal statevector QAOA", color="white", weight="bold")
ax.tick_params(colors="white")
for spine in ax.spines.values(): spine.set_color("#9aa4ad")
ax.grid(True, color="#39505d", alpha=.55)
legend=ax.legend(facecolor="#17232c", edgecolor="#607d8b")
for text in legend.get_texts(): text.set_color("white")
ax.text(.02,.02, "QAOA points exist only at measured statevector sizes through n=26; no QAOA extrapolation.\n"
                  "Repeat counts vary by size (raw CSV); QAOA is ideal CPU simulation, not hardware runtime or advantage.",
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

zoom, zoom_ax = plt.subplots(figsize=(9,5), facecolor="#101820")
zoom_ax.set_facecolor("#101820")
zoom_ax.plot(common, end_to_end, "o-", color="#2374ab", lw=2.5, label="QAOA end-to-end")
zoom_ax.plot(common, [median("common", n, "graph_build_s") + median("common", n, "mincut_s") for n in common],
             "o-", color="#4caf50", lw=2.5, label="min-cut end-to-end")
zoom_ax.set_yscale("log"); zoom_ax.set(xlabel="common measured n", ylabel="wall-clock seconds",
                                       title="Common-size zoom: same seeded instances")
zoom_ax.xaxis.label.set_color("white"); zoom_ax.yaxis.label.set_color("white"); zoom_ax.title.set_color("white")
zoom_ax.tick_params(colors="white"); zoom_ax.grid(True, color="#39505d", alpha=.55)
legend=zoom_ax.legend(facecolor="#17232c", edgecolor="#607d8b", labelcolor="white")
zoom.tight_layout()
zoom.savefig(ROOT / "results" / "runtime_common_zoom.png", dpi=180, facecolor=zoom.get_facecolor())

quality, (gap_ax, prob_ax) = plt.subplots(2, 1, figsize=(9,7), sharex=True, facecolor="#101820")
for axis in (gap_ax, prob_ax):
    axis.set_facecolor("#101820"); axis.set_xscale("log", base=2); axis.set_yscale("log")
    axis.tick_params(colors="white"); axis.grid(True, color="#39505d", alpha=.55)
    for spine in axis.spines.values(): spine.set_color("#9aa4ad")
gap_ax.plot(common, [median("common",n,"qaoa_expected_energy")-median("common",n,"exact_energy") for n in common],
            "o-", color="#f0ad4e")
prob_ax.plot(common, [median("common",n,"qaoa_ground_probability") for n in common],
             "o-", color="#61c0bf")
gap_ax.set(title="Measured p=1 QAOA quality (no polishing)", ylabel="expected-energy gap")
prob_ax.set(xlabel="qubits", ylabel="exact-ground probability")
for axis in (gap_ax,prob_ax):
    axis.title.set_color("white"); axis.xaxis.label.set_color("white"); axis.yaxis.label.set_color("white")
quality.tight_layout()
quality.savefig(ROOT / "results" / "qaoa_quality.png", dpi=180, facecolor=quality.get_facecolor())

with (ROOT / "results" / "summary.csv").open("w", newline="") as handle:
    writer=csv.writer(handle); writer.writerow(["family","n","repeat_count","mincut_solver_median_s","mincut_end_to_end_median_s","qaoa_end_to_end_median_s","qaoa_optimizer_median_s","qaoa_one_eval_median_s","precompute_median_s","qaoa_expected_energy_gap_median","qaoa_ground_probability_median"])
    for n in classical:
        family=classical_family(n)
        repeated=groups[(family,n)]
        writer.writerow([family,n,len(repeated),median(family,n,"mincut_s"),
                         median(family,n,"graph_build_s")+median(family,n,"mincut_s"),
                         median("common",n,"graph_build_s") + median("common",n,"energy_precompute_s") + median("common",n,"qaoa_optimizer_s") if family=="common" else "",
                         median("common",n,"qaoa_optimizer_s") if family=="common" else "",
                         median("common",n,"qaoa_one_eval_s") if family=="common" else "",
                         median("common",n,"energy_precompute_s") if family=="common" else "",
                         median("common",n,"qaoa_expected_energy") - median("common",n,"exact_energy") if family=="common" else "",
                         median("common",n,"qaoa_ground_probability") if family=="common" else ""])


</cursor_untrusted_data_1337>
