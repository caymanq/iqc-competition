"""Bounded, explicit standard-p1-QAOA energy landscapes for teaching."""
from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import time
import uuid
from typing import Any

import numpy as np
from qiskit.quantum_info import Statevector

from .dashboard import model_fingerprint
from .exact import mincut
from .model import IsingModel
from .region_views import _energy_vector, standard_qaoa_circuit


def compute_qaoa_landscape(model: IsingModel, year: int, gamma_values: np.ndarray,
                           beta_values: np.ndarray) -> dict[str, Any]:
    """Evaluate actual circuit statevectors over a deliberately small grid."""
    gamma_values, beta_values = np.asarray(gamma_values, dtype=float), np.asarray(beta_values, dtype=float)
    if gamma_values.ndim != 1 or beta_values.ndim != 1 or len(gamma_values) < 2 or len(beta_values) < 2:
        raise ValueError("landscape needs at least two gamma and beta values")
    if len(gamma_values) > 9 or len(beta_values) > 9:
        raise ValueError("grid is capped at 9×9 to keep 20-node CPU work bounded")
    started = time.perf_counter()
    energies = _energy_vector(model, year)
    exact = mincut(model, year)
    surface = np.empty((len(beta_values), len(gamma_values)), dtype=float)
    for beta_index, beta in enumerate(beta_values):
        for gamma_index, gamma in enumerate(gamma_values):
            vector = Statevector.from_instruction(standard_qaoa_circuit(model, year, float(gamma), float(beta))).data
            surface[beta_index, gamma_index] = np.dot(np.abs(vector) ** 2, energies) / model.unit
    d_beta, d_gamma = np.gradient(surface, beta_values, gamma_values, edge_order=1)
    gradient_norm = np.hypot(d_gamma, d_beta)
    selected = np.unravel_index(np.argmin(surface), surface.shape)
    return {
        "status": "LOCAL_CPU_STATEVECTOR_STANDARD_P1_QAOA_NOT_DQA_NOT_QBRAID_NOT_HARDWARE",
        "model_fingerprint": model_fingerprint(model),
        "year": year,
        "exact_minimum_model_units": exact.energy / model.unit,
        "gamma_values": gamma_values.tolist(),
        "beta_values": beta_values.tolist(),
        "expected_energy_model_units": surface.tolist(),
        "gradient_norm_model_units_per_radian": gradient_norm.tolist(),
        "selected_grid_minimum": {
            "gamma": float(gamma_values[selected[1]]),
            "beta": float(beta_values[selected[0]]),
            "expected_energy_model_units": float(surface[selected]),
            "note": "lowest sampled grid value; a small gradient is not claimed to prove a minimum",
        },
        "cpu_seconds": time.perf_counter() - started,
    }


def persist_landscape(landscape: dict[str, Any], output_dir: str | Path) -> Path:
    """Append-only local provenance; no remote service or overwrite."""
    directory = Path(output_dir)
    directory.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    payload = {
        "schema_version": 1,
        "run_id": f"{timestamp}_{uuid.uuid4().hex[:10]}",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        **landscape,
    }
    path = directory / f"{payload['run_id']}.json"
    path.write_text(json.dumps(payload, indent=2) + "\n")
    return path


def landscape_matches(landscape: dict[str, Any], model: IsingModel, year: int,
                      gamma_values: np.ndarray, beta_values: np.ndarray) -> bool:
    return (
        landscape.get("model_fingerprint") == model_fingerprint(model)
        and landscape.get("year") == year
        and landscape.get("gamma_values") == np.asarray(gamma_values, dtype=float).tolist()
        and landscape.get("beta_values") == np.asarray(beta_values, dtype=float).tolist()
    )
