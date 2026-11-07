# Paper Phase Transition — Implementation Plan

Status: **planning only** (no production code yet). Authoritative spec: Vasion "The Paper Phase Transition"
challenge README (IQC 2026, BYU, Nov 6–7). Planning: Claude Opus 5.5. Build: GPT-5.6 Terra on branch
`cursor/paper-phase-transition-plan-8ab6`. Theory constraints: Aristotle. Practical lead: IQC.

## 0. Findings from repo / runtime inspection

| Item | Finding | Consequence |
|---|---|---|
| Repo | `caymanq/iqc-competition`, one commit, only `README.md` | Greenfield; no conflicts |
| Python | 3.12.3, system pip 24.0, no `uv` | Use `python3 -m venv .venv` + `pip install -e .[dev]` |
| Installed | only `numpy 1.26.4` | Everything else must be installed in M0 |
| PyPI | reachable: qiskit 2.6.2, qiskit-aer 0.18.2, networkx 3.7, scipy 1.18.1, pandas 3.1.1, matplotlib 3.11.2, pytest 9.2.0, dimod 0.12.23, dwave-samplers 1.8.0 | Free, local quantum circuit simulation is available |
| Hardware | 4 vCPU, ~15 GB RAM (≈4 GB reported free; balloon may under-report) | Statevector cap ≈ 24 qubits for sweeps, 20 for production runs |
| Credentials | none (no D-Wave/Leap, IBM, Braket, Azure env vars) | **No real QPU** without sign-in. Not a blocker: spec allows simulators |
| Float trap | `0.07*5 > 0.35` is `True` in float64 | Exact-zero fields (e.g. Hospitality 2031) mis-resolve → use integer units |

No hard blockers. The only unavailable item is real hardware, which would need a user account (D-Wave Leap trial or
IBM Quantum open plan). Hardware stays an optional, env-gated adapter that is **off by default**.

## 1. Recommended quantum path (no credentials, $0)

**Primary: digitized (Trotterized) quantum annealing circuit**, built in Qiskit, run on Qiskit Aer:
`H(t) = (1−t/T)·(−Σ X_i) + (t/T)·H_problem`, with p layers of `exp(−iγ_k H_P) · exp(−iβ_k Σ X)` on a linear schedule
(γ_k = k/p·Δt, β_k = (1−k/p)·Δt). Starting from |+…+⟩ and measuring in Z with shots, this is the gate-model analogue of
a D-Wave anneal: it matches the annealer framing in the spec, has no classical optimizer loop (deterministic and
reproducible), and degrades predictably when gaps are small. Report p and Δt.

**Secondary: variational QAOA** (p = 1–3, COBYLA, angles warm-started from the previous year). This is the spec's
"gate-based approach". It is a comparison only; low-depth QAOA on 20 qubits will often have low ground-state
probability, and that is reported honestly.

**Reference oracle:** a hand-written numpy statevector implementation of the same circuits (diagonal phase plus RX
mixer). It is used to cross-check Aer at n ≤ 10 (to 1e-8) and as a fast path for parameter scans.

**Sizes, quantum vs classical (labelled explicitly in every figure/table):**

| Label | Nodes/qubits | Method | Claim allowed |
|---|---|---|---|
| `QUANTUM-FULL-1R` | 20 (one region, entire model) | DQA / QAOA statevector + shots | "full one-region tipping map from a quantum circuit simulation" |
| `QUANTUM-SCALING` | 4–24 (sub-networks) | DQA statevector | runtime/accuracy vs n; simulation cost is exponential |
| `HYBRID-12R` (stretch in M4) | 240 via 12×20-qubit blocks | block-coordinate: each region solved by DQA with boundary fields frozen from neighbours, iterate to fixed point | "quantum-in-the-loop heuristic decomposition", **not** a full-model quantum result |
| `CLASSICAL-12R` | 240 | exact min-cut + SA | exact ground truth for the full model |

Memory: statevector is 16·2ⁿ B (20q → 16 MB, 24q → 256 MB, 26q → 1 GB, 28q → 4 GB). The time budget is roughly a few
seconds per year at 20 qubits with p ≈ 100. Simulation time is classical CPU time and is **not** a QPU runtime;
it is labelled that way, and no quantum advantage is claimed.

