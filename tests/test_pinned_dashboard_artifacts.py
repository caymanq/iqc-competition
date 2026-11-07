"""Committed static evidence must stay internally consistent and read-only."""
from pathlib import Path
import json
from zipfile import ZipFile


ROOT = Path(__file__).resolve().parents[1]


def test_pinned_dqa_baseline_has_requested_configuration_and_raw_counts():
    record = json.loads(
        (ROOT / "artifacts" / "dashboard_pins" / "dqa_2033_aer_8000_seed20264139.json").read_text()
    )
    assert record["status"] == "COMPLETED_LOCAL_CPU_AER_DQA"
    assert record["model"]["year"] == 2033
    assert record["algorithm"] == {
        "name": "digitized_quantum_annealing",
        "p": 40,
        "normalized_total_time": 20.0,
        "shots": 8000,
        "seed": 20264139,
        "mixer": "DQA driver -sum X (not QAOA beta)",
    }
    assert sum(record["raw_result"]["counts"].values()) == 8000
    assert record["raw_result"]["best_measured_energy_error_int"] == 0


def test_pinned_qaoa_heatmap_is_full_baseline_sweep_with_digital_bit_zero():
    result = json.loads(
        (ROOT / "artifacts" / "qaoa_yearly_probability_pacific_nw.json").read_text()
    )
    assert result["years"] == list(range(2026, 2041))
    assert result["bit_convention"] == "digital=x_i=0=s_i=+1; each heatmap cell is P(bit_i=0)"
    assert len(result["rows"]) == 15
    assert all(abs(row["statevector_probability_sum"] - 1) < 1e-10 for row in result["rows"])


def test_bundle_contains_the_current_generated_notebook_and_pinned_evidence():
    bundle = ROOT / "artifacts" / "paperflip_qbraid_lab_dashboard_bundle.zip"
    with ZipFile(bundle) as archive:
        assert archive.read("notebooks/paperflip_dashboard.ipynb") == (
            ROOT / "notebooks" / "paperflip_dashboard.ipynb"
        ).read_bytes()
        assert "artifacts/dashboard_pins/dqa_2033_aer_8000_seed20264139.json" in archive.namelist()
        assert "artifacts/qaoa_yearly_probability_pacific_nw.json" in archive.namelist()
