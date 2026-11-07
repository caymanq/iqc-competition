"""Render a bounded, real 20-node p=1-QAOA landscape preview for the handoff."""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from paperflip.model import load_model
from paperflip.qaoa_landscape import compute_qaoa_landscape
from paperflip.region_views import nested_regions


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    base, _, _ = load_model(ROOT / "configs" / "one_region.yaml")
    scenario = nested_regions(base, seed=20261106, count=1)[0]
    gamma = np.linspace(-np.pi, np.pi, 5)
    beta = np.linspace(0.0, np.pi / 2, 5)
    result = compute_qaoa_landscape(scenario.model, 2033, gamma, beta)
    result["region"] = scenario.name
    result["assumption"] = "Independent 20-node region; no cross-region ties."

    output = ROOT / "artifacts"
    (output / "qaoa_landscape_pacific_nw_2033.json").write_text(json.dumps(result, indent=2) + "\n")
    energy = np.array(result["expected_energy_model_units"])
    gradient = np.array(result["gradient_norm_model_units_per_radian"])
    G, B = np.meshgrid(gamma, beta)
    selected = result["selected_grid_minimum"]
    fig = plt.figure(figsize=(12, 4.5))
    ax = fig.add_subplot(1, 2, 1, projection="3d")
    norm = plt.Normalize(gradient.min(), gradient.max() if gradient.max() > gradient.min() else gradient.min() + 1)
    ax.plot_surface(G, B, energy, facecolors=plt.cm.viridis(norm(gradient)), shade=False)
    ax.scatter([selected["gamma"]], [selected["beta"]], [selected["expected_energy_model_units"]],
               color="#e63946", s=55, label="selected grid angle")
    ax.set(xlabel="γ", ylabel="β", zlabel="expected energy",
           title="Actual 20-node p=1 QAOA energy")
    ax.legend()
    mapper = plt.cm.ScalarMappable(norm=norm, cmap="viridis")
    mapper.set_array(gradient)
    fig.colorbar(mapper, ax=ax, pad=.1, label="||∇E||")
    contour = fig.add_subplot(1, 2, 2)
    levels = min(12, len(gamma) + 3)
    filled = contour.contourf(G, B, energy, levels=levels, cmap="cividis")
    contour.contour(G, B, gradient, colors="white", linewidths=.7)
    contour.scatter([selected["gamma"]], [selected["beta"]], color="#e63946", marker="*", s=100)
    contour.set(xlabel="γ", ylabel="β", title="Energy; white = gradient contours")
    fig.colorbar(filled, ax=contour, label="expected energy")
    fig.suptitle("Pacific NW, 2033 — local CPU statevector; QAOA not DQA / qBraid / hardware", y=1.02)
    fig.tight_layout()
    fig.savefig(output / "qaoa_landscape_pacific_nw_2033.png", dpi=160, bbox_inches="tight")
    plt.close(fig)
    print(json.dumps({"cpu_seconds": result["cpu_seconds"], "selected_grid_minimum": selected}, indent=2))


if __name__ == "__main__":
    main()
