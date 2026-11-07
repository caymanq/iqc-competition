# Classical yearly target plans, 2026–2040

These are exact target-selection solutions using the attached script's assumptions and CSV, not re-simulated Ising transitions, QAOA results, observed business outcomes, or calibrated forecasts.

## Unchanged assumptions
Each planning year is solved independently with budget5 (reset each year), seven-year look-ahead, unit cost for every region, equal attractiveness, BASE_VALUE8, no pair bonuses, and at most one region per industry. Only flips strictly after the planning year and within seven years are eligible. There is no carry-over or exclusion of industries selected in previous years.

## Exact scalable classical solution
Because all costs equal1, values are nonnegative and there are no pair bonuses, choose the highest-valued eligible region per industry, then the five highest-valued industries (or all when fewer). This solves this particular constrained model exactly without enumerating its potentially large QUBO. It is not a general solver for arbitrary QUBOs, costs, or pair bonuses. The original QUBO is constructed and its energy verified for each plan.18 small cases also agree with exhaustive QUBO enumeration.

Region ties are broken by input CSV order (California first), not regional preference or evidence. Other regions may be equally optimal. Value ties between industries likewise use deterministic input order. Saved rows represent one exact optimum, not all tied plans.

## Coverage limitation
The last flip year supplied is2035. Under the strict future-flip eligibility rule,2035–2040 contain no eligible targets. Empty plans in those years are exact results for the provided inputs, not an estimate of future market activity. Forecasts beyond those flip years need additional inputs. Source flip years are treated as supplied, not independently validated.

## Outputs
- yearly_summary.csv:15annual optima, feasibility, QUBO energies and single-run local checking times.
- yearly_selected_targets.csv: chosen industry/region, input flip year, value and cost.
- yearly_all_candidates.csv: every eligible annual candidate with selected indicator.
- seven_year_comparison.png: white-background presentation plot.
- validation.json: exhaustive test status.
- target_selection_original.py and quantum_flip_years.csv: exact copies of supplied files.
- run_yearly.py: runnable exact annual extension using only Python standard library; run `python3 run_yearly.py` in this directory. Matplotlib is only needed to recreate the separate plot, not solve plans.

QUBO energy without constant = -total_value - penalty*budget^2. With the budget constant restored, optimum energy=-total_value. Raw omitted-constant energies are not directly comparable across years because penalties change.

## Seven-year rerun
run_yearly.py sets model.LEAD_TIME_YEARS=7 before constructing candidates. Other parameters remain unchanged. The original supplied script remains unchanged for provenance. The comparison PNG shows the previous four-year baseline and the new seven-year result. Urgency is recalculated using the seven-year denominator, so changes reflect both eligibility and urgency weights, not just a larger candidate set.
