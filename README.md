# Paper Phase Transition — IQC 2026 MVP

This is a reproducible implementation of the Vasion/IQC Paper Phase Transition
challenge. It treats the provided coefficients as **illustrative model inputs,
not empirical forecasts**.

> **Using qBraid Lab? Read [QBRAID_START_HERE.md](QBRAID_START_HERE.md).**
> The Git branch is authoritative; `artifacts/paperflip_qbraid_lab_dashboard_bundle.zip`
> is a convenience preview/handoff and is not a standalone source checkout.

## One-command reproduction

```bash
python3 -m venv .venv
.venv/bin/pip install -e '.[dev,quantum]'
.venv/bin/pytest -q
.venv/bin/python -m paperflip.cli all --config configs/one_region.yaml --out results/mvp
```

The command saves figures, raw annual solver metrics, per-node flip-year
metrics, a bounded DQA schedule benchmark, seeded config/run metadata, and a concise results report in
`results/mvp/`.

The default DQA run is 40 Trotter steps over normalized anneal time 20 with
4,096 shots. The generated schedule study retains the lower-cost 3-step and
20-step results so the quality/runtime choice is reproducible rather than
assumed.

## Scope and method

- `exact`: an integer-capacity s-t min-cut baseline. It exposes the
  most-paper and most-digital ground states, so exact ties become flip-year
  intervals rather than accidental floating-point choices.
- `sa`: seeded classical simulated annealing, separately labelled.
- `dqa_aer`: a genuine, measured Qiskit/Aer digitized quantum-annealing
  circuit. It reports both its raw modal result and its best *measured*
  bitstring, the standard sampling-solver selection rule. It does not apply
  local search or classical state polishing.
- `qaoa_aer`: a p=1 circuit comparison at three representative years. It is
  deliberately kept separate from full sweep flip metrics because it does not
  run all years.
- The quantum result is a **20-qubit full one-region** circuit simulation,
  not a 12-region quantum result and not a hardware result. Classical min-cut
  is used for the 240-node 12-region scenario.

`per_year_metrics.csv` contains modal and best-observed energy errors,
exact-ground failure rates, ground-state shot probabilities, circuit depth and
the 4,096-shot budget. `per_node_flip_metrics.csv` contains
match/early/late/censored and flip-back status against exact flip intervals.
A near-optimal nonzero energy or an incorrect flip year remains an error;
fragility does not erase it.

Ties represent mutual dependence, not causal evidence. The yearly equilibria
are not a model of adoption delay or switching costs.

## Offline qBraid export and count scoring

No qBraid credentials or API calls are in this repository. The command below
only emits plain-text OpenQASM 3 and JSON manifests; it does **not** submit a
job:

```bash
.venv/bin/python -m paperflip.cli export-qbraid \
  --config configs/one_region.yaml --year 2033 --artifacts-dir artifacts
```

It creates:
- `artifacts/qbraid_dqa_2033_20q.qasm` and matching manifest: the full
  20-industry DQA at a representative near-transition year, configured for
  qBraid's QIR state-vector simulator with a 2,000-shot request.
- `artifacts/qbraid_dqa_2033_3q_smoke.qasm` and matching manifest: a connected
  Healthcare–Insurance–Pharma smoke test with 256 requested shots.

The manifest gives QASM bit ordering, industry/qubit mapping, Ising decoding,
exact integer energy, ground states, source gate counts, and scoring rules.
After a parent/controller receives provider counts as a JSON map (or
`{"counts": {...}}`), score them locally:

```bash
.venv/bin/python -m paperflip.cli score-qbraid \
  --manifest artifacts/qbraid_dqa_2033_20q.manifest.json \
  --counts provider_counts.json
```

The resulting JSON reports modal and best-observed raw sample energy errors
and ground-shot probability. It does not resubmit or alter provider results.
The export already decomposes each ZZ term to portable `cx; rz; cx`; provider
compilation can still change depth/counts. Hardware
follow-on should use shallow small-QAOA circuits; confirm backend entitlement,
transpilation, shot limits, and linked-account billing at submission time—
zero catalog pricing is not a billing guarantee.

## qBraid Lab teaching dashboard

`notebooks/paperflip_dashboard.ipynb` is a self-contained, interactive
ipywidgets dashboard designed for qBraid Lab. **It is not deployed to qBraid
Lab yet.** It never submits a task, starts a server, or needs a secret.

```bash
.venv/bin/pip install -e '.[dashboard,quantum]'
.venv/bin/python scripts/build_dashboard_notebook.py
.venv/bin/jupyter lab notebooks/paperflip_dashboard.ipynb
```

The notebook teaches the business → energy → bits → circuit → sampled-versus-
exact flow with a tangible three-industry lab, a 20-industry exact network
heatmap, ties/no-ties and resistance-intervention controls, and cached Aer
evidence. Quantum controls use only the committed
`notebooks/data/quantum_cache_2033.json`; parameter changes visibly mark the
cache stale rather than silently resimulating. qBraid-imported results remain
a separate, manually scored workflow described in `artifacts/README.md`.

The dashboard’s **Run selected year (local CPU)** button makes an explicit new
Aer DQA run for the selected 2026–2040 year, current ties/resistance model,
actual shot budget, and seed. It saves raw counts and same-graph exact metrics
under `results/dashboard_runs/` without overwriting older runs. One-year runs
do not claim a flip-year error.

The independent-regions tab uses
`notebooks/data/independent_region_views_2033.json`: five nested, stable-seed
synthetic regional models, each run as a separate 20-node local CPU circuit.
The 1/2/5-region controls compare prefixes of that set. They do not construct
a 40- or 100-node quantum circuit and include no cross-region ties.

For a downloadable convenience handoff, run `python scripts/build_dashboard_bundle.py`;
the ZIP contains the notebook, cache, offline QASM artifacts, and handoff
instructions, but **not** the full source/config tree. Use the Git checkout
above for a runnable environment. The source notebook centralizes notation in one
`NOTATION` dictionary for theory updates.
