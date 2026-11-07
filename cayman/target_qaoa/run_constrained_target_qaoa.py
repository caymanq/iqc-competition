"""Local constrained-QAOA study for the supplied four-year target-selection inputs.

This is an optimization-equivalent industry reduction for the documented
equal-cost/no-bonus model, not a distribution-equivalent simulation of the
full regional QUBO. Bit 1 means an industry is TARGET SELECTED here.
"""
from __future__ import annotations

import csv
from dataclasses import dataclass
from itertools import combinations
import json
from math import comb
from pathlib import Path
import time
from typing import Iterable
import argparse

import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap, TwoSlopeNorm
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "results" / "supplied_user_results_20261107" / "target_selection_4year"
OUT = ROOT / "results" / "target_selection_qaoa_4year"
YEARS = list(range(2026, 2041))
LEAD_TIME_YEARS, BUDGET, BASE_VALUE = 4, 5, 8.0
ANGLE_GAMMAS = np.linspace(0.0, 0.35, 5)
ANGLE_BETAS = np.linspace(0.0, 0.35, 5)
RANDOM_SEED = 20261107


@dataclass(frozen=True)
class ReducedItem:
    industry: str
    value: float
    regions: tuple[str, ...]
    flip_year: int


def load_rows(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return [
            {"industry": row["industry"], "region": row["region"],
             "base_resistance": float(row["base_resistance"]), "flip_year": int(row["flip_year"])}
            for row in csv.DictReader(handle)
        ]


def eligible_candidates(rows: Iterable[dict], year: int) -> list[dict]:
    candidates = []
    for row in rows:
        remaining = row["flip_year"] - year
        if 1 <= remaining <= LEAD_TIME_YEARS:
            urgency = (LEAD_TIME_YEARS + 1 - remaining) / LEAD_TIME_YEARS
            candidates.append({**row, "value": BASE_VALUE * (1 - row["base_resistance"]) * urgency})
    return candidates


def reduce_industries(candidates: Iterable[dict]) -> list[ReducedItem]:
    """Losslessly reduce regional alternatives for objective optimization only."""
    grouped: dict[str, list[dict]] = {}
    for candidate in candidates:
        grouped.setdefault(candidate["industry"], []).append(candidate)
    reduced = []
    for industry, choices in grouped.items():
        value = max(choice["value"] for choice in choices)
        tied = [choice for choice in choices if np.isclose(choice["value"], value)]
        reduced.append(ReducedItem(industry, value, tuple(choice["region"] for choice in tied), tied[0]["flip_year"]))
    return sorted(reduced, key=lambda item: item.industry)


def basis_masks(n: int, k: int) -> np.ndarray:
    return np.array([sum(1 << i for i in choice) for choice in combinations(range(n), k)], dtype=np.uint32)


def pair_maps(masks: np.ndarray, n: int) -> list[tuple[np.ndarray, np.ndarray]]:
    lookup = {int(mask): index for index, mask in enumerate(masks)}
    maps = []
    for left in range(n):
        for right in range(left + 1, n):
            source, target = [], []
            for index, mask in enumerate(masks):
                if ((mask >> left) & 1) and not ((mask >> right) & 1):
                    source.append(index)
                    target.append(lookup[int(mask ^ (1 << left) ^ (1 << right))])
            maps.append((np.asarray(source, dtype=np.int32), np.asarray(target, dtype=np.int32)))
    return maps


def apply_xy_mixer(state: np.ndarray, maps: list[tuple[np.ndarray, np.ndarray]], beta: float) -> np.ndarray:
    """One fixed-order first-order XY product formula; it preserves cardinality."""
    out = state.copy()
    cosine, sine = np.cos(beta), np.sin(beta)
    for left, right in maps:
        a, b = out[left].copy(), out[right].copy()
        out[left] = cosine * a - 1j * sine * b
        out[right] = cosine * b - 1j * sine * a
    return out


def evaluate(values: np.ndarray, masks: np.ndarray, maps: list[tuple[np.ndarray, np.ndarray]],
             gamma: float, beta: float, optimum_value: float) -> dict:
    timing_start = time.perf_counter()
    selected = ((masks[:, None] >> np.arange(len(values))) & 1).astype(float)
    plan_values = selected @ values
    state = np.ones(len(masks), dtype=np.complex128) / np.sqrt(len(masks))
    state_prep_seconds = time.perf_counter() - timing_start
    # H_C=-value; phase is exp(-i gamma H_C)=exp(+i gamma value).
    cost_start = time.perf_counter()
    state *= np.exp(1j * gamma * plan_values)
    cost_phase_seconds = time.perf_counter() - cost_start
    mixer_start = time.perf_counter()
    state = apply_xy_mixer(state, maps, beta)
    mixer_seconds = time.perf_counter() - mixer_start
    measurement_start = time.perf_counter()
    probability = np.abs(state) ** 2
    return {
        "expected_value": float(probability @ plan_values),
        "optimum_probability_all_ties": float(probability[np.isclose(plan_values, optimum_value)].sum()),
        "marginals": (probability @ selected).tolist(),
        "normalization": float(probability.sum()),
        "feasibility_mass": float(probability.sum()),  # basis contains only cardinality-k feasible plans
        "state_prep_seconds": state_prep_seconds,
        "cost_phase_seconds": cost_phase_seconds,
        "mixer_seconds": mixer_seconds,
        "measurement_seconds": time.perf_counter() - measurement_start,
    }


def exact(values: np.ndarray, masks: np.ndarray) -> tuple[float, np.ndarray, int]:
    selected = ((masks[:, None] >> np.arange(len(values))) & 1).astype(float)
    plan_values = selected @ values
    optimum = float(plan_values.max())
    tied = np.flatnonzero(np.isclose(plan_values, optimum))
    return optimum, selected[tied[0]], len(tied)


def solve_year(rows: list[dict], year: int) -> dict:
    candidates = eligible_candidates(rows, year)
    items = reduce_industries(candidates)
    n, k = len(items), min(BUDGET, len(items))
    if not items:
        return {"year": year, "status": "no_eligible_candidates", "items": [], "k": 0, "basis_dimension": 0}
    values = np.array([item.value for item in items])
    construction_start = time.perf_counter()
    masks = basis_masks(n, k)
    optimum, representative, tie_count = exact(values, masks)
    maps = pair_maps(masks, n)
    construction_seconds = time.perf_counter() - construction_start
    start = time.perf_counter()
    best = None
    for gamma in ANGLE_GAMMAS:
        for beta in ANGLE_BETAS:
            result = evaluate(values, masks, maps, float(gamma), float(beta), optimum)
            if best is None or result["expected_value"] > best["expected_value"]:
                best = {**result, "gamma": float(gamma), "beta": float(beta)}
    assert best is not None
    uniform_expected = float(k / n * values.sum())
    return {
        "year": year, "status": "completed", "items": [item.__dict__ for item in items], "k": k,
        "basis_dimension": int(len(masks)), "xy_mixer_pair_gates_per_layer": len(maps),
        "qaoa_depth_note": f"p=1; {len(maps)} fixed-order number-preserving XY rotations",
        "basis_and_mixer_map_seconds": construction_seconds,
        "exact_optimum_value": optimum, "exact_representative_selection": representative.astype(int).tolist(),
        "exact_tied_industry_plans": tie_count, "uniform_feasible_expected_value": uniform_expected,
        "uniform_feasible_marginal": float(k / n), "qaoa": best, "optimizer_evaluations": len(ANGLE_GAMMAS) * len(ANGLE_BETAS),
        "optimizer_seconds": time.perf_counter() - start,
    }


def matrix(results: list[dict], industries: list[str], key: str) -> np.ndarray:
    values = np.full((len(industries), len(YEARS)), np.nan)
    index = {industry: i for i, industry in enumerate(industries)}
    for column, result in enumerate(results):
        if result["status"] != "completed":
            continue
        for position, item in enumerate(result["items"]):
            row = index[item["industry"]]
            if key == "exact":
                values[row, column] = result["exact_representative_selection"][position]
            elif key == "qaoa":
                values[row, column] = result["qaoa"]["marginals"][position]
            elif key == "uniform":
                values[row, column] = result["uniform_feasible_marginal"]
    return values


def plot_heatmap(data: np.ndarray, industries: list[str], title: str, filename: str,
                 *, difference: bool = False) -> None:
    fig, ax = plt.subplots(figsize=(12, 7), facecolor="white")
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")
    cmap = plt.get_cmap("viridis").copy() if not difference else plt.get_cmap("coolwarm").copy()
    cmap.set_bad("#e6e6e6")
    if difference:
        image = ax.imshow(data, aspect="auto", cmap=cmap, norm=TwoSlopeNorm(vcenter=0, vmin=-.5, vmax=.5))
        label = "QAOA marginal − uniform feasible marginal"
    else:
        image = ax.imshow(data, aspect="auto", cmap=cmap, vmin=0, vmax=1)
        label = "P(industry selected; bit 1)"
    ax.set(title=title, xlabel="planning year", ylabel="industry",
           xticks=range(len(YEARS)), xticklabels=YEARS, yticks=range(len(industries)), yticklabels=industries)
    ax.tick_params(axis="x", rotation=0)
    ax.tick_params(colors="black")
    ax.xaxis.label.set_color("black")
    ax.yaxis.label.set_color("black")
    ax.title.set_color("black")
    for spine in ax.spines.values():
        spine.set_color("black")
    colorbar = fig.colorbar(image, ax=ax, label=label)
    fig.text(.01, .01, "Gray = industry ineligible that year / no eligible candidates; bit 1 means TARGET SELECTED. "
             "Local ideal statevector QAOA; not hardware, shots, or forecast.", fontsize=8, color="black")
    fig.tight_layout()
    fig.savefig(OUT / filename, dpi=180, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def write_outputs(results: list[dict], industries: list[str]) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "yearly_results.json").write_text(json.dumps({
        "source": "local constrained feasible-subspace p=1 QAOA; no provider/hardware",
        "lead_time_years": LEAD_TIME_YEARS, "budget": BUDGET, "bit_convention": "bit 1 = industry selected",
        "reduction": "best value per industry; tied regional alternatives retained in items[].regions",
        "angle_grid": {"gamma": ANGLE_GAMMAS.tolist(), "beta": ANGLE_BETAS.tolist(),
                       "evaluations_per_completed_year": len(ANGLE_GAMMAS) * len(ANGLE_BETAS),
                       "seed": RANDOM_SEED, "seed_note": "deterministic grid; no stochastic optimizer"},
        "results": results,
    }, indent=2) + "\n")
    rows = []
    mappings = []
    for result in results:
        base = {"year": result["year"], "status": result["status"], "eligible_industries": len(result["items"]),
                "k": result["k"], "basis_dimension": result["basis_dimension"]}
        if result["status"] == "completed":
            q = result["qaoa"]
            base.update(exact_optimum_value=result["exact_optimum_value"], qaoa_expected_value=q["expected_value"],
                        qaoa_gap=result["exact_optimum_value"]-q["expected_value"],
                        qaoa_ratio=q["expected_value"]/result["exact_optimum_value"] if result["exact_optimum_value"] else None,
                        qaoa_optimum_probability_all_ties=q["optimum_probability_all_ties"],
                        qaoa_feasibility_mass=q["feasibility_mass"], uniform_feasible_expected_value=result["uniform_feasible_expected_value"],
                        gamma=q["gamma"], beta=q["beta"], optimizer_evaluations=result["optimizer_evaluations"],
                        optimizer_seconds=result["optimizer_seconds"], xy_mixer_pair_gates_per_layer=result["xy_mixer_pair_gates_per_layer"],
                        basis_and_mixer_map_seconds=result["basis_and_mixer_map_seconds"],
                        best_eval_state_prep_seconds=q["state_prep_seconds"],
                        best_eval_cost_phase_seconds=q["cost_phase_seconds"],
                        best_eval_mixer_seconds=q["mixer_seconds"],
                        best_eval_measurement_seconds=q["measurement_seconds"],
                        exact_tied_industry_plans=result["exact_tied_industry_plans"])
            for index, item in enumerate(result["items"]):
                mappings.append({"year": result["year"], "industry": item["industry"], "value": item["value"],
                                 "flip_year": item["flip_year"], "tied_best_regions": "|".join(item["regions"]),
                                 "exact_representative_selected": result["exact_representative_selection"][index],
                                 "qaoa_industry_marginal": q["marginals"][index],
                                 "uniform_feasible_marginal": result["uniform_feasible_marginal"]})
        rows.append(base)
    for name, records in [("yearly_metrics.csv", rows), ("industry_region_mapping.csv", mappings)]:
        with (OUT / name).open("w", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(records[0]) if records else [])
            writer.writeheader(); writer.writerows(records)
    exact_matrix = matrix(results, industries, "exact")
    qaoa_matrix = matrix(results, industries, "qaoa")
    uniform_matrix = matrix(results, industries, "uniform")
    plot_heatmap(exact_matrix, industries, "Exact classical selection (representative among tied optima)", "exact_selection_heatmap.png")
    plot_heatmap(qaoa_matrix, industries, "Constrained p=1 QAOA industry selection marginal", "qaoa_selection_marginal_heatmap.png")
    plot_heatmap(uniform_matrix, industries, "Uniform feasible-plan baseline marginal", "uniform_feasible_marginal_heatmap.png")
    plot_heatmap(qaoa_matrix-uniform_matrix, industries, "QAOA − uniform feasible marginal", "qaoa_minus_uniform_heatmap.png", difference=True)


def tests() -> None:
    rows = [
        {"industry": "A", "region": "California", "base_resistance": .1, "flip_year": 2027},
        {"industry": "A", "region": "Texas", "base_resistance": .1, "flip_year": 2027},
        {"industry": "B", "region": "California", "base_resistance": .2, "flip_year": 2027},
    ]
    items = reduce_industries(eligible_candidates(rows, 2026))
    assert len(items) == 2 and items[0].regions == ("California", "Texas")
    values = np.array([item.value for item in items]); masks = basis_masks(2, 1); optimum, _, ties = exact(values, masks)
    assert ties == 1
    value = evaluate(values, masks, pair_maps(masks, 2), 0., 0., optimum)
    assert np.isclose(value["normalization"], 1) and np.allclose(value["marginals"], [.5, .5])
    assert np.isclose(value["feasibility_mass"], 1)
    # Independent exhaustive reference: fixed-cardinality plans and uniform expectation.
    reference_values = np.array([4.0, 2.0, 1.0])
    reference_masks = basis_masks(3, 2)
    reference_optimum, _, reference_ties = exact(reference_values, reference_masks)
    assert np.isclose(reference_optimum, 6.0) and reference_ties == 1
    expected_uniform = 2 / 3 * reference_values.sum()
    zero_angle = evaluate(reference_values, reference_masks, pair_maps(reference_masks, 3), 0., 0., reference_optimum)
    assert np.isclose(zero_angle["expected_value"], expected_uniform)
    # The pair-rotation mixer must remain normalized and cannot leave the feasible basis.
    rotated = evaluate(reference_values, reference_masks, pair_maps(reference_masks, 3), .21, .17, reference_optimum)
    assert np.isclose(rotated["normalization"], 1) and np.isclose(rotated["feasibility_mass"], 1)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--test", action="store_true", help="run bounded mathematical checks without writing results")
    args = parser.parse_args(argv)
    tests()
    if args.test:
        print("Constrained target-selection QAOA checks passed")
        return
    rows = load_rows(INPUT / "quantum_flip_years.csv")
    industries = sorted({row["industry"] for row in rows})
    results = [solve_year(rows, year) for year in YEARS]
    write_outputs(results, industries)
    print(f"Wrote {OUT}; completed years={sum(result['status']=='completed' for result in results)}")


if __name__ == "__main__":
    main()
