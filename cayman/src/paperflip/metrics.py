"""Energy and business-output metrics. Degeneracy is handled as an interval, not erased."""
from __future__ import annotations
import numpy as np


def observed_flip_years(states: dict[int, np.ndarray]) -> tuple[np.ndarray, np.ndarray]:
    years = sorted(states)
    n = len(states[years[0]])
    first = np.full(n, -1, dtype=int)
    flipback = np.zeros(n, dtype=bool)
    for i in range(n):
        seen_digital = False
        for y in years:
            if states[y][i] == 1 and first[i] < 0:
                first[i] = y
                seen_digital = True
            elif seen_digital and states[y][i] == -1:
                flipback[i] = True
    return first, flipback


def flip_comparison(observed: np.ndarray, early: np.ndarray, late: np.ndarray) -> list[dict]:
    records = []
    for i, (actual, lo, hi) in enumerate(zip(observed, early, late)):
        if actual < 0 and hi < 0:
            kind, error = "MATCH_CENSORED", None
        elif actual < 0 or hi < 0:
            kind, error = "CENSOR_MISMATCH", None
        elif lo <= actual <= hi:
            kind, error = "MATCH", 0
        elif actual < lo:
            kind, error = "EARLY", int(actual - lo)
        else:
            kind, error = "LATE", int(actual - hi)
        records.append({"node": i, "observed_flip": int(actual), "exact_early": int(lo),
                        "exact_late": int(hi), "category": kind, "year_error": error})
    return records