**Optional hardware adapter (stretch, only if Cayman supplies a token):** `DWAVE_API_TOKEN` → Ocean
`DWaveSampler`+`EmbeddingComposite` with embedding computed once and reused across years (per spec tip). Otherwise
`IBM_QUANTUM_TOKEN` → Qiskit Runtime sampler for ≤ ~10-qubit subsets. The adapter is never required, never called in
tests or CI, and spends no money. A **precision emulation** (Gaussian perturbation of h, J at ~1–3 % of range, plus
autoscale to h∈[−2,2], J∈[−1,1]) gives a "what limited-precision hardware would do" curve, labelled as emulation.

## 2. Model specification (illustrative coefficients, not forecasts)

- Node = (industry, region). State s = −1 paper, +1 digital (QUBO: x = (s+1)/2, x = 1 digital).
- Spec energy: `E(s; y) = −Σ_{i<j} J_ij s_i s_j − Σ_i b_i(y) s_i`, with `b_i(y) = A(y) − r_i`, `A(y) = 0.07·(y−2026)`,
  y ∈ {2026..2040} (15 years; A ∈ [0, 0.98]).
- Ties: `J = tie_scale · strength` (default tie_scale 0.15; 24 within-region edges from spec) plus
  `cross_region_J` (default 0.05) between the same industry in adjacent regions.
- Resistance: `r = r_industry + region_shift + noise`, where noise ~ N(0, σ=0.03) is seeded and rounded to the unit
  grid. Region shifts form a fixed illustrative table in [−0.15, +0.15].
- 12 regions (illustrative adjacency): Pacific NW, California, Mountain West, Southwest, Texas, Great Plains,
  Midwest, Great Lakes, Southeast, Florida, Mid-Atlantic, Northeast.
- Every coefficient lives in a YAML config with a `source:` note ("challenge-suggested, illustrative"). Public data
  substitutions are optional later and must be cited.

**Exact arithmetic.** All quantities are stored as integers in units of 1e-4 (`UNIT = 10_000`): A step = 700,
r = 0.35 → 3500, J = 0.15·0.6 → 900, cross = 500, noise is rounded to 1 unit. Min-cut capacities, energies, gaps and
ties are then exact integers. Floats appear only at plotting/reporting time and in quantum circuit angles, where the
integer Hamiltonian is divided by a single documented scale.

