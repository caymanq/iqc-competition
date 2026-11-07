import json
import numpy as np

from paperflip.model import IsingModel
from paperflip.qbraid import dqa_qasm3, export_artifact, score_counts


def small_model() -> IsingModel:
    return IsingModel(
        ("healthcare", "insurance", "pharma"),
        np.array([7500, 5500, 6000]),
        np.array([[0, 1500, 1050], [1500, 0, 0], [1050, 0, 0]]),
        700,
        10000,
    )


def test_qasm3_export_is_standard_and_has_expected_counts():
    qasm, counts = dqa_qasm3(small_model(), 2033, p=2, total_time=1.0)
    assert qasm.startswith('OPENQASM 3.0;\ninclude "stdgates.inc";')
    assert "qubit[3] q;" in qasm and "bit[3] c;" in qasm
    assert "c[0] = measure q[0];" in qasm
    assert counts == {
        "h": 3, "rz": 10, "rx": 3, "cx": 8, "measure": 3,
        "total_nonmeasurement": 24, "estimated_source_depth_including_measurement": 17,
    }
    # Independent QASM3 loader validates the provider-facing syntax.
    from qiskit import qasm3
    parsed = qasm3.loads(qasm)
    assert parsed.num_qubits == 3


def test_external_counts_score_using_qasm_bit_order(tmp_path):
    model = small_model()
    qasm_path = tmp_path / "tiny.qasm"
    manifest_path = tmp_path / "tiny.json"
    manifest = export_artifact(model, 2033, 2, 1.0, 32, "offline-test", qasm_path, manifest_path)
    # q[0] is rightmost. 000 means all digital (s=+1), 111 all paper (s=-1).
    counts_path = tmp_path / "counts.json"
    counts_path.write_text(json.dumps({"counts": {"000": 3, "111": 5}}))
    scored = score_counts(manifest_path, counts_path)
    assert scored["shots_received"] == 8
    assert scored["modal_bitstring"] == "111"
    assert scored["exact_energy_int"] == manifest["classical_reference"]["exact_energy_int"]
    assert scored["ground_shots"] <= 8


def test_committed_parent_smoke_counts_match_committed_manifest():
    scored = score_counts(
        "artifacts/qbraid_dqa_2033_3q_smoke.manifest.json",
        "artifacts/qbraid_runs/smoke_3q_counts.json",
    )
    assert scored["shots_received"] == 1000
    assert scored["ground_shots"] == 805
    assert scored["ground_shot_probability"] == 0.805
    assert scored["modal_energy_error_int"] == 0
