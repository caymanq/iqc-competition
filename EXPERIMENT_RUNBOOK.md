# Paper Phase Transition: next-experiment runbook

Status: proposed experiments, not completed runs. Existing Classiq Reports 1–2 and local NumPy experiments are separate execution series; retain that distinction in the ledger.

Challenge reference: https://github.com/PrinterLogic/iqc-2026-paper-phase-transition

## Presentation target

Build one argument: define the scenario; establish a trustworthy reference; measure quantum performance; test robustness and regional scale; demonstrate a decision. The challenge's approximately five-minute presentation is judged on model (25%), quantum results (25%), classical comparison/scaling (20%), and story/insight (30%). Its optional extension is budget-constrained sales targeting. Hardware is optional; a quantum simulator qualifies.

## Before running

Freeze the original 20-node model as `original-v1`. Save node order, node IDs, resistances, undirected edges counted once, positive tie strengths, yearly pressure, spin/bit convention, and a hash of the serialized inputs. Save solver versions, backend, machine, objective-evaluation budget, measurement shots, starting-angle policy, and distinct model/optimizer/sampling seeds.

Add a classical-only path that never builds an energy array or statevector. Add explicit model-file inputs for regional and new-data scenarios. The present `paper_transition.run` does neither: it builds a fixed 20-node model and always enumerates quantum basis energies. Its `--seed` controls measurement sampling; optimizer starts are fixed or reused, not randomized. Do not treat new sampling seeds as new optimizer initializations.

Use the same immutable model input for every solver in a comparison. Unknown settings in imported reports stay unknown.

## 1. Certify the original reference

Run minimum cut for every year 2026–2040. At 20 nodes, independently compare optimum energies with exhaustive enumeration once. Then run simulated annealing with 10 solver seeds, a recorded schedule and fixed budget (start with 100,000 proposals per year). Use fresh independent starts for the baseline.

Record optimum energy; SA energy gap; whether SA reaches any optimum; runtime; assignments; industry flip years. Report success fractions over seeds. Equal-energy assignments may differ: energy is the primary correctness metric, and ties should be recorded rather than called failures. A deterministic min-cut solver needs repeated timings, not stochastic seed trials.

Deliverable: certified baseline table and original tipping map. If imported report energies disagree, resolve objective signs, edge counting, coefficients, and bit order before extending the study.

## 2. Measure quantum repeatability fairly

Retain Reports 1–2 as historical demonstrations. For a controlled test, use years 2033, 2035, and 2036; depths p=1 and p=2; three explicitly randomized optimizer initializations per depth/year. This is 18 optimization jobs. Keep the same starting-angle distribution, maximum 100 objective evaluations per job, 4,096 measurement shots, and backend. Record actual evaluations and termination status; a budget stop is not convergence. Expand to five initializations only if useful and affordable.

Record expected-energy gap, best sampled complete-bitstring gap, shot count, optimum sampling success, per-industry digital frequencies, and runtime. On an exact small statevector, also report total probability of any optimum. Separate exact expectation simulation from finite-shot or hardware estimation.

Do not infer a full flip-year map from three selected years. Existing full-sweep agreement remains a reported claim until supported by per-year assignments. Prefer exporting those states from Report 2; if unavailable, perform one documented full sweep. Preserve reversals and any never-flipped nodes.

If claiming warm-start benefits, add a matched warm/cold comparison with the same years, starts, and total evaluation budget; otherwise describe reuse without claiming it improved convergence.

## 3. Identify what causes the cascade

Keep all other inputs fixed and run exact classical sweeps under four scenarios:

- Original model.
- All partner ties removed.
- Healthcare–Insurance tie removed.
- Healthcare resistance lowered by 0.10.

Compare flip-year shifts, the number switching in the largest year, and affected neighbors. A zero effect is a useful result. Do not infer a causal trigger from simultaneous flips alone. A model equilibrium is not a measured real-world cascade.

If individual leverage is promising, lower each industry's resistance by 0.10 in 20 separate experiments. Rank additional digital nodes by a predeclared year, with a consistent intervention-cost assumption. This supports a concrete business story without pretending the assumed intervention has been empirically measured.

## 4. Scale the classical model

Use 20 industries × 1, 3, 6, and 12 regions: 20, 60, 120, and 240 nodes. Optional timing extensions: 480 and 960 nodes.

