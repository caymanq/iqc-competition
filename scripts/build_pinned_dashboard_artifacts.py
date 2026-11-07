"""One-time offline builder for the dashboard's fixed 2033 Aer evidence."""
from __future__ import annotations

import json
from pathlib import Path
import sys

import matplotlib.pyplot as plt
import numpy as np

from paperflip.dashboard_runs import run_local_dqa_and_persist
from paperflip.model import load_model
from paperflip.solvers import _decode


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "artifacts" / "dashboard_pins"
RECORD = OUTPUT / "dqa_2033_aer_8000_seed20264139.json"
IMAGE = OUTPUT / "dqa_2033_aer_8000_seed20264139.png"
YEAR, SHOTS, SEED, P, TOTAL_TIME = 2033, 8000, 20264139, 40, 20.0


def main() -> None:
    if RECORD.exists() or IMAGE.exists():
        raise SystemExit(
            "Pinned artifacts already exist; refusing to replace evidence. "
            "Remove them intentionally only when creating a separately reviewed baseline."
        )
    model, _, _ = load_model(ROOT / "configs" / "one_region.yaml")
    record, temporary_path = run_local_dqa_and_persist(
        model, YEAR, SHOTS, SEED, OUTPUT, p=P, total_time=TOTAL_TIME
    )
    temporary_path.replace(RECORD)
    raw, exact = record["raw_result"], record["exact_same_graph"]
    histogram: dict[float, int] = {}
    for bitstring, count in raw["counts"].items():
        energy = model.energy(_decode(bitstring, model.n), YEAR) / model.unit
        histogram[energy] = histogram.get(energy, 0) + count
    xs = np.array(sorted(histogram))
    ys = np.array([histogram[x] for x in xs])
    fig, ax = plt.subplots(figsize=(10, 4.5))
    ax.bar(xs, ys, width=max(.01, (xs.max() - xs.min()) / 55), color="#457b9d")
    ax.axvline(exact["energy_model_units"], color="#e63946", linestyle="--", label="exact same-graph minimum")
    ax.set(
        title="Fixed 2033 local Aer DQA raw energy histogram",
        xlabel="absolute Ising energy (model units)", ylabel="shots",
    )
    ax.legend()
    fig.text(
        .01, .01,
        "Illustrative one-region baseline; 8,000 Aer shots, seed 20264139, p=40, T=20. "
        "Local CPU simulator only—not qBraid or hardware.",
        fontsize=8,
    )
    fig.tight_layout()
    fig.savefig(IMAGE, dpi=160, bbox_inches="tight")
    plt.close(fig)
    print(json.dumps({
        "record": str(RECORD), "preview": str(IMAGE),
        "expected_energy_model_units": raw["expected_energy_model_units"],
        "modal_energy_error_model_units": raw["modal_energy_error_int"] / model.unit,
        "best_measured_energy_error_model_units": raw["best_measured_energy_error_int"] / model.unit,
        "exact_optimum_probability": raw["ground_shot_probability"],
        "cpu_seconds": raw["cpu_seconds"],
    }, indent=2))


if __name__ == "__main__":
    main()
