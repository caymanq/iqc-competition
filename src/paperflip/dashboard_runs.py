"""Persisted, explicit local DQA runs for the teaching dashboard."""
from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import platform
import uuid
from typing import Any

import numpy as np

from .dashboard import model_fingerprint
from .exact import mincut
from .model import IsingModel
from .solvers import _decode, dqa_aer


def _model_provenance(model: IsingModel, year: int) -> dict[str, Any]:
    return {
        "fingerprint": model_fingerprint(model),
        "names": list(model.names),
        "resistance_int": [int(value) for value in model.resistance],
        "tie_count": int(np.count_nonzero(np.triu(model.ties, 1))),
        "tie_sum_int": int(np.sum(np.triu(model.ties, 1))),
        "pressure_int": int((year - 2026) * model.pressure_step),
        "year": year,
    }


def run_local_dqa_and_persist(model: IsingModel, year: int, shots: int, seed: int,
                              output_dir: str | Path, p: int = 40,
                              total_time: float = 20.0) -> tuple[dict[str, Any], Path]:
    """Run one requested local CPU/Aer DQA simulation and persist raw counts.

    This is deliberately invoked only from an explicit dashboard Run button;
    it has no provider SDK, credentials, or remote submission path.
    """
    if not 2026 <= year <= 2040:
        raise ValueError("dashboard runs support years 2026–2040")
    if shots < 1:
        raise ValueError("shots must be positive")
    result = dqa_aer(model, year, seed=seed, shots=shots, p=p, total_time=total_time)
    truth = mincut(model, year)
    energies = {
        bitstring: model.energy(_decode(bitstring, model.n), year)
        for bitstring in result.samples
    }
    ground_shots = sum(count for bitstring, count in result.samples.items() if energies[bitstring] == truth.energy)
    expected_energy = sum(energies[bitstring] * count for bitstring, count in result.samples.items()) / shots
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    record = {
        "schema_version": 1,
        "run_id": f"{timestamp}_{uuid.uuid4().hex[:10]}",
        "status": "COMPLETED_LOCAL_CPU_AER_DQA",
        "source": "LOCAL_AER_ON_DEMAND; not qBraid; not hardware; no remote submission",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "python_platform": platform.platform(),
        "model": _model_provenance(model, year),
        "algorithm": {
            "name": "digitized_quantum_annealing",
            "p": p,
            "normalized_total_time": total_time,
            "shots": shots,
            "seed": seed,
            "mixer": "DQA driver -sum X (not QAOA beta)",
        },
        "exact_same_graph": {
            "energy_int": truth.energy,
            "energy_model_units": truth.energy / model.unit,
            "paper_tie_state": [int(value) for value in truth.paper_state],
            "digital_extreme_state": [int(value) for value in truth.digital_state],
        },
        "raw_result": {
            "counts": result.samples,
            "modal_bitstring": max(result.samples, key=result.samples.get),
            "modal_energy_int": result.energy,
            "modal_energy_error_int": result.energy - truth.energy,
            "best_measured_bitstring": result.meta["best_observed_bitstring"],
            "best_measured_energy_int": result.meta["best_observed_energy"],
            "best_measured_energy_error_int": result.meta["best_observed_energy"] - truth.energy,
            "expected_energy_int": expected_energy,
            "expected_energy_model_units": expected_energy / model.unit,
            "ground_shots": ground_shots,
            "ground_shot_probability": ground_shots / shots,
            "distinct_states": result.meta["distinct_states"],
            "cpu_seconds": result.seconds,
            "circuit_depth": result.meta["depth"],
            "two_qubit_gates": result.meta["two_qubit_gates"],
        },
        "scope_note": "Single-year data has no flip-year metric. Compute a complete matching sweep before reporting flip-year errors.",
    }
    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    path = destination / f"{record['run_id']}.json"
    path.write_text(json.dumps(record, indent=2) + "\n")
    return record, path


def run_matches(record: dict[str, Any], model: IsingModel, year: int, shots: int, seed: int,
                p: int, total_time: float) -> bool:
    """True only for transparently identical cache/provenance settings."""
    algorithm = record.get("algorithm", {})
    return (
        record.get("model", {}).get("fingerprint") == model_fingerprint(model)
        and record.get("model", {}).get("year") == year
        and algorithm.get("shots") == shots and algorithm.get("seed") == seed
        and algorithm.get("p") == p and algorithm.get("normalized_total_time") == total_time
    )


def latest_matching_run(output_dir: str | Path, model: IsingModel, year: int, shots: int,
                        seed: int, p: int, total_time: float) -> tuple[dict[str, Any], Path] | None:
    """Load the most recent matching persisted result, never a near match."""
    directory = Path(output_dir)
    if not directory.exists():
        return None
    matches = []
    for path in directory.glob("*.json"):
        try:
            record = json.loads(path.read_text())
        except (OSError, json.JSONDecodeError):
            continue
        if run_matches(record, model, year, shots, seed, p, total_time):
            matches.append((record, path))
    return max(matches, key=lambda item: item[0].get("created_at_utc", "")) if matches else None