**Sign conventions (single source of truth in `convert.py`):**
- Ocean/dimod form `E = Σ h_i s_i + Σ J'_ij s_i s_j` with `h = −b`, `J' = −J` (matches the spec's warning).
- QUBO via s = 2x−1: `Q_ij = −4J_ij` (i<j), `Q_ii = 2·Σ_j J_ij − 2b_i`, `const = −Σ J_ij + Σ b_i`.
- Min-cut (s-t, source = digital): edge i–j capacity 2J_ij each direction; if b_i > 0, source→i with capacity
  2b_i; if b_i < 0, i→sink with capacity 2|b_i|. Then `E(s) = cut(s) − Σ J_ij − Σ |b_i|`.
- Sanity checks from the spec: in 2026 (A=0) every b ≤ 0, so all nodes are paper. In the one-region default, Legal
  (r = 0.90) flips alone by 2039 (A = 0.91), so the one-region map must fill in completely. With regional shifts
  (r up to 1.05) some nodes **never flip within the window**, and that case is expected.

## 3. Ground truth, degeneracy and tipping-year uncertainty

- **Exact solver:** `networkx.minimum_cut` (preflow-push) on integer capacities, ≈ms for 240 nodes.
- **Minimal and maximal ground states.** Ferromagnetic minimizers form a distributive lattice. The source side
  reachable in the residual graph gives the *most-paper* ground state `S_min`. The complement of nodes that can
  reach the sink gives the *most-digital* ground state `S_max`. Node i is **degenerate in year y** iff
  S_min ≠ S_max at i.
- **Tie-break convention:** the canonical exact answer is `S_min` (paper wins exact ties). This is consistent with
  the spec's "once pressure is *greater than* resistance". Both bounds are always reported.
- **Monotonicity:** A(y) raises every field equally, so `S_min(y)` and `S_max(y)` are monotone non-decreasing in y.
  This is asserted in tests, which makes flip years well-defined for the exact solver.
- **Exact flip-year interval** per node: `lo = first y with S_max(y)_i = +1`, `hi = first y with S_min(y)_i = +1`.
  `lo == hi` means certain. `lo < hi` means **uncertain (degenerate)**. If the node is never digital within 2040,
  the result is `CENSORED (>2040)` (and `hi` may be censored while `lo` is not).
- **Fragility margin:** in the canonical ground state, `m_i(y) = 2·|b_i + Σ_j J_ij s_j|` is the single-flip energy
  cost. A flip year is **fragile** if its margin at the flip transition is below a threshold τ (default: 2σ of
  resistance noise, plus a second threshold equal to the hardware-precision emulation level). Fragile years are
  starred on the heatmap.
- **Exhaustive enumeration** (validation only): vectorized numpy over all 2ⁿ states, n ≤ 20 (2²⁰ × 15 years is a few
  seconds). It returns the ground energy, the full ground-state set (so S_min/S_max = elementwise min/max of the set,
  validating the lattice claim), and the first excited gap.

## 4. Solvers to compare (identical integer Hamiltonian, identical year grid)

1. `exact_mincut` — ground truth (+ interval).
2. `enumerate` — validator for n ≤ 20.
3. `sa` — own numpy Metropolis simulated annealing (seeded, geometric β schedule, R restarts). Optionally
   cross-check with `dwave-samplers` `SimulatedAnnealingSampler`. **Labelled classical heuristic, not quantum.**
4. `dqa` — digitized quantum annealing circuit (Qiskit → Aer), shots = 4096, report best-sample and modal state.
5. `qaoa` — p = 1–3 variational QAOA (Aer), same reporting.
6. (stretch) `hybrid_dqa_blocks`, `dwave_qpu`, `ibm_qpu`.

Each solver returns per-year `SolveResult{state, energy_int, samples?, wall_time_s, meta}`. Quantum solvers also
return `p_ground` (probability mass on the exact ground-state set from the statevector), `approx_ratio`, and circuit
depth / 2-qubit gate count after transpiling to a generic heavy-hex-like basis. These are resource estimates only.

**Per-year independence vs sweep.** By default every solver solves each year independently (as the spec says).
Heuristic solvers can therefore produce **non-monotone** trajectories (digital in y, paper in y+1). The flip year
is defined as the first year digital (spec definition), and the number of non-monotone nodes is reported. These are
not silently repaired. An optional "monotone projection" view may be shown, labelled as post-processing.

## 5. Metrics (both energy error AND flip-year error, per Aristotle)

Per (solver, year), against exact:
- `ΔE = E_solver − E_ground` (integer units, ≥ 0; < 0 is a bug) and `ΔE_rel = ΔE / (Σ|b|+ΣJ)`.
- `is_ground` (ΔE == 0 exactly), `p_ground` (quantum), `hamming_lb` = number of nodes outside [S_min, S_max]
  (a lower bound on the distance to the ground-state set; exact when non-degenerate).
- Exact spectral gap (enumeration, n ≤ 20) and minimum fragility margin, to explain failures.

Per (solver, node), against the exact interval [lo, hi]:
- Categories: `MATCH` (solver year ∈ [lo, hi], or both censored), `EARLY k`, `LATE k`, `CENSOR_MISMATCH`
  (one side flips within the window and the other never does), and `NON_MONOTONE` (flag; can co-occur).
- Numeric error `d = distance(solver_year, [lo, hi])` is computed **only when both sides are uncensored**. Censor
  mismatches are counted separately and never get a fake number such as 2041.
- Summary: % MATCH, MAE and max |d| over uncensored pairs, censor-mismatch count, # uncertain (lo<hi) nodes, # fragile
  nodes, # non-monotone nodes. Report with and without uncertain/fragile nodes.
- Key figure: scatter of per-year ΔE_rel versus the number of flip-year mismatches. It shows that near-optimal energy
  can still mean wrong tipping years.
- Seeds: SA over ≥ 10 seeds, quantum shot sampling over ≥ 5 seeds; report mean ± spread. Timing uses
  `time.perf_counter`, split into build, solve and post-process, with the median of repeats.

## 6. Theory-constrained scenarios (Aristotle)

Language rules for all outputs: J is **mutual dependence**, not causal evidence. "Influence" means a
**model-based counterfactual scenario**. The equilibrium sequence is not adoption-delay or switching-cost dynamics.
Coefficients are illustrative, not validated forecasts.

1. **No-ties baseline** (J = 0): flip year = first y with A(y) > r_i (closed form, used as a test). The difference
   `network_flip − solo_flip` shows who is pulled earlier and who is held back.
2. **Lower-one-resistance scenarios:** for each node k, set r_k ← r_k − δ (default δ = 0.10; also r_k → 0), recompute
   exact flip years for all nodes, and record `Δflip[k→i]`. This produces an influence matrix (20×20 per region,
   aggregated by industry for 12 regions) and a "who pulls whom" ranking.
3. **Sensitivity:** tie_scale ∈ {0, 0.075, 0.15, 0.3, 0.6}, cross_region_J ∈ {0, 0.05, 0.1, 0.2}, noise seeds
   (≥ 20), region-shift magnitude ∈ {0, 0.15}. Outputs: largest single-year flip cluster ("big tipping year"),
   lockstep index across regions, and flip-year stability per node.
4. All scenarios run on the exact solver (cheap). Quantum is re-run only on the default one-region case and on one
   or two highlighted scenarios.

## 7. Repository architecture

```
pyproject.toml            # pinned deps; extras: [dev], [quantum], [dwave]
configs/
  one_region.yaml         # 20 industries, default coefficients, seeds
  twelve_regions.yaml     # adjacency, region shifts, noise σ
  sensitivity.yaml
src/paperflip/
  data.py                 # industry table, ties, regions, adjacency (+ source notes)
  model.py                # IsingNetwork (integer units), build_network(config), fields_for_year(y)
  convert.py              # spec ⇄ ocean(h,J) ⇄ QUBO ⇄ min-cut graph; energy() for each form
  exact.py                # mincut_ground_states() -> (S_min, S_max, E); enumerate_ground() for n ≤ 20
  sweep.py                # run_sweep(solver, network, years) -> SweepResult; flip years, intervals, censoring
  solvers/sa.py
  solvers/quantum_circuits.py   # Qiskit circuit builders (DQA, QAOA) from integer Hamiltonian
  solvers/quantum_run.py        # Aer execution, shots, statevector p_ground; numpy reference simulator
  solvers/hybrid_blocks.py      # stretch: region-block decomposition
  solvers/hardware.py           # stretch: env-gated D-Wave / IBM adapters (never default)
  metrics.py              # energy & flip-year metrics, categories, fragility, timing
  scenarios.py            # no-ties, lower-one, sensitivity grids
  plots.py                # heatmap, timeline, influence matrix, scaling, ΔE-vs-year-error
  sales_qubo.py           # stretch
  cli.py                  # `python -m paperflip <cmd> --config ... --out results/<run_id>`
tests/                    # see §9
results/                  # gitignored; curated figures copied to docs/figures/
docs/PLAN.md, docs/MODEL_CARD.md (assumptions + honest scope), docs/RESULTS.md (generated summary)
```

CLI commands: `validate` (enumeration vs min-cut), `sweep --solver {exact,sa,dqa,qaoa}`, `compare`,
`scaling`, `scenarios`, `figures`, `all`. Every run writes `run.json` (config hash, seeds, package versions, git SHA)
plus a CSV/Parquet of per-(solver, year, node) states so figures are regenerated from data alone.

## 8. Milestones (ordered for the fastest credible MVP)

- **M0 — Environment & skeleton.** venv, pinned `pyproject.toml`, package layout, pytest runs, `.gitignore`.
  Gate: `pip install -e .[dev,quantum]` works and imports qiskit/qiskit_aer.
- **M1 — One-region exact core.** data/config, integer model, conversions, min-cut S_min/S_max, enumeration, flip-year
  intervals, no-ties closed form. Gate: all §9 correctness tests pass. First heatmap/timeline from the exact solver.
- **M2 — Classical heuristic.** SA solver + metrics module + `compare` table (exact vs SA). Gate: SA matches exact on
  the one-region default in ≥ 95 % of (year, seed) pairs, or the shortfall is explained.
- **M3 — Quantum one-region (MVP core).** DQA and QAOA circuits, Aer runs, numpy oracle cross-check, full 20-qubit
  tipping map `QUANTUM-FULL-1R`, energy and flip-year metrics vs exact. Gate: map produced; disagreements explained via
  gap/fragility. **This is the minimum presentable deliverable (M1–M3).**
- **M4 — Scale & scaling.** 12-region classical (exact + SA), 240-node heatmap (industries × regions, colour = flip
  year, hatched = censored, star = uncertain/fragile). Scaling plot: wall time vs n for min-cut, SA and DQA statevector
  (n = 4…24) with a clearly marked exponential curve. Optional `HYBRID-12R`.
- **M5 — Aristotle scenarios.** No-ties delta, lower-one influence matrix, sensitivity grids, caveat text.
- **M6 — Presentation evidence.** `docs/figures/*.png` (heatmap, one-region timeline exact vs DQA vs SA, influence
  matrix, ΔE-vs-year-error scatter, scaling, precision-emulation curve), `docs/RESULTS.md` with numbers, a 5-minute
  slide outline mapped to the 25/25/20/30 rubric, and an "honest scope" slide.
- **S1 (stretch) — Sales QUBO**, only after M3 is green (see §10). **S2 (stretch)** — hardware adapter if a token
  appears.

## 9. Test & acceptance plan (pytest; must stay < ~60 s except `-m slow`)

Correctness:
1. **Form consistency:** spec energy == ocean(h, J) energy == QUBO energy + const for all 2ⁿ states (random n = 6
   instances) and on 10⁴ random states of the 20-node model, in exact integers.
2. **Min-cut == enumeration:** ground energy equal for every year of the one-region model (n = 20) and for 200 random
   ferromagnetic instances (n ≤ 12), including zero-field and engineered tie cases. S_min/S_max equal the elementwise
   min/max of the enumerated ground-state set.
3. **Sign sanity:** 2026 is all paper; the one-region default is all digital by 2040; neither "all flip in 2026" nor
   "never flip" occurs.
4. **No-ties closed form:** J = 0 gives flip year = first y with A > r. When A == r exactly, the result is an
   uncertain interval, not a float artifact (regression test for Hospitality r = 0.35 at 2031).
5. **Monotonicity:** exact S_min(y), S_max(y) are non-decreasing in y.
6. **Quantum oracle:** Aer statevector vs numpy reference probabilities agree to 1e-8 for n ≤ 8. DQA on a large-gap
   instance gives p_ground > 0.9.
7. **Metrics:** synthetic fixtures for MATCH within an interval, EARLY/LATE, CENSOR_MISMATCH (no numeric error),
   NON_MONOTONE, and ΔE ≥ 0.
8. **Reproducibility:** the same config and seed give byte-identical result CSVs; `run.json` captures versions.

MVP acceptance (end of M3, then M6):
- `python -m paperflip all --config configs/one_region.yaml` finishes in < 5 min on this VM and regenerates every
  one-region figure and table.
- The quantum tipping map is produced from circuit simulation of the full 20-node model, with %MATCH, MAE,
  censor-mismatch and uncertain counts reported against exact.
- Every figure and table carries its scope label (QUANTUM-FULL-1R / QUANTUM-SCALING / HYBRID / CLASSICAL) and the
  "illustrative coefficients" caveat.

## 10. Stretch: sales-budget QUBO (after M3 only)

Choose x_i ∈ {0,1} (target node i). Maximise `Σ v_i x_i + Σ w_ij x_i x_j` subject to `Σ c_i x_i ≤ B`.
- v_i = urgency (flip year within 1–3 years ahead of the "sales year") × an illustrative market weight.
- w_ij ∝ J_ij (landing tied pairs is worth more).
- The budget is enforced with binary slack bits and a penalty λ (λ chosen above the max marginal gain, validated by
  enumeration for n ≤ 20).
- Solve on a ≤ 20-variable instance with exact enumeration, SA and QAOA/DQA. The full-scale version is classical only.

## 11. Risks & mitigations

- **Low-depth QAOA quality** → DQA is primary; report p_ground honestly; best-of-shots is labelled as classical
  post-selection.
- **Small gaps near flip years** (degenerate or fragile) → the interval/fragility machinery turns these into
  "uncertain", not "wrong".
- **Qiskit API churn (2.x)** → build circuits directly (`PauliEvolutionGate` / manual RZZ+RZ+RX) and avoid
  qiskit-optimization. Pin versions in M0.
- **Memory spikes** in scaling sweeps → cap at 24 qubits; run sequentially.
- **Over-claiming** → every quantum number is from a classical simulation of a quantum circuit; no advantage claimed;
  the 12-region result is classical (or hybrid-labelled).
