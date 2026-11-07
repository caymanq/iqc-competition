"""Integer-valued Ising model.  Integer units avoid false zero-field flips."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import yaml
import numpy as np


@dataclass(frozen=True)
class IsingModel:
    names: tuple[str, ...]
    resistance: np.ndarray  # integer units
    ties: np.ndarray  # symmetric, non-negative integer units
    pressure_step: int
    unit: int = 10_000

    def __post_init__(self) -> None:
        """Min-cut exactness is valid only for symmetric ferromagnetic ties."""
        n = len(self.names)
        if self.resistance.shape != (n,) or self.ties.shape != (n, n):
            raise ValueError("resistance must have n entries and ties must be an n×n matrix")
        if not np.array_equal(self.ties, self.ties.T):
            raise ValueError("ties must be symmetric: J_ij represents mutual dependence")
        if np.any(np.diag(self.ties) != 0):
            raise ValueError("ties must have a zero diagonal")
        if np.any(self.ties < 0):
            raise ValueError(
                "negative/frustrated ties are unsupported: exact s-t min-cut requires J_ij >= 0"
            )

    @property
    def n(self) -> int:
        return len(self.names)

    def fields(self, year: int) -> np.ndarray:
        """b=A-r in E=-sum J ss - sum b s."""
        return np.full(self.n, (year - 2026) * self.pressure_step, dtype=np.int64) - self.resistance

    def energy(self, state: np.ndarray, year: int) -> int:
        s = np.asarray(state, dtype=np.int64)
        return int(-np.sum(np.triu(self.ties, 1) * np.outer(s, s)) - np.dot(self.fields(year), s))

    def ocean_terms(self, year: int) -> tuple[np.ndarray, np.ndarray]:
        """Ocean/dimod minimises sum h*s + sum J*s*s; signs oppose challenge energy."""
        return -self.fields(year), -self.ties

    def qubo(self, year: int) -> tuple[np.ndarray, int]:
        """x=(1-s)/2 (paper=1); returns x'Qx plus the absolute-energy constant."""
        b = self.fields(year)
        q = np.zeros((self.n, self.n), dtype=np.int64)
        for i in range(self.n):
            q[i, i] = 2 * b[i] + 2 * int(np.sum(self.ties[i]))
            for j in range(i + 1, self.n):
                q[i, j] = -4 * self.ties[i, j]
        return q, int(-np.sum(np.triu(self.ties, 1)) - np.sum(b))


def load_model(path: str | Path) -> tuple[IsingModel, range, dict]:
    data = yaml.safe_load(Path(path).read_text())
    unit = int(data["unit"])
    names = tuple(data["industries"])
    resist = np.array([round(float(data["industries"][x]) * unit) for x in names], dtype=np.int64)
    ties = np.zeros((len(names), len(names)), dtype=np.int64)
    for left, right, strength in data["ties"]:
        i, j = names.index(left), names.index(right)
        value = round(float(data["tie_scale"]) * float(strength) * unit)
        ties[i, j] = ties[j, i] = value
    years = range(int(data["years"][0]), int(data["years"][1]) + 1)
    return IsingModel(names, resist, ties, round(float(data["pressure_step"]) * unit), unit), years, data
