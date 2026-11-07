"""Run bounded p=2 constrained target-selection QAOA and render adoption overlays.

The Pacific-NW adoption heatmap is a saved, independent 20-node p=1 QAOA
result with digital=bit 0.  Target selection is a five-region optimization
reduced to industry choices with selected=bit 1.  The plots deliberately
overlay markers without mixing those two probabilities into a shared scale.
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
import time

import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import matplotlib.patheffects as path_effects
import numpy as np

from run_constrained_target_qaoa import (
    ANGLE_BETAS, ANGLE_GAMMAS, BUDGET, INPUT, RANDOM_SEED, YEARS,
    apply_xy_mixer, basis_masks, eligible_candidates, exact, load_rows,
    pair_maps, reduce_industries,
)


ROOT = Path(__file__).resolve().parents[1]
P1 = ROOT / "results" / "target_selection_qaoa_4year" / "yearly_results.json"
ADOPTION = ROOT / "artifacts" / "qaoa_yearly_probability_pacific_nw.json"
OUT = ROOT / "results" / "target_selection_qaoa_p2_4year"


def plan_arrays(values: np.ndarray, masks: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    selected = ((masks[:, None] >> np.arange(len(values))) & 1).astype(float)
    return selected, selected @ values


def apply_layers(
    values: np.ndarray, masks: np.ndarray, maps: list[tuple[np.ndarray, np.ndarray]],
    gammas: tuple[float, ...], betas: tuple[float, ...], optimum: float,
) -> dict:
    """p-layer cost then fixed-order XY mixer, starting uniform over feasible plans."""
    if len(gammas) != len(betas):
        raise ValueError("each cost angle requires a mixer angle")
    selected, plan_values = plan_arrays(values, masks)
    state = np.ones(len(masks), dtype=np.complex128) / np.sqrt(len(masks))
    for gamma, beta in zip(gammas, betas):
        # H_C=-value; U_C=e^-i gamma H_C = exp(+i gamma value).
        state *= np.exp(1j * gamma * plan_values)
        state = apply_xy_mixer(state, maps, beta)
    probability = np.abs(state) ** 2
    mode = int(np.argmax(probability))
    return {
        "expected_value": float(probability @ plan_values),
        "optimum_probability_all_ties": float(probability[np.isclose(plan_values, optimum)].sum()),
        "marginals": (probability @ selected).tolist(),
        "normalization": float(probability.sum()),
        "feasibility_mass": float(probability.sum()),
        "mode_mask": int(masks[mode]),
        "mode_selected": selected[mode].astype(int).tolist(),
        "mode_probability": float(probability[mode]),
        "mode_value": float(plan_values[mode]),
        "mode_value_gap": float(optimum - plan_values[mode]),
    }


def solve_p2_year(rows: list[dict], year: int) -> dict:
    items = reduce_industries(eligible_candidates(rows, year))
    if not items:
        return {"year": year, "status": "no_eligible_candidates", "items": [], "k": 0, "basis_dimension": 0}
    n, k = len(items), min(BUDGET, len(items))
    values = np.array([item.value for item in items])
    setup_started = time.perf_counter()
    masks = basis_masks(n, k)
    optimum, representative, tie_count = exact(values, masks)
    maps = pair_maps(masks, n)
    setup_seconds = time.perf_counter() - setup_started
    selected, plan_values = plan_arrays(values, masks)
    tied_industry_sets = [
        [items[index].industry for index, picked in enumerate(selection) if picked]
        for selection in selected[np.isclose(plan_values, optimum)].astype(int)
    ]

    # A full deterministic 5^4 grid. It contains (gamma_1,beta_1,0,0), the
    # p=1 identity-layer embedding, so p=2 selection cannot regress from it.
    started = time.perf_counter()
    best = None
    incumbent = None
    for gamma_1 in ANGLE_GAMMAS:
        for gamma_2 in ANGLE_GAMMAS:
            for beta_1 in ANGLE_BETAS:
                for beta_2 in ANGLE_BETAS:
                    candidate = apply_layers(
                        values, masks, maps, (float(gamma_1), float(gamma_2)),
                        (float(beta_1), float(beta_2)), optimum,
                    )
                    tagged = {**candidate, "gamma_1": float(gamma_1), "gamma_2": float(gamma_2),
                              "beta_1": float(beta_1), "beta_2": float(beta_2)}
                    if gamma_2 == 0 and beta_2 == 0 and (
                        incumbent is None or tagged["expected_value"] > incumbent["expected_value"]
                    ):
                        incumbent = tagged
                    if best is None or tagged["expected_value"] > best["expected_value"]:
                        best = tagged
    assert best is not None and incumbent is not None
    if best["expected_value"] + 1e-12 < incumbent["expected_value"]:
        raise AssertionError("p=2 grid omitted its p=1 identity-layer incumbent")
    return {
        "year": year, "status": "completed", "items": [item.__dict__ for item in items],
        "k": k, "basis_dimension": int(len(masks)), "xy_mixer_pair_gates_per_layer": len(maps),
        "exact_optimum_value": optimum, "exact_representative_selection": representative.astype(int).tolist(),
        "exact_tied_industry_plans": tie_count, "exact_tied_industry_sets": tied_industry_sets, "p2": best,
        "p1_identity_layer_incumbent": incumbent,
        "optimizer_evaluations": len(ANGLE_GAMMAS) ** 2 * len(ANGLE_BETAS) ** 2,
        "optimizer_seconds": time.perf_counter() - started,
        "basis_and_mixer_map_seconds": setup_seconds,
        "uniform_feasible_expected_value": float(k / n * values.sum()),
    }


def industry_matrix(results: list[dict], industries: list[str], source: str) -> np.ndarray:
    output = np.full((len(industries), len(YEARS)), np.nan)
    index = {name: position for position, name in enumerate(industries)}
    for column, result in enumerate(results):
        if result["status"] != "completed":
            continue
        for position, item in enumerate(result["items"]):
            row = index[item["industry"]]
            output[row, column] = (
                result["p2"]["marginals"][position] if source == "p2"
                else result["exact_representative_selection"][position]
            )
    return output


def _style_axis(ax: plt.Axes, industries: list[str]) -> None:
    ax.set_facecolor("white")
    ax.set(xlabel="planning year", ylabel="industry", xticks=range(len(YEARS)), xticklabels=YEARS,
           yticks=range(len(industries)), yticklabels=industries)
    ax.tick_params(colors="black")
    ax.xaxis.label.set_color("black"); ax.yaxis.label.set_color("black")
    for spine in ax.spines.values():
        spine.set_color("black")


def _adoption_background() -> tuple[np.ndarray, list[str], list[dict]]:
    saved = json.loads(ADOPTION.read_text())
    # The saved artifact is authoritative for its probabilities, names, and
    # flip markers; this script does not rerun the adoption calculation.
    markers = saved["exact_flip_markers"]
    return (np.array([row["digital_probability_by_industry"] for row in saved["rows"]]).T,
            [marker["industry"] for marker in markers], markers)


def draw_adoption(ax: plt.Axes, probability: np.ndarray, industries: list[str], flip_markers: list[dict]) -> None:
    image = ax.imshow(probability, vmin=0, vmax=1, cmap="viridis", aspect="auto")
    _style_axis(ax, industries)
    for index, marker in enumerate(flip_markers):
        early, late = marker["earliest_digital_year"], marker["latest_digital_year"]
        if marker["has_exact_degeneracy"]:
            left, right = YEARS.index(marker["degenerate_years"][0]), YEARS.index(marker["degenerate_years"][-1])
            ax.hlines(index, left, right, color="white", linewidth=1.5, zorder=4)
        if marker["never_digital_through_window"]:
            ax.scatter([len(YEARS) - 1], [index], marker=">", s=55, facecolors="none",
                       edgecolors="white", linewidths=1.4, zorder=5)
        elif marker["already_digital_at_window_start"]:
            ax.scatter([0], [index], marker="<", s=55, color="white", linewidths=1.4, zorder=5)
        elif marker["degenerate_tipping_interval"]:
            ax.scatter([YEARS.index(early), YEARS.index(late)], [index, index], marker="|", s=85,
                       color="white", linewidths=1.5, zorder=5)
        else:
            ax.scatter([YEARS.index(early)], [index], marker="x", s=32, color="white", linewidths=1.4, zorder=5)
    return image


def draw_adoption_flip_context(ax: plt.Axes, flip_markers: list[dict]) -> None:
    """Draw saved adoption flip annotations without plotting adoption probability."""
    white_outline = [path_effects.Stroke(linewidth=2.4, foreground="black"), path_effects.Normal()]
    for index, marker in enumerate(flip_markers):
        early, late = marker["earliest_digital_year"], marker["latest_digital_year"]
        if marker["has_exact_degeneracy"]:
            left, right = YEARS.index(marker["degenerate_years"][0]), YEARS.index(marker["degenerate_years"][-1])
            line = ax.hlines(index, left, right, color="white", linewidth=1.5, zorder=4)
            line.set_path_effects(white_outline)
        if marker["never_digital_through_window"]:
            ax.scatter([len(YEARS) - 1], [index], marker=">", s=55, facecolors="none",
                       edgecolors="white", linewidths=1.4, zorder=5, path_effects=white_outline)
        elif marker["already_digital_at_window_start"]:
            ax.scatter([0], [index], marker="<", s=55, color="white", linewidths=1.4,
                       zorder=5, path_effects=white_outline)
        elif marker["degenerate_tipping_interval"]:
            ax.scatter([YEARS.index(early), YEARS.index(late)], [index, index], marker="|", s=85,
                       color="white", linewidths=1.5, zorder=5, path_effects=white_outline)
        else:
            ax.scatter([YEARS.index(early)], [index], marker="x", s=32, color="white", linewidths=1.4,
                       zorder=5, path_effects=white_outline)


def overlay_target_markers(
    ax: plt.Axes, results: list[dict], adoption_industries: list[str], *, p2_circles: bool,
) -> None:
    target_row = {name: row for row, name in enumerate(adoption_industries)}
    for column, result in enumerate(results):
        if result["status"] != "completed":
            continue
        for position, item in enumerate(result["items"]):
            row = target_row[item["industry"]]
            if result["exact_representative_selection"][position]:
                # BLACK x is the exact target-selection recommendation, distinct
                # from the WHITE x used for adoption flip-year markers.
                ax.scatter(column, row, marker="x", s=82, color="black", linewidths=2.0, zorder=8)
            if p2_circles:
                marginal = result["p2"]["marginals"][position]
                ax.scatter(column, row, marker="o", s=20 + 260 * marginal, facecolors="none",
                           edgecolors="#d81b60", linewidths=1.8, zorder=6)
        if p2_circles:
            chosen = result["p2"]["mode_selected"]
            for position, is_selected in enumerate(chosen):
                if is_selected:
                    ax.scatter(column, target_row[result["items"][position]["industry"]], marker="s", s=92,
                               facecolors="none", edgecolors="black", linewidths=1.5, zorder=7)


def plot_overlay(results: list[dict]) -> None:
    probability, adoption_industries, flips = _adoption_background()
    # Reserve a dedicated right-hand column for the legend.  In particular,
    # never attach it to an axes whose colorbar can cover the legend text.
    fig = plt.figure(figsize=(25, 8), facecolor="white")
    grid = fig.add_gridspec(1, 3, width_ratios=(1, 1, .43), wspace=.16)
    left = fig.add_subplot(grid[0, 0])
    right = fig.add_subplot(grid[0, 1], sharey=left)
    legend_axis = fig.add_subplot(grid[0, 2])
    legend_axis.axis("off")
    fig.patch.set_facecolor("white")
    image = draw_adoption(left, probability, adoption_industries, flips)
    overlay_target_markers(left, results, adoption_industries, p2_circles=False)
    left.set_title("Saved Pacific NW adoption + exact target choices", color="black")
    image = draw_adoption(right, probability, adoption_industries, flips)
    overlay_target_markers(right, results, adoption_industries, p2_circles=True)
    right.set_title("Saved adoption + p=2 target marginals and feasible MAP plan", color="black")
    cbar = fig.colorbar(image, ax=(left, right), fraction=.028, pad=.025,
                        label="Saved Pacific NW QAOA P(industry digital = bit 0)")
    cbar.ax.yaxis.label.set_color("black"); cbar.ax.tick_params(colors="black")
    legend = [
        Line2D([0], [0], marker="x", color="white", linestyle="None", label="adoption exact flip year"),
        Line2D([0], [0], marker="x", color="black", linestyle="None", markersize=8,
               label="exact target recommendation (representative; tied alternatives in CSV)"),
        Line2D([0], [0], marker="o", color="#d81b60", fillstyle="none", linestyle="None", markersize=8,
               label="p=2 target P(selected bit 1): circle area"),
        Line2D([0], [0], marker="s", color="black", fillstyle="none", linestyle="None", markersize=8,
               label="p=2 feasible MAP-plan recommendation"),
    ]
    legend_axis.legend(handles=legend, loc="upper left", fontsize=10, framealpha=.95)
    legend_axis.text(.02, .50, "Exact tied industry sets and tied-best\nregional alternatives are recorded in\n"
                     "yearly_metrics.csv and yearly_recommendations.csv.", color="black", fontsize=10,
                     va="top", transform=legend_axis.transAxes)
    fig.text(.01, .01,
             "Background: unchanged independent Pacific NW adoption (digital = bit 0). Markers: five-region "
             "target-selection optimization (selected = bit 1), placed at planning year. 2035–2040 have no eligible targets.",
             color="black", fontsize=9)
    fig.tight_layout(rect=(0, .04, 1, 1))
    for suffix in ("png", "svg"):
        fig.savefig(OUT / f"adoption_target_selection_overlay_panels.{suffix}", dpi=220, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def plot_main_overlay(results: list[dict]) -> None:
    """Produce a readable single-panel attachment in addition to the pair."""
    probability, adoption_industries, flips = _adoption_background()
    # A distinct legend column prevents the colorbar from obscuring key text.
    fig = plt.figure(figsize=(17, 8), facecolor="white")
    grid = fig.add_gridspec(1, 2, width_ratios=(1, .42), wspace=.22)
    ax = fig.add_subplot(grid[0, 0])
    legend_axis = fig.add_subplot(grid[0, 1])
    legend_axis.axis("off")
    fig.patch.set_facecolor("white")
    image = draw_adoption(ax, probability, adoption_industries, flips)
    overlay_target_markers(ax, results, adoption_industries, p2_circles=True)
    ax.set_title("Saved Pacific NW adoption background + p=2 target-selection overlay", color="black")
    cbar = fig.colorbar(image, ax=ax, label="Saved Pacific NW QAOA P(industry digital = bit 0)")
    cbar.ax.yaxis.label.set_color("black"); cbar.ax.tick_params(colors="black")
    legend_axis.legend(handles=[
        Line2D([0], [0], marker="x", color="white", linestyle="None", label="adoption exact flip year"),
        Line2D([0], [0], marker="x", color="black", linestyle="None", markersize=8,
               label="exact target recommendation (representative; tied alternatives in CSV)"),
        Line2D([0], [0], marker="o", color="#d81b60", fillstyle="none", linestyle="None", markersize=8,
               label="p=2 target P(selected bit 1): circle area"),
        Line2D([0], [0], marker="s", color="black", fillstyle="none", linestyle="None", markersize=8,
               label="p=2 feasible MAP-plan recommendation"),
    ], loc="upper left", fontsize=10, framealpha=.95)
    legend_axis.text(.02, .49, "Exact tied industry sets and tied-best\nregional alternatives are recorded in\n"
                     "yearly_metrics.csv and yearly_recommendations.csv.", color="black", fontsize=10,
                     va="top", transform=legend_axis.transAxes)
    fig.text(.01, .01,
             "Background: unchanged independent Pacific NW adoption (digital = bit 0). Markers: five-region "
             "target-selection optimization (selected = bit 1), placed at planning year. 2035–2040 have no eligible targets.",
             color="black", fontsize=9)
    fig.tight_layout(rect=(0, .04, 1, 1))
    for suffix in ("png", "svg"):
        fig.savefig(OUT / f"adoption_target_selection_overlay.{suffix}", dpi=220, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def target_values_on_adoption_axes(results: list[dict]) -> tuple[np.ndarray, np.ndarray, list[str], list[dict]]:
    """Return exact and p=2 target values aligned to the saved adoption rows."""
    _, adoption_industries, flips = _adoption_background()
    index = {name: row for row, name in enumerate(adoption_industries)}
    exact_values = np.full((len(adoption_industries), len(YEARS)), np.nan)
    quantum_values = np.full_like(exact_values, np.nan)
    for column, result in enumerate(results):
        if result["status"] != "completed":
            continue
        for position, item in enumerate(result["items"]):
            row = index[item["industry"]]
            exact_values[row, column] = result["exact_representative_selection"][position]
            quantum_values[row, column] = result["p2"]["marginals"][position]
    return exact_values, quantum_values, adoption_industries, flips


def _draw_target_foreground(
    ax: plt.Axes, values: np.ndarray, industries: list[str], flips: list[dict],
    *, title: str, cmap_name: str, colorbar_label: str, discrete: bool,
) -> tuple[object, np.ndarray]:
    cmap = plt.get_cmap(cmap_name).copy()
    cmap.set_bad("#d9d9d9")
    image = ax.imshow(values, aspect="auto", cmap=cmap, vmin=0, vmax=1,
                      interpolation="nearest")
    _style_axis(ax, industries)
    ax.set_title(title, color="black")
    # White adoption markers are context only. A black outline keeps their
    # white center visible on either target foreground palette.
    draw_adoption_flip_context(ax, flips)
    exact_mask = np.isclose(values, 1.0) if discrete else None
    return image, exact_mask


def plot_distinct_target_heatmaps(results: list[dict]) -> None:
    """Render classical and p=2 values without blending them with adoption P."""
    exact_values, quantum_values, industries, flips = target_values_on_adoption_axes(results)
    shared_black_mask = np.isclose(exact_values, 1.0)
    # The exact selection mask is intentionally the same reference layer in
    # both plots, not an assertion that p=2 returns the same feasible plan.
    classical_mask = np.isclose(exact_values, 1.0)
    quantum_reference_mask = np.isclose(exact_values, 1.0)
    assert np.array_equal(classical_mask, quantum_reference_mask)
    assert not np.allclose(exact_values[~np.isnan(exact_values)], quantum_values[~np.isnan(quantum_values)])

    def draw_shared_crosses(ax: plt.Axes) -> None:
        rows, columns = np.where(shared_black_mask)
        ax.scatter(columns, rows, marker="x", s=82, color="black", linewidths=2.0, zorder=8)

    specs = [
        (exact_values, "Exact classical target selection over adoption flip context",
         "target_classical_over_adoption_context", "YlGnBu",
         "Exact target selection xᵢ (bit 1); representative tied optimum"),
        (quantum_values, "p=2 QAOA target marginal over adoption flip context",
         "target_p2_over_adoption_context", "magma",
         "Ideal p=2 QAOA P(target selected = bit 1)"),
    ]
    for values, title, filename, cmap, label in specs:
        fig = plt.figure(figsize=(17, 8), facecolor="white")
        grid = fig.add_gridspec(1, 2, width_ratios=(1, .42), wspace=.22)
        ax = fig.add_subplot(grid[0, 0])
        legend_axis = fig.add_subplot(grid[0, 1])
        legend_axis.axis("off")
        fig.patch.set_facecolor("white")
        image, _ = _draw_target_foreground(ax, values, industries, flips, title=title, cmap_name=cmap,
                                             colorbar_label=label, discrete=values is exact_values)
        draw_shared_crosses(ax)
        cbar = fig.colorbar(image, ax=ax, label=label)
        cbar.ax.tick_params(colors="black"); cbar.ax.yaxis.label.set_color("black")
        legend_axis.legend(handles=[
            Line2D([0], [0], marker="x", color="white", markeredgewidth=1.5, markeredgecolor="black",
                   linestyle="None", label="saved Pacific NW adoption exact flip"),
            Line2D([0], [0], marker="x", color="black", linestyle="None",
                   label="shared exact target recommendation"),
        ], loc="upper left", fontsize=10, framealpha=.95)
        legend_axis.text(.02, .52,
                         "The black × positions are intentionally\nidentical in both heatmaps: they are\n"
                         "the exact reference, not a claim that\np=2 returns the same MAP plan.\n\n"
                         "Tied industry sets and tied-best\nregional alternatives are in the CSV.",
                         color="black", fontsize=10, va="top", transform=legend_axis.transAxes)
        fig.text(.01, .01,
                 "Cell color is target selection only: classical left value is exact xᵢ; quantum value is p=2 "
                 "P(xᵢ=1). White markers are saved Pacific NW adoption flip context, not cell values. "
                 "Black × is the same exact feasible target recommendation in both plots; ties are in CSV.",
                 color="black", fontsize=8)
        fig.tight_layout(rect=(0, .04, 1, 1))
        for suffix in ("png", "svg"):
            fig.savefig(OUT / f"{filename}.{suffix}", dpi=220, bbox_inches="tight", facecolor="white")
        plt.close(fig)

    # The requested aligned comparison: intentionally separate colorbars and
    # palettes, because one panel is a binary exact selection and the other is
    # a quantum marginal probability.
    fig = plt.figure(figsize=(25, 8), facecolor="white")
    grid = fig.add_gridspec(1, 3, width_ratios=(1, 1, .38), wspace=.17)
    left = fig.add_subplot(grid[0, 0])
    right = fig.add_subplot(grid[0, 1], sharey=left)
    legend_axis = fig.add_subplot(grid[0, 2])
    legend_axis.axis("off")
    axes = (left, right)
    fig.patch.set_facecolor("white")
    first, _ = _draw_target_foreground(
        axes[0], exact_values, industries, flips,
        title="Classical: exact target selection", cmap_name="YlGnBu",
        colorbar_label="Exact xᵢ (bit 1)", discrete=True,
    )
    second, _ = _draw_target_foreground(
        axes[1], quantum_values, industries, flips,
        title="Quantum: p=2 target-selection marginal", cmap_name="magma",
        colorbar_label="p=2 P(xᵢ=1)", discrete=False,
    )
    draw_shared_crosses(axes[0]); draw_shared_crosses(axes[1])
    for image, axis, label in [(first, axes[0], "Exact xᵢ (bit 1)"), (second, axes[1], "p=2 P(xᵢ=1)")]:
        cbar = fig.colorbar(image, ax=axis, fraction=.046, pad=.04, label=label)
        cbar.ax.tick_params(colors="black"); cbar.ax.yaxis.label.set_color("black")
    legend_axis.legend(handles=[
        Line2D([0], [0], marker="x", color="white", markeredgewidth=1.5, markeredgecolor="black",
               linestyle="None", label="saved Pacific NW adoption exact flip"),
        Line2D([0], [0], marker="x", color="black", linestyle="None",
               label="shared exact target recommendation"),
    ], loc="upper left", fontsize=9, framealpha=.95)
    legend_axis.text(.02, .52, "Black × positions are identical\nexact-reference targets in both\n"
                     "panels. They do not claim p=2\nreturns the same MAP plan.\n\n"
                     "Tied sets and tied-best regions\nare recorded in the CSV.",
                     color="black", fontsize=10, va="top", transform=legend_axis.transAxes)
    fig.text(.01, .01,
             "No adoption and target probabilities are blended. Left foreground is exact target xᵢ; right is p=2 "
             "target marginal P(xᵢ=1). White flip markers provide saved adoption context. Black × mask is identical.",
             color="black", fontsize=9)
    fig.tight_layout(rect=(0, .04, 1, 1))
    for suffix in ("png", "svg"):
        fig.savefig(OUT / f"target_classical_vs_p2_over_adoption_context.{suffix}",
                    dpi=220, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def plot_target_heatmaps(results: list[dict], industries: list[str], p1_results: list[dict]) -> None:
    p2 = industry_matrix(results, industries, "p2")
    p1 = np.full_like(p2, np.nan)
    lookup = {name: row for row, name in enumerate(industries)}
    for column, result in enumerate(p1_results):
        if result["status"] == "completed":
            for position, item in enumerate(result["items"]):
                p1[lookup[item["industry"]], column] = result["qaoa"]["marginals"][position]
    for data, title, filename, cmap, limits, label in [
        (p2, "Constrained p=2 target-selection marginal", "p2_selection_marginal_heatmap.png", "viridis", (0, 1), "P(industry selected; bit 1)"),
        (p2 - p1, "p=2 minus p=1 target-selection marginal", "p2_minus_p1_marginal_heatmap.png", "coolwarm", (-.5, .5), "P(selected) difference"),
    ]:
        fig, ax = plt.subplots(figsize=(12, 7), facecolor="white")
        fig.patch.set_facecolor("white"); ax.set_facecolor("white")
        cmap_object = plt.get_cmap(cmap).copy(); cmap_object.set_bad("#e6e6e6")
        norm = None
        if limits[0] < 0:
            from matplotlib.colors import TwoSlopeNorm
            norm = TwoSlopeNorm(vcenter=0, vmin=limits[0], vmax=limits[1])
        image = ax.imshow(data, aspect="auto", cmap=cmap_object, vmin=None if norm else limits[0],
                          vmax=None if norm else limits[1], norm=norm)
        _style_axis(ax, industries); ax.set_title(title, color="black")
        cbar = fig.colorbar(image, ax=ax, label=label); cbar.ax.tick_params(colors="black")
        cbar.ax.yaxis.label.set_color("black")
        fig.text(.01, .01, "Gray = ineligible/no eligible candidates; target-selection bit 1 only. Local ideal statevector, not shots or hardware.",
                 color="black", fontsize=8)
        fig.tight_layout()
        fig.savefig(OUT / filename, dpi=220, bbox_inches="tight", facecolor="white")
        plt.close(fig)


def write_outputs(results: list[dict], industries: list[str]) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    p1 = json.loads(P1.read_text())["results"]
    p1_by_year = {result["year"]: result for result in p1}
    payload = {
        "source": "local ideal constrained feasible-subspace p=2 QAOA; no provider/hardware",
        "bit_convention": "target selection bit 1 = selected; separate from adoption digital bit 0",
        "reduction": "objective-equivalent best-region-per-industry; tied regions retained, not regional QAOA marginals",
        "optimizer": {"depth": 2, "gamma_grid": ANGLE_GAMMAS.tolist(), "beta_grid": ANGLE_BETAS.tolist(),
                      "evaluations_per_completed_year": 625, "seed": RANDOM_SEED,
                      "p1_incumbent": "identity second layer (gamma_2=beta_2=0) included in grid"},
        "results": results,
    }
    (OUT / "yearly_results.json").write_text(json.dumps(payload, indent=2) + "\n")
    metrics, recommendations = [], []
    for result in results:
        row = {"year": result["year"], "status": result["status"], "eligible_industries": len(result["items"]),
               "k": result["k"], "basis_dimension": result["basis_dimension"]}
        if result["status"] == "completed":
            p2 = result["p2"]
            row.update(exact_optimum_value=result["exact_optimum_value"], p2_expected_value=p2["expected_value"],
                       p2_gap=result["exact_optimum_value"] - p2["expected_value"],
                       p2_ratio=p2["expected_value"] / result["exact_optimum_value"],
                       p2_optimum_probability_all_ties=p2["optimum_probability_all_ties"],
                       p2_feasibility_mass=p2["feasibility_mass"], p2_marginal_sum=sum(p2["marginals"]),
                       p2_gamma_1=p2["gamma_1"], p2_beta_1=p2["beta_1"], p2_gamma_2=p2["gamma_2"], p2_beta_2=p2["beta_2"],
                       p2_mode_probability=p2["mode_probability"], p2_mode_value=p2["mode_value"],
                       p2_mode_value_gap=p2["mode_value_gap"], p2_optimizer_seconds=result["optimizer_seconds"],
                       p2_evaluations=result["optimizer_evaluations"], p1_identity_expected_value=result["p1_identity_layer_incumbent"]["expected_value"],
                       p1_expected_value=p1_by_year[result["year"]]["qaoa"]["expected_value"],
                       p1_ratio=p1_by_year[result["year"]]["qaoa"]["expected_value"] / result["exact_optimum_value"],
                       uniform_feasible_expected_value=result["uniform_feasible_expected_value"],
                       exact_tied_industry_plans=result["exact_tied_industry_plans"],
                       exact_tied_industry_sets=json.dumps(result["exact_tied_industry_sets"]))
            for position, item in enumerate(result["items"]):
                recommendations.append({
                    "year": result["year"], "industry": item["industry"], "value": item["value"],
                    "representative_or_tied_best_regions": "|".join(item["regions"]),
                    "exact_representative_recommended": result["exact_representative_selection"][position],
                    "p2_marginal_selected_bit_1": p2["marginals"][position],
                    "p2_map_feasible_recommended": p2["mode_selected"][position],
                    "p2_map_plan_probability": p2["mode_probability"], "p2_map_plan_value": p2["mode_value"],
                    "p2_map_plan_value_gap_to_exact": p2["mode_value_gap"],
                })
        metrics.append(row)
    for name, records in [("yearly_metrics.csv", metrics), ("yearly_recommendations.csv", recommendations)]:
        with (OUT / name).open("w", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(records[0]))
            writer.writeheader(); writer.writerows(records)
    plot_target_heatmaps(results, industries, p1)
    plot_overlay(results)
    plot_main_overlay(results)
    plot_distinct_target_heatmaps(results)


def tests() -> None:
    values = np.array([4.0, 2.0, 1.0])
    masks = basis_masks(3, 2); maps = pair_maps(masks, 3); optimum, _, _ = exact(values, masks)
    one = apply_layers(values, masks, maps, (.21,), (.17,), optimum)
    embedded = apply_layers(values, masks, maps, (.21, 0.0), (.17, 0.0), optimum)
    assert np.isclose(one["expected_value"], embedded["expected_value"])
    assert np.allclose(one["marginals"], embedded["marginals"])
    two = apply_layers(values, masks, maps, (.21, .13), (.17, .09), optimum)
    assert np.isclose(two["normalization"], 1) and np.isclose(two["feasibility_mass"], 1)
    assert np.isclose(sum(two["marginals"]), 2)  # every basis state has cardinality k=2


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--test", action="store_true")
    parser.add_argument("--render-only", action="store_true",
                        help="re-render saved p=2 overlays only; never evaluates a circuit")
    args = parser.parse_args(argv)
    tests()
    if args.test:
        print("p=2 constrained-QAOA checks passed")
        return
    if args.render_only:
        saved = json.loads((OUT / "yearly_results.json").read_text())["results"]
        plot_overlay(saved)
        plot_main_overlay(saved)
        plot_distinct_target_heatmaps(saved)
        print(f"Re-rendered saved overlays in {OUT}; no simulation evaluated")
        return
    rows = load_rows(INPUT / "quantum_flip_years.csv")
    industries = sorted({row["industry"] for row in rows})
    started = time.perf_counter()
    results = [solve_p2_year(rows, year) for year in YEARS]
    write_outputs(results, industries)
    print(json.dumps({"output": str(OUT), "total_seconds": time.perf_counter() - started,
                      "completed_years": sum(row["status"] == "completed" for row in results)}, indent=2))


if __name__ == "__main__":
    main()
