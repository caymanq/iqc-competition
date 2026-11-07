"""Offline OpenQASM 3 export and qBraid-count scoring.

This module never authenticates, contacts qBraid, or submits jobs.  It emits
portable artifacts for a parent/controller to submit through its connector.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any
import numpy as np

from .exact import mincut
from .model import IsingModel
from .solvers import _decode


def induced_model(model: IsingModel, names: tuple[str, ...]) -> IsingModel:
    """Return an explicitly named connected-business subnetwork."""
    indices = [model.names.index(name) for name in names]
    return IsingModel(
        names,
        model.resistance[indices].copy(),
        model.ties[np.ix_(indices, indices)].copy(),
        model.pressure_step,
        model.unit,
    )


def _scale(model: IsingModel, year: int) -> int:
    b = model.fields(year)
    return int(max(1, np.max(np.abs(b)), np.max(np.sum(model.ties, axis=1))))


def dqa_qasm3(model: IsingModel, year: int, p: int, total_time: float) -> tuple[str, dict[str, int | float]]:
    """Emit normalized standard-gate OpenQASM 3 for the tested DQA schedule.

    q[i] represents Ising s_i=+1 when it is measured as |0>. The source uses
    only h, rz, rx, cx and explicit measurements, avoiding Qiskit objects.
    """
    if p < 1:
        raise ValueError("p must be positive")
    scale = _scale(model, year)
    dt = total_time / p
    lines = [
        "OPENQASM 3.0;",
        'include "stdgates.inc";',
        "",
        f"// PaperFlip DQA: year={year}, p={p}, normalized_total_time={total_time:.17g}.",
        "// q[i]: |0> => s_i=+1 (digital); |1> => s_i=-1 (paper).",
        f"qubit[{model.n}] q;",
        f"bit[{model.n}] c;",
        "",
    ]
    counts: dict[str, int | float] = {"h": model.n, "rz": 0, "rx": 0, "cx": 0, "measure": model.n}
    depth = [0] * model.n
    for i in range(model.n):
        lines.append(f"h q[{i}];")
        depth[i] += 1
    b = model.fields(year)
    for layer in range(1, p + 1):
        frac = layer / p
        for i in range(model.n):
            angle = -2 * dt * frac * int(b[i]) / scale
            lines.append(f"rz({angle:.17g}) q[{i}];")
            counts["rz"] += 1
            depth[i] += 1
        for i in range(model.n):
            for j in range(i + 1, model.n):
                if model.ties[i, j]:
                    angle = -2 * dt * frac * int(model.ties[i, j]) / scale
                    # rzz(theta) = cx(i,j); rz(theta) j; cx(i,j).
                    # This decomposition avoids nonstandard rzz declarations.
                    lines.append(f"cx q[{i}], q[{j}];")
                    lines.append(f"rz({angle:.17g}) q[{j}];")
                    lines.append(f"cx q[{i}], q[{j}];")
                    counts["cx"] += 2
                    counts["rz"] += 1
                    level = max(depth[i], depth[j]) + 1
                    depth[i] = depth[j] = level
                    depth[j] += 1
                    level = max(depth[i], depth[j]) + 1
                    depth[i] = depth[j] = level
        # The last mixer rotation is identity and is intentionally omitted.
        if layer < p:
            angle = -2 * dt * (1 - frac)
            for i in range(model.n):
                lines.append(f"rx({angle:.17g}) q[{i}];")
                counts["rx"] += 1
                depth[i] += 1
    lines.append("")
    for i in range(model.n):
        lines.append(f"c[{i}] = measure q[{i}];")
        depth[i] += 1
    counts["total_nonmeasurement"] = int(counts["h"] + counts["rz"] + counts["rx"] + counts["cx"])
    counts["estimated_source_depth_including_measurement"] = max(depth)
    return "\n".join(lines) + "\n", counts


def _model_payload(model: IsingModel) -> dict[str, Any]:
    return {
        "names": list(model.names),
        "resistance_int": [int(v) for v in model.resistance],
        "ties_int": [
            {"i": i, "j": j, "value": int(model.ties[i, j])}
            for i in range(model.n) for j in range(i + 1, model.n) if model.ties[i, j]
        ],
        "pressure_step_int": int(model.pressure_step),
        "unit": int(model.unit),
    }


def _model_from_payload(payload: dict[str, Any]) -> IsingModel:
    names = tuple(payload["names"])
    ties = np.zeros((len(names), len(names)), dtype=np.int64)
    for tie in payload["ties_int"]:
        ties[tie["i"], tie["j"]] = ties[tie["j"], tie["i"]] = tie["value"]
    return IsingModel(names, np.array(payload["resistance_int"], dtype=np.int64), ties,
                      int(payload["pressure_step_int"]), int(payload["unit"]))


def export_artifact(model: IsingModel, year: int, p: int, total_time: float, shots: int,
                    target: str, qasm_path: str | Path, manifest_path: str | Path) -> dict[str, Any]:
    """Write QASM and a self-contained manifest. This is an offline file operation."""
    qasm, gate_counts = dqa_qasm3(model, year, p, total_time)
    exact = mincut(model, year)
    qasm_path, manifest_path = Path(qasm_path), Path(manifest_path)
    qasm_path.parent.mkdir(parents=True, exist_ok=True)
    qasm_path.write_text(qasm)
    manifest = {
        "schema_version": 1,
        "status": "EXPORTED_NOT_SUBMITTED",
        "target": target,
        "format": "openqasm3",
        "qasm_file": qasm_path.name,
        "year": year,
        "dqa": {
            "p": p,
            "normalized_total_time": total_time,
            "normalization_scale_int": _scale(model, year),
            "schedule": "linear: H(t)=(1-t/T)(-sum X)+t/T*H_problem; first-order product formula",
            "sample_budget_requested": shots,
        },
        "bitstring_contract": {
            "result_key_order": f"c[{model.n - 1}]...c[0] (left-to-right), as returned by common OpenQASM result APIs",
            "qubit_to_industry": [{"qubit": i, "industry": name} for i, name in enumerate(model.names)],
            "spin_decoding": "displayed bit 0 -> s=+1 digital; displayed bit 1 -> s=-1 paper; reverse displayed key before indexing industry",
            "scoring": "Use paperflip score-qbraid --manifest MANIFEST --counts COUNTS_JSON. Counts are scored directly; no state polishing.",
        },
        "classical_reference": {
            "exact_energy_int": exact.energy,
            "exact_energy_model_units": exact.energy / model.unit,
            "most_paper_ground_state": [int(x) for x in exact.paper_state],
            "most_digital_ground_state": [int(x) for x in exact.digital_state],
            "ground_state_degenerate": bool(np.any(exact.degenerate)),
        },
        "predicted_source_gate_counts": gate_counts,
        "transpilation_note": "Counts are pre-transpilation source gates. ZZ terms are already decomposed to cx-rz-cx; qBraid/provider compilation may still alter depth and counts. Record provider-reported compilation data separately.",
        "provider_note": "This artifact is not a submission. qBraid entitlement, backend availability, limits, and linked-account billing must be checked at submission time.",
        "ising_model": _model_payload(model),
    }
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest


def normalize_counts(raw: dict[str, int]) -> dict[str, int]:
    """Accept a standard qBraid/OpenQASM count map, rejecting ambiguous keys."""
    normalized: dict[str, int] = {}
    for raw_key, value in raw.items():
        key = "".join(ch for ch in str(raw_key) if ch in "01")
        if not key or len(key) != len(str(raw_key).replace(" ", "")):
            raise ValueError(f"unsupported count key {raw_key!r}; expected a plain 0/1 bitstring")
        if not isinstance(value, int) or value < 0:
            raise ValueError(f"count for {raw_key!r} must be a non-negative integer")
        normalized[key] = normalized.get(key, 0) + value
    return normalized


def score_counts(manifest_path: str | Path, counts_path: str | Path) -> dict[str, Any]:
    """Score externally supplied result counts without any provider interaction."""
    manifest = json.loads(Path(manifest_path).read_text())
    loaded = json.loads(Path(counts_path).read_text())
    raw_counts = loaded.get("counts", loaded)
    if not isinstance(raw_counts, dict):
        raise ValueError("counts JSON must be a mapping or {'counts': mapping}")
    model = _model_from_payload(manifest["ising_model"])
    year = int(manifest["year"])
    counts = normalize_counts(raw_counts)
    if any(len(key) != model.n for key in counts):
        raise ValueError(f"each count key must contain exactly {model.n} bits")
    total_shots = sum(counts.values())
    if not total_shots:
        raise ValueError("no shots supplied")
    exact_energy = int(manifest["classical_reference"]["exact_energy_int"])
    scored = [
        (key, count, model.energy(_decode(key, model.n), year))
        for key, count in counts.items()
    ]
    modal_key, modal_count, modal_energy = max(scored, key=lambda row: row[1])
    best_key, _, best_energy = min(scored, key=lambda row: row[2])
    ground_shots = sum(count for _, count, energy in scored if energy == exact_energy)
    return {
        "manifest": str(manifest_path),
        "status": "SCORED_EXTERNAL_COUNTS_NOT_A_QBRAID_SUBMISSION",
        "year": year,
        "shots_received": total_shots,
        "shot_budget_requested": manifest["dqa"]["sample_budget_requested"],
        "exact_energy_int": exact_energy,
        "modal_bitstring": modal_key,
        "modal_energy_int": modal_energy,
        "modal_energy_error_int": modal_energy - exact_energy,
        "best_measured_bitstring": best_key,
        "best_measured_energy_int": best_energy,
        "best_measured_energy_error_int": best_energy - exact_energy,
        "ground_shots": ground_shots,
        "ground_shot_probability": ground_shots / total_shots,
    }
