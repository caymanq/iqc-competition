# qBraid handoff artifacts (offline only)

Status: **exported, not submitted**. These files do not contain credentials and
this repository does not contact qBraid.

## Primary QIR-state-vector target

- `qbraid_dqa_2033_20q.qasm`
- `qbraid_dqa_2033_20q.manifest.json`

This is the full 20-industry, one-region DQA instance in 2033, a
near-transition year (five industries are digital in the exact baseline). It
uses 40 first-order Trotter steps, normalized total time 20, and requests
2,000 shots, matching the supplied QIR simulator maximum. The source has
20 H, 1,760 RZ, 1,920 CX, and 780 RX gates (4,480 non-measurement gates),
plus 20 measurements; estimated source depth is 576. The manifest is
authoritative for angles, fields, industry mapping, spin decoding, exact
minimum energy and ground state.

The QASM uses only OpenQASM 3 standard gates (`h`, `rz`, `rx`, `cx`) and
measurements. Each Ising ZZ phase is already written as `cx; rz; cx`. An
independent OpenQASM 3 parser accepted the emitted files. These are source
counts, not qBraid-transpiled counts/depth.

## Smoke test first

- `qbraid_dqa_2033_3q_smoke.qasm`
- `qbraid_dqa_2033_3q_smoke.manifest.json`

This is the connected Healthcare–Insurance–Pharma subnetwork of the identical
model type. It requests 256 shots. Use it to confirm QASM ingestion and count
key ordering before considering the full circuit.

## Submission and scoring contract

1. Submit only through the authorized parent/controller connector. Check live
   backend state, account entitlement, shot maximum, transpiled circuit and
   linked-account billing immediately before submission. A $0 catalog listing
   does not prove a linked account cannot be billed.
2. Preserve the raw count map exactly. The expected count key is
   `c[n-1]...c[0]`, left-to-right. A displayed `0` is Ising `s=+1`
   (digital); `1` is `s=-1` (paper).
3. Save provider counts either as `{"010...": count, ...}` or as
   `{"counts": {"010...": count, ...}}`, then run:

   ```bash
   .venv/bin/python -m paperflip.cli score-qbraid \
     --manifest artifacts/qbraid_dqa_2033_20q.manifest.json \
     --counts provider_counts.json
   ```

The scorer only evaluates supplied counts. It does not alter samples, submit
jobs, authenticate, or feed the exact solution into the circuit.

For later hardware work, begin with a shallow 3–8 qubit QAOA/smoke circuit
after a provider-specific transpilation and entitlement check. Do not infer
hardware feasibility or cost from these simulator artifacts.
