"""Render the p=1 QAOA teaching view from committed cached stage data only."""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    cache = json.loads((ROOT / "notebooks" / "data" / "independent_region_views_2033.json").read_text())
    view = next(item for item in cache["views"] if item["region"] == "Pacific NW" and item["year"] == 2033)
    records = view["fixed_configurations"]
    values = np.array([item["post_mixer_probability"] for item in records])
    exact = np.array([item["is_exact_minimum"] for item in records])
    labels = [f"C{index+1:02d}" for index in range(len(records))]
    fig = plt.figure(figsize=(12, 7))
    circuit = fig.add_subplot(2, 1, 1)
    for y in np.linspace(.18, .82, 6):
        circuit.plot([.02,.95], [y,y], color="#4e5660", lw=1)
    blocks = [
        ("Hadamards", .12, "#bfc7cf"), ("Cost $e^{-iγH_C}$", .34, "#b28af0"),
        ("Mixer $e^{-iβH_M}$", .57, "#d1b5f7"), ("Measure", .82, "#76a5ea"),
    ]
    for name, x, color in blocks:
        circuit.add_patch(plt.Rectangle((x,.1), .14, .8, facecolor=color, edgecolor="#17212b", linewidth=1.3))
        circuit.text(x+.07, .5, name, ha="center", va="center", fontsize=10)
    circuit.text(.02, .96, "20 logical wires abstracted", fontsize=9)
    circuit.text(.41, .02, "actual teaching view is p=1: one cost and one mixer block", ha="center", fontsize=9)
    circuit.set(xlim=(0,1), ylim=(0,1)); circuit.axis("off")
    plot = fig.add_subplot(2, 1, 2)
    plot.bar(range(len(records)), values, color="#457b9d")
    plot.scatter(np.where(exact)[0], values[exact], color="#e63946", marker="*", s=80, label="exact minimum")
    mass = view["stages"]["post_mixer"]
    plot.set(
        title=f"Actual cached post-mixer probabilities; included={mass['included_mass']:.3e}, omitted={mass['omitted_mass']:.3e}",
        xticks=range(len(records)), xticklabels=labels, ylabel="P(configuration)",
    )
    plot.legend()
    fig.text(.01, .01, f"Pacific NW 2033 cached local CPU statevector; p=1 grid selected γ={view['optimization']['gamma']}, β={view['optimization']['beta']}. "
             "C01… are a fixed, non-renormalized subset of the 2²⁰ configurations.", fontsize=8)
    fig.tight_layout()
    fig.savefig(ROOT / "artifacts" / "qaoa_p1_walkthrough_pacific_nw_2033.png", dpi=160, bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    main()