Create a documented nested region graph. Retain within-region ties; connect the same industry across neighboring regions. Start with cross-region strength 0.05. Use fixed regional shifts spanning −0.15 to +0.15 and a disclosed synthetic noise rule, for example uniform [−0.03,+0.03], clipping resistance to [0,1]. Use five model seeds. Reuse previously generated nodes/edges when extending the graph, so network size is not confounded with regenerating all inputs.

For every size/model seed, solve minimum cut for all 15 years. Check SA at 2033, 2035, and 2036 with three solver seeds and the original fixed proposal budget. Report that a fixed proposal budget gives fewer proposals per node at larger N. If SA quality falls, add a separately labeled fixed-sweeps-per-node experiment instead of silently increasing its budget. SA timing excludes exact verification; never feed the exact solution into SA.

Time graph construction separately from solver execution; perform a warm-up and five timing repeats for min-cut, reporting medians and ranges. Record N, E, total sweep time, and observed peak memory where available. Keep SA quality separate from speed. The all-positive-tie model retains an exact min-cut formulation as it grows; scaling it does not establish a quantum advantage.

## 5. Test regional coupling

On a fixed 240-node instance, vary only cross-region tie strength: 0, 0.05, and 0.15. Run exact sweeps. Report spread of flip years across regions, largest single-year cluster, and a heatmap with consistent color limits. Replicated identical regions without shifts/noise test size, not regional realism.

## 6. Add a separately versioned dataset

Start with one credible public dataset or documented partner dataset. Record publisher, date, geography, variable definitions, missingness, and why each variable proxies paper resistance or digital pressure. Observed digital adoption is not automatically observed paper use.

Publish the conversion rule before inspecting model outcomes. Keep measured columns separate from constructed resistances and assumed ties. Run baseline / low / high transformations, such as resistance offsets of −0.05 / 0 / +0.05 with clipping, to show sensitivity. Call this a data-informed scenario unless there is independent held-out evidence of forecast accuracy.

Use exact classical sweeps first. For quantum testing, choose a documented 20-node subset and rerun the classical solver on that exact same subset. It is a reduced scenario, not a direct solution of the entire regional graph. Full-network neighbor effects are omitted unless explicitly modeled as boundary fields.

## 7. Optional stretch: choose targets under a budget

Use a fixed decision year and candidate subset. State values v_i, costs c_i, budget B, and partner bonuses b_ij. Optimize sum(v_i*x_i) + sum(b_ij*x_i*x_j), subject to sum(c_i*x_i) <= B. Distinguish evidence-based inputs from assumed business values.

Compare against a simple greedy allocation and an exact small-instance optimum. If using QAOA, encode the budget with documented slack bits/penalties; count all extra qubits. Report feasibility rate, spend, objective value, and gap. Do not quietly repair infeasible samples. State that a partnership bonus models joint value; it is not proof one sale causes another.

## Every run exports the same evidence bundle

- `metadata.json`: run ID, question, parent run, model ID/hash, input files, solver/backend/version, machine, all seeds, budgets, timing boundaries, and convergence status.
- `year_results.csv`: year, N, E, reference energy, method energy, expected/best-sample gaps as applicable, evaluations, shots, runtime, success and feasibility indicators.
- `node_results.csv`: node, industry, region, year, state/probability, flip year or never-flipped flag, and reversals.
- Full sampled bitstrings/counts and optimizer trace for quantum jobs; original reports and backend job IDs when available.
- `summary.md`: question, one result, comparison, limitation, next decision.

Use absolute energy gap within the same objective as a primary metric. EV/reference-energy quotients are not assignment accuracy and are sensitive to additive energy offsets. Never pool raw energies across different models or years as one quality score.

## Five-minute presentation

1. 0:00–0:40 — Business question, node/tie model, input provenance.
2. 0:40–1:25 — Quantum-derived tipping map and classical agreement or discrepancies.
3. 1:25–2:10 — Quantum energy, sampled quality, and limitations.
4. 2:10–3:00 — Classical scaling, with clear comparison boundaries.
5. 3:00–4:20 — One counterfactual and regional/new-data result; concrete decision implication.
6. 4:20–5:00 — Main lesson; optional budgeted-target result if complete.

Keep all individual-run tables, seeds, and traces in the appendix. Count experiments in the ledger, not as one slide per run.

## Priority if time is short

Must finish: certified original reference; auditable quantum map; honest timing/quality comparison; one causal counterfactual; regional classical scaling. Then add the new-data scenario. Attempt the sales QUBO only after the core results and presentation are complete. No experimental outcome is guaranteed by this plan.
