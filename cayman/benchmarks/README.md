# Empirical C++ min-cut vs ideal QAOA-statevector benchmark

This is a local-CPU benchmark, not a qBraid, hardware, or quantum-advantage
claim. It measures the same seeded dense ferromagnetic Ising instances:

\[
E(s)=-\sum_{i<j}J_{ij}s_is_j-\sum_i h_i s_i,\quad J_{ij}\ge0,
\quad x_i=0\Leftrightarrow s_i=+1\text{ (digital)}.
\]

`h` has deliberately mixed signs and positive dense ties are seeded/scaled as
`(0.25 + 0.75 U[0,1))/n`, so this is neither a uniform-field nor trivial
always-uniform instance family.

## Algorithms actually timed

- **Exact:** source/sink min-cut reduction with double capacities and Dinic
  max-flow. Source-side nodes are digital. Pair capacities are `2J`; terminal
  capacities are `2 max(h,0)` source-to-node and `2 max(-h,0)` node-to-sink.
  The reported energy is `cut - sum(J) - sum(abs(h))`. Dinic’s actual
  practical performance is measured; no generic `O(VE)` claim is made.
- **QAOA:** ideal local CPU **p=1** statevector only. It applies
  `exp(-i gamma E(z))` directly to amplitudes, then in-place
  `Rx(2 beta)` pair updates. It never builds a dense unitary. A fixed 3×3
  `(gamma,beta)` grid performs exactly 9 objective evaluations at every common
  measured size. The CSV separates energy precomputation, one circuit
  evaluation, and optimizer-inclusive time.

Expectation values are exact statevector expectations, not shots. Quality
columns report expected energy and probability of any exact min-cut ground
state; equal solution quality is not assumed.

## Reproduce

```bash
cd cayman/benchmarks
chmod +x run_benchmark.sh
PYTHON_BIN="$(command -v python)" ./run_benchmark.sh
```

The program first runs an untimed warmup, then tiny tests: brute-force/min-cut agreement,
statevector normalization, cost-only probability invariance (`beta=0`), and
uniform-probability behavior for `gamma=0`. It then measures three repeats
at common statevector sizes `4,6,...,20`, and exact min-cut alone at
`20,40,80,120,160,200,240,500,1000,2000`.

The plot uses only measured QAOA sizes. It deliberately does **not**
extrapolate CPU statevector timings to 40–2000 qubits. Memory grows
exponentially for this simulator; max-flow has a different scaling regime.
All completed rows are marked `completed`; no timeout/censored row was needed
on the recorded VM run.
