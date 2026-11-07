"""Classical scale-out and counterfactual diagnostics (illustrative model scenarios)."""
from __future__ import annotations
import numpy as np
from .model import IsingModel
from .exact import mincut, flip_intervals

REGIONS = ("Pacific NW", "California", "Mountain West", "Southwest", "Texas", "Great Plains",
           "Midwest", "Great Lakes", "Southeast", "Florida", "Mid-Atlantic", "Northeast")


def twelve_region(base: IsingModel) -> IsingModel:
    """Illustrative chain geography: same industry adjacent regions share weak ties."""
    n, r = base.n, len(REGIONS)
    names = tuple(f"{name} / {region}" for region in REGIONS for name in base.names)
    shifts = np.rint(np.linspace(-0.15, 0.15, r) * base.unit).astype(np.int64)
    resistance = np.concatenate([base.resistance + shift for shift in shifts])
    ties = np.zeros((n * r, n * r), dtype=np.int64)
    for k in range(r):
        sl = slice(k * n, (k + 1) * n)
        ties[sl, sl] = base.ties
    cross = round(0.05 * base.unit)
    for k in range(r - 1):
        for i in range(n):
            a, b = k * n + i, (k + 1) * n + i
            ties[a, b] = ties[b, a] = cross
    return IsingModel(names, resistance, ties, base.pressure_step, base.unit)


def no_ties(base: IsingModel) -> IsingModel:
    return IsingModel(base.names, base.resistance, np.zeros_like(base.ties), base.pressure_step, base.unit)


def resistance_influence(base: IsingModel, years: range, delta: int) -> np.ndarray:
    """Change in canonical exact flip year under r_k -= delta; -1 means censored."""
    original = flip_intervals({y: mincut(base, y) for y in years})["late"]
    matrix = np.full((base.n, base.n), np.nan)
    for k in range(base.n):
        r = base.resistance.copy()
        r[k] -= delta
        altered = IsingModel(base.names, r, base.ties, base.pressure_step, base.unit)
        outcome = flip_intervals({y: mincut(altered, y) for y in years})["late"]
        mask = (original >= 0) & (outcome >= 0)
        matrix[k, mask] = outcome[mask] - original[mask]
    return matrix
