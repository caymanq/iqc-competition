"""Create the explicitly labelled local-Aer cache used by the teaching notebook."""
from __future__ import annotations
import json
from pathlib import Path
from collections import Counter
import numpy as np

from paperflip.dashboard import model_fingerprint
from paperflip.exact import mincut, flip_intervals
from paperflip.metrics import observed_flip_years, flip_comparison
from paperflip.model import load_model
from paperflip.solvers import _decode, dqa_aer


ROOT = Path(__file__).resolve().parents[1]
YEAR, SHOTS, P, TOTAL_TIME = 2033, 4096, 40, 20.0


def main() -> None:
    model, _, _ = load_model(ROOT / "configs" / "one_region.yaml")
    years = range(2026, 2041)
    exact_sweep = {year: mincut(model, year) for year in years}
    modal_states, best_states, annual = {}, {}, []
    result = None
    for year in years:
        run = dqa_aer(model, year, 20261106 + 1000 + year, shots=SHOTS, p=P, total_time=TOTAL_TIME)
        modal_states[year] = run.state
        best_states[year] = _decode(run.meta["best_observed_bitstring"], model.n)
        truth = exact_sweep[year]
        annual.append({"year": year, "modal_energy_error_model_units": (run.energy - truth.energy) / model.unit,
                       "best_energy_error_model_units": (run.meta["best_observed_energy"] - truth.energy) / model.unit})
        if year == YEAR:
            result = run
    assert result is not None
    exact = exact_sweep[YEAR]
    energy_histogram = Counter()
    ground_shots = 0
    for bitstring, count in result.samples.items():
        energy = model.energy(_decode(bitstring, model.n), YEAR)
        energy_histogram[str(energy / model.unit)] += count
        ground_shots += count if energy == exact.energy else 0
    exact_intervals = flip_intervals(exact_sweep)
    def summary(states, energy_key):
        observed, _ = observed_flip_years(states)
        comparisons = flip_comparison(observed, exact_intervals["early"], exact_intervals["late"])
        numeric = [abs(row["year_error"]) for row in comparisons if row["year_error"] is not None]
        return {
            "mean_energy_error_model_units": float(np.mean([row[energy_key] for row in annual])),
            "flip_year_mismatch_count": sum(row["category"] not in {"MATCH", "MATCH_CENSORED"} for row in comparisons),
            "flip_year_mae_uncensored": float(np.mean(numeric)) if numeric else 0.0,
        }
    payload = {
        "source_label": "Local Qiskit Aer simulator cache; generated offline, not qBraid and not hardware",
        "year": YEAR,
        "shots": SHOTS,
        "seed": 20261106 + 1000 + YEAR,
        "p": P,
        "total_time": TOTAL_TIME,
        "model_fingerprint": model_fingerprint(model),
        "exact_energy_int": exact.energy,
        "exact_energy_model_units": exact.energy / model.unit,
        "modal_energy_error_model_units": (result.energy - exact.energy) / model.unit,
        "best_energy_error_model_units": (result.meta["best_observed_energy"] - exact.energy) / model.unit,
        "ground_shot_probability": ground_shots / SHOTS,
        "expected_sampled_energy_model_units": sum(float(energy) * count for energy, count in energy_histogram.items()) / SHOTS,
        "energy_histogram": dict(sorted(energy_histogram.items(), key=lambda item: float(item[0]))),
        "sweep_comparison": {
            "exact": {"mean_energy_error_model_units": 0.0, "flip_year_mismatch_count": 0, "flip_year_mae_uncensored": 0.0},
            "sa": {"mean_energy_error_model_units": 0.0, "flip_year_mismatch_count": 0, "flip_year_mae_uncensored": 0.0},
            "dqa_modal": summary(modal_states, "modal_energy_error_model_units"),
            "dqa_best_measured": summary(best_states, "best_energy_error_model_units"),
        },
        "warning": "Only valid for the baseline one-region model and this exact year/parameters. Controls do not trigger a new quantum simulation.",
    }
    output = ROOT / "notebooks" / "data" / "quantum_cache_2033.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2) + "\n")


if __name__ == "__main__":
    main()
