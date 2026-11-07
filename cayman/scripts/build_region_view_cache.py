"""Precompute independent 20-node regional teaching views on local CPU only."""
from __future__ import annotations
import json
from pathlib import Path

from paperflip.model import load_model
from paperflip.region_views import nested_regions, compute_region_view


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    model, _, _ = load_model(ROOT / "configs" / "one_region.yaml")
    scenarios = nested_regions(model, seed=20261106, count=5)
    # Exactly five separate 20-node circuits; deliberately no 40/100-node circuit.
    views = [compute_region_view(scenario, 2033) for scenario in scenarios]
    payload = {
        "status": "PRECOMPUTED_LOCAL_CPU_SIMULATOR_NOT_QBRAID_NOT_HARDWARE",
        "scenario": "nested stable-seed synthetic independent regional models",
        "region_counts_available": [1, 2, 5],
        "no_cross_region_ties": True,
        "views": views,
    }
    output = ROOT / "notebooks" / "data" / "independent_region_views_2033.json"
    output.write_text(json.dumps(payload, indent=2) + "\n")
    print(output)


if __name__ == "__main__":
    main()
