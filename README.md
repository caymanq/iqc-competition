# Paper Phase Transition — IQC 2026 MVP

This is a reproducible implementation of the Vasion/IQC Paper Phase Transition
challenge. It treats the provided coefficients as **illustrative model inputs,
not empirical forecasts**.

## One-command reproduction

```bash
python3 -m venv .venv
.venv/bin/pip install -e '.[dev,quantum]'
.venv/bin/pytest -q
.venv/bin/python -m paperflip.cli all --config configs/one_region.yaml --out results/mvp
```

The command saves figures, raw annual solver metrics, per-node flip-year
metrics, seeded config/run metadata, and a concise results report in
`results/mvp/`.

## Scope and method

- `exact`: an integer-capacity s-t min-cut baseline. It exposes the
  most-paper and most-digital ground states, so exact ties become flip-year
  intervals rather than accidental floating-point choices.
- `sa`: seeded classical simulated annealing, separately labelled.
- `dqa_aer`: a genuine, measured Qiskit/Aer digitized quantum-annealing
  circuit; results are raw modal measurement outcomes. It does not apply
  local search or classical state polishing.
- `qaoa_aer`: a p=1 circuit comparison at three representative years. It is
  deliberately kept separate from full sweep flip metrics because it does not
  run all years.
- The quantum result is a **20-qubit full one-region** circuit simulation,
  not a 12-region quantum result and not a hardware result. Classical min-cut
  is used for the 240-node 12-region scenario.

`per_year_metrics.csv` contains raw energy errors and exact-ground failure
rates. `per_node_flip_metrics.csv` contains match/early/late/censored and
flip-back status against exact flip intervals. A near-optimal nonzero energy
or an incorrect flip year remains an error; fragility does not erase it.

Ties represent mutual dependence, not causal evidence. The yearly equilibria
are not a model of adoption delay or switching costs.
