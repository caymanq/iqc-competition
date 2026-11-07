# Parent-supplied qBraid run provenance

These records are sanitized evidence supplied by the parent qBraid MCP
executor. They contain no credentials. The repository did not submit, poll, or
spend on either job.

| Export | Device | Job | Status | Evidence |
|---|---|---|---|---|
| 3-qubit Healthcare–Insurance–Pharma smoke | `qbraid:qbraid:sim:qir-sv` | `qbraid:qbraid:sim:qir-sv-450c-qjob-6aeeea4bd1eb272b3e1c97c9` | **COMPLETED** | 1,000 raw shots; verified locally |
| 20-qubit 2033 DQA | `qbraid:qbraid:sim:qir-sv` | `qbraid:qbraid:sim:qir-sv-450c-qjob-6aeeea5ad1eb272b3e1c97cf` | **RUNNING/PENDING** at last parent check | no counts, no result metrics |

## Verified 3-qubit smoke result

Organization: `intermountain_quantum_competition`; device:
`qbraid:qbraid:sim:qir-sv`; cost/credits reported by parent: `0`.

`smoke_3q_counts.json` has the raw result map. It is scored against the
committed three-node manifest and the repository’s 2033 pressure/config:

```bash
python -m paperflip.cli score-qbraid \
  --manifest artifacts/qbraid_dqa_2033_3q_smoke.manifest.json \
  --counts artifacts/qbraid_runs/smoke_3q_counts.json
```

The verified ground-state count is 805/1000 = **80.5%**. The result does not
infer pressure from an energy value; pressure is sourced from
`configs/one_region.yaml` and the export’s declared year.

## Pending 20-qubit export

The parent reported a 2,000-shot, zero-estimate 20-qubit 2033 DQA job as
`RUNNING` at its last check. This repository intentionally includes no
fabricated counts, energy, mode, or optimum probability for it. When raw
counts arrive, save them as `{"counts": {...}}` and use the same scorer with
`artifacts/qbraid_dqa_2033_20q.manifest.json`.
