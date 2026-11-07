import json
import numpy as np

from paperflip.dashboard_runs import latest_matching_run, run_local_dqa_and_persist, run_matches
from paperflip.model import IsingModel, load_model


def small(tie: int = 3, resistance: tuple[int, int, int] = (6, 7, 8)) -> IsingModel:
    return IsingModel(
        ("a", "b", "c"), np.array(resistance),
        np.array([[0, tie, 0], [tie, 0, 2], [0, 2, 0]]), 4, 10,
    )


def test_explicit_runs_persist_without_overwrite_and_mark_stale(tmp_path):
    first, first_path = run_local_dqa_and_persist(small(), 2027, shots=64, seed=1, output_dir=tmp_path, p=2, total_time=1)
    second, second_path = run_local_dqa_and_persist(small(tie=4), 2030, shots=32, seed=2, output_dir=tmp_path, p=2, total_time=1)
    assert first_path != second_path and first_path.exists() and second_path.exists()
    assert first["model"]["year"] == 2027 and second["model"]["year"] == 2030
    assert first["algorithm"]["shots"] == 64 and second["algorithm"]["shots"] == 32
    assert first["raw_result"]["ground_shots"] <= 64
    assert not run_matches(first, small(tie=4), 2027, 64, 1, 2, 1)
    assert not run_matches(first, small(), 2030, 64, 1, 2, 1)
    assert not run_matches(first, small(), 2027, 32, 1, 2, 1)
    assert json.loads(first_path.read_text())["run_id"] == first["run_id"]
    restored = latest_matching_run(tmp_path, small(), 2027, 64, 1, 2, 1)
    assert restored is not None and restored[1] == first_path


def test_representative_20_node_run_is_local_and_scored_same_graph(tmp_path):
    model, _, _ = load_model("configs/one_region.yaml")
    record, path = run_local_dqa_and_persist(model, 2031, shots=64, seed=99, output_dir=tmp_path, p=1, total_time=1)
    assert path.exists()
    assert record["model"]["year"] == 2031
    assert record["raw_result"]["ground_shots"] <= 64
    assert record["raw_result"]["modal_energy_error_int"] >= 0
    assert "flip-year" in record["scope_note"]
