"""Pure helpers for the qBraid Lab teaching dashboard.

Widget code lives in the notebook; these deterministic functions make its
model calculations testable and keep notation/control behavior consistent.
"""
from __future__ import annotations

import hashlib
import json
import numpy as np

from .exact import mincut
from .model import IsingModel


def model_with_pressure(model: IsingModel, pressure_int: int) -> IsingModel:
    """Represent a custom A value at synthetic year 2026 without float math."""
    return IsingModel(model.names, model.resistance - pressure_int, model.ties,
                      model.pressure_step, model.unit)


def tiny_business_model(resistance_int: tuple[int, int, int], healthcare_insurance: int,
                        healthcare_pharma: int) -> IsingModel:
    """Connected tangible Healthcare–Insurance–Pharma teaching example."""
    ties = np.array(
        [[0, healthcare_insurance, healthcare_pharma],
         [healthcare_insurance, 0, 0],
         [healthcare_pharma, 0, 0]],
        dtype=np.int64,
    )
    return IsingModel(("Healthcare", "Insurance", "Pharma"),
                      np.array(resistance_int, dtype=np.int64), ties, 700, 10_000)


def energy_breakdown(model: IsingModel, pressure_int: int, state: np.ndarray) -> dict:
    """Terms in E=-sum J ss -sum(A-r)s for a selected state."""
    synthetic = model_with_pressure(model, pressure_int)
    s = np.asarray(state, dtype=np.int8)
    ties = -int(np.sum(np.triu(synthetic.ties, 1) * np.outer(s, s)))
    local = -int(np.dot(synthetic.fields(2026), s))
    return {"tie_term_int": ties, "local_preference_term_int": local,
            "total_energy_int": ties + local,
            "tie_term": ties / model.unit, "local_preference_term": local / model.unit,
            "total_energy": (ties + local) / model.unit}


def exact_at_pressure(model: IsingModel, pressure_int: int):
    return mincut(model_with_pressure(model, pressure_int), 2026)


def model_fingerprint(model: IsingModel) -> str:
    payload = {
        "names": model.names,
        "resistance": model.resistance.tolist(),
        "ties": model.ties.tolist(),
        "pressure_step": int(model.pressure_step),
        "unit": int(model.unit),
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()[:16]
