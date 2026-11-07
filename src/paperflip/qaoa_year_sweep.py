"""Explicit, bounded yearly standard-p1-QAOA probability sweeps."""
from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import time
import uuid
from typing import Any, Iterable

import numpy as np
from qiskit.quantum_info import Statevector

from .dashboard import model_fingerprint
from .exact import ExactResult, flip_intervals, mincut
from .model import IsingModel
from .region_views import _energy_vector, _sector_marginals, standard_qaoa_circuit


DEFAULT_GAMMA_GRID = (0.2, 0.6, 1.0)
DEFAULT_BETA_GRID = (0.2, 0.5, 0.8)


def compute_qaoa_year_sweep(
    model: IsingModel,
    years: Iterable[int],
    *,
    region: str,
    region_seed: int,
    gamma_grid: tuple[float, ...] = DEFAULT_GAMMA_GRID,
    beta_grid: tuple[float, ...] = DEFAULT_BETA_GRID,
) -> dict[str, Any]:
    """Optimize each year's actual p=1 statevector then retain P(bit_i=0).

    Qiskit's integer basis index stores qubit ``i`` in bit ``i``.  Our
    convention is x_i=0 / s_i=+1 = digital, so the reported marginal is the
    probability of that bit being zero.  No samples, classical polishing, or
    optimum-state injection are used.
    """
    years = tuple(int(year) for year in years)
    if not years:
        raise ValueError("year sweep needs at least one year")
    if not gamma_grid or not beta_grid:
        raise ValueError("year sweep needs nonempty angle grids")
    started = time.perf_counter()
    rows: list[dict[str, Any]] = []
    exact_by_year: dict[int, ExactResult] = {}

    for year in years:
        year_started = time.perf_counter()
        energies = _energy_vector(model, year)
        exact = mincut(model, year)
        exact_by_year[year] = exact
        best: tuple[float, float, float, np.ndarray] | None = None
        for gamma in gamma_grid:
            for beta in beta_grid:
                vector = Statevector.from_instruction(
                    standard_qaoa_circuit(model, year, float(gamma), float(beta))
                ).data
                probabilities = np.abs(vector) ** 2
                expected = float(np.dot(probabilities, energies))
                candidate = (expected, float(gamma), float(beta), probabilities)
                if best is None or candidate[:3] < best[:3]:
                    best = candidate
        assert best is not None
        expected, gamma, beta, probabilities = best
        rows.append({
            "year": year,
            "selected_gamma": gamma,
            "selected_beta": beta,
            "expected_energy_model_units": expected / model.unit,
            "exact_energy_model_units": exact.energy / model.unit,
            "exact_optimum_probability": float(
                probabilities[energies == exact.energy].sum()
            ),
            "digital_probability_by_industry": _sector_marginals(probabilities, model.n),
            "statevector_probability_sum": float(probabilities.sum()),
            "cpu_seconds": time.perf_counter() - year_started,
        })

    intervals = flip_intervals(exact_by_year)
    markers = []
    for index, name in enumerate(model.names):
        early, late = int(intervals["early"][index]), int(intervals["late"][index])
        degenerate_years = [
            year for year in years if bool(exact_by_year[year].degenerate[index])
        ]
        markers.append({
            "industry": name,
            "earliest_digital_year": None if early < 0 else early,
            "latest_digital_year": None if late < 0 else late,
            "already_digital_at_window_start": early == years[0],
            "never_digital_through_window": early < 0,
            "has_exact_degeneracy": bool(degenerate_years),
            "degenerate_years": degenerate_years,
            "degenerate_tipping_interval": bool(early >= 0 and late >= 0 and early != late),
        })
    return {
        "schema_version": 1,
        "status": "LOCAL_CPU_STATEVECTOR_STANDARD_P1_QAOA_NOT_DQA_NOT_QBRAID_NOT_HARDWARE",
        "source": "exact statevector marginals; not finite-shot measured samples",
        "region": region,
        "region_seed": int(region_seed),
        "assumption": "Independent same-20-node region; no cross-region ties or linked multi-region circuit.",
        "model_fingerprint": model_fingerprint(model),
        "bit_convention": "digital=x_i=0=s_i=+1; each heatmap cell is P(bit_i=0)",
        "years": list(years),
        "algorithm": {
            "name": "standard_p1_qaoa_bounded_expected_energy_grid",
            "gamma_grid": list(gamma_grid),
            "beta_grid": list(beta_grid),
            "objective": "minimize expected Ising energy independently for each year",
            "random_seed": None,
        },
        "rows": rows,
        "exact_flip_markers": markers,
        "cpu_seconds": time.perf_counter() - started,
    }


def persist_qaoa_year_sweep(result: dict[str, Any], output_dir: str | Path) -> Path:
    """Write a new local result without overwriting old runs."""
    directory = Path(output_dir)
    directory.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    payload = {
        "run_id": f"{timestamp}_{uuid.uuid4().hex[:10]}",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        **result,
    }
    path = directory / f"{payload['run_id']}.json"
    path.write_text(json.dumps(payload, indent=2) + "\n")
    return path


def year_sweep_matches(
    result: dict[str, Any], model: IsingModel, years: Iterable[int], *, region: str,
    region_seed: int, gamma_grid: tuple[float, ...], beta_grid: tuple[float, ...],
) -> bool:
    algorithm = result.get("algorithm", {})
    return (
        result.get("model_fingerprint") == model_fingerprint(model)
        and result.get("region") == region
        and result.get("region_seed") == region_seed
        and result.get("years") == list(years)
        and algorithm.get("gamma_grid") == list(gamma_grid)
        and algorithm.get("beta_grid") == list(beta_grid)
    )


def latest_matching_qaoa_year_sweep(
    output_dir: str | Path, model: IsingModel, years: Iterable[int], *, region: str,
    region_seed: int, gamma_grid: tuple[float, ...], beta_grid: tuple[float, ...],
) -> tuple[dict[str, Any], Path] | None:
    """Return only a provenance record with an exact cache-key match."""
    directory = Path(output_dir)
    if not directory.exists():
        return None
    for path in sorted(directory.glob("*.json"), reverse=True):
        try:
            result = json.loads(path.read_text())
        except (OSError, json.JSONDecodeError):
            continue
        if year_sweep_matches(
            result, model, years, region=region, region_seed=region_seed,
            gamma_grid=gamma_grid, beta_grid=beta_grid,
        ):
            return result, path
    return None
