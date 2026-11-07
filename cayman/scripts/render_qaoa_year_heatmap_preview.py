"""Render a real 15-year, 20-node local-QAOA probability heatmap artifact."""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import numpy as np

from paperflip.model import load_model
from paperflip.qaoa_year_sweep import compute_qaoa_year_sweep
from paperflip.region_views import nested_regions


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    base, years, _ = load_model(ROOT / "configs" / "one_region.yaml")
    selected = nested_regions(base, seed=20261106, count=1)[0]
    result = compute_qaoa_year_sweep(
        selected.model, years, region=selected.name, region_seed=20261106
    )
    artifacts = ROOT / "artifacts"
    (artifacts / "qaoa_yearly_probability_pacific_nw.json").write_text(
        json.dumps(result, indent=2) + "\n"
    )
    probability = np.array(
        [row["digital_probability_by_industry"] for row in result["rows"]]
    ).T
    years = result["years"]
    fig, ax = plt.subplots(figsize=(12, 7))
    image = ax.imshow(probability, vmin=0, vmax=1, cmap="viridis", aspect="auto")
    ax.set(
        title="QAOA digital probability by year — P(bit 0), not bit 1",
        xlabel="year", ylabel="industry", xticks=range(len(years)), xticklabels=years,
        yticks=range(selected.model.n), yticklabels=selected.model.names,
    )
    for index, marker in enumerate(result["exact_flip_markers"]):
        early, late = marker["earliest_digital_year"], marker["latest_digital_year"]
        if marker["has_exact_degeneracy"]:
            left, right = years.index(marker["degenerate_years"][0]), years.index(marker["degenerate_years"][-1])
            ax.hlines(index, left, right, color="white", linewidth=1.5)
        if marker["never_digital_through_window"]:
            ax.scatter([len(years) - 1], [index], marker=">", s=55, facecolors="none",
                       edgecolors="white", linewidths=1.4)
        elif marker["already_digital_at_window_start"]:
            ax.scatter([0], [index], marker="<", s=55, color="white", linewidths=1.4)
        elif marker["degenerate_tipping_interval"]:
            left, right = years.index(early), years.index(late)
            ax.scatter([left, right], [index, index], marker="|", s=85, color="white", linewidths=1.5)
        else:
            ax.scatter([years.index(early)], [index], marker="x", s=32, color="white", linewidths=1.4)
    ax.legend(handles=[
        Line2D([0], [0], marker="x", color="white", linestyle="None", label="exact classical flip"),
        Line2D([0], [0], color="white", linewidth=1.5, label="exact degeneracy / flip-uncertainty range"),
        Line2D([0], [0], marker="<", color="white", linestyle="None", label="already digital at 2026"),
        Line2D([0], [0], marker=">", markerfacecolor="none", color="white", linestyle="None", label="never digital through 2040"),
    ], loc="upper right", fontsize=8, framealpha=.8)
    fig.colorbar(image, ax=ax, label="QAOA statevector P(industry is digital = bit 0)")
    fig.text(.01, .01, "Independent 20-node Pacific NW local CPU statevectors; model output, not an empirical forecast or remote/hardware result.", fontsize=8)
    fig.tight_layout()
    fig.savefig(artifacts / "qaoa_yearly_probability_pacific_nw.png", dpi=160, bbox_inches="tight")
    plt.close(fig)
    print(json.dumps({
        "cpu_seconds": result["cpu_seconds"],
        "per_year_cpu_seconds": [row["cpu_seconds"] for row in result["rows"]],
        "first_year": result["rows"][0],
        "last_year": result["rows"][-1],
    }, indent=2))


if __name__ == "__main__":
    main()
