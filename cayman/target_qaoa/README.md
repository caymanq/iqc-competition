# Constrained local QAOA target-selection comparison

This study uses the supplied four-year target-selection inputs. It is separate
from the industry-adoption dashboard: **here bit 1 means TARGET SELECTED**,
not paper/digital adoption.

## Lossless optimization reduction

For each year, candidates are eligible only when `1 <= flip_year-year <= 4`.
All regional costs are one, attractiveness is one, values are positive, and
there are no pair bonuses. Thus each industry's highest-value region can be
selected first; all equal best regional alternatives are retained as a mapping
tie. The remaining optimization has one bit per eligible industry, not a bit
per industry-region pair. The supplied 2031–32 full formulation has 75
candidates (78 QUBO variables including auxiliaries), so this study does not
claim to statevector-simulate that full QUBO.

With positive values and unit costs, the optimum selects exactly
`k=min(5, eligible industries)` industries. This is lossless for **objective
optimization** in this documented instance family. It is not
distribution-equivalent to the full regional QUBO: QAOA marginals here are
industry-selection probabilities, not regional target probabilities.

## QAOA implementation

The local ideal p=1 statevector lives in the cardinality-`k` feasible subspace,
with dimension `C(n,k)`, and begins uniformly over feasible plans. Its
diagonal cost is `H_C=-sum_i value_i x_i`; the cost phase is
`exp(+i gamma value(plan))`. The mixer is a fixed-order product of
number-preserving XY rotations over all industry pairs:

\[
e^{-i\beta (X_iX_j+Y_iY_j)/2}.
\]

This is a constrained alternating-operator/product-formula ansatz, not
standard unconstrained-X-mixer QAOA. Feasibility mass is exactly one by basis
construction. A fixed 5×5 `(gamma,beta)` grid performs 25 local objective
evaluations per completed year. No exact solution is inserted into the initial
state or used to alter probabilities.

## Outputs

Run:

```bash
cd cayman
python target_qaoa/run_constrained_target_qaoa.py
```

Results are saved in `results/target_selection_qaoa_4year/`:
white-background exact, QAOA-marginal, uniform-feasible, and difference
heatmaps; raw JSON; yearly metrics; and industry-to-tied-region mapping.
The metrics separate basis/mixer-map construction, the 25-evaluation angle
search, and state-preparation/cost/mixer/measurement time for the selected
evaluation.

Gray heatmap cells mean ineligible/no-candidate, not zero selection. Years
2035–2040 have no eligible candidates under the supplied flip-year inputs and
are intentionally empty. Exact heatmap marks one representative tied optimum;
all tied industry optima count toward reported QAOA optimum probability.

These are local simulated optimization outputs from supplied flip-year
assumptions, not observed outcomes, causal estimates, hardware results, or
forecasts.

## p=2 comparison and adoption overlay

Run the bounded two-layer comparison:

```bash
cd cayman/target_qaoa
python run_p2_target_qaoa_overlay.py
```

It evaluates a deterministic 5⁴ grid (625 p=2 angle settings per eligible
year) and includes every p=1 solution as an identity-second-layer incumbent
(`gamma_2=beta_2=0`). Results therefore cannot report a p=2 expected value
worse than that evaluated incumbent; any lack of material improvement is
preserved rather than tuned away.

`results/target_selection_qaoa_p2_4year/` contains p=2 metrics, a p=1-versus-
p=2 marginal comparison, and `yearly_recommendations.csv`. The latter records
the exact representative, tied-best regions, and a **whole feasible MAP
bitstring** recommendation from p=2 (not a set manufactured from independent
marginals), including its plan value and gap.

The overlay uses the already-saved Pacific NW adoption heatmap only as a
background. It retains its white adoption flip crosses and `P(digital bit 0)`
colorbar; black × markers are exact target recommendations, magenta hollow
circle area is `P(target selected bit 1)`, and black outlined squares are the
p=2 MAP-plan selections. Target selection spans five regions, so neither its
markers nor its bit convention are adoption probabilities. All target markers
are placed at the planning year; 2035–2040 are explicitly no-eligible-target
columns.

For the primary comparison, the script also creates two non-blended
foreground heatmaps: exact target `x_i` (classical) and p=2 target
`P(x_i=1)` (quantum). Both use the same fixed 0–1 sequential blue scale; pale
blue explicitly means no eligible target/ineligible, not zero probability.
The saved Pacific NW adoption flip markers are white context annotations only.
The same black × exact-reference mask appears on both
panels. It is not evidence that p=2 produces the exact feasible plan; the
separate p=2 MAP plan remains in the recommendation CSV.
