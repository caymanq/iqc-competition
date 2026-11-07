# Supplied generated-results handoff

Source attachment: `cayman-latest-generated-results_5340.zip`, preserved
unchanged beside the extracted files. `HANDOFF_MANIFEST.json` is the supplied
file inventory and checksum record.

## Status labels

- `target_selection_4year/` is the current user-selected **four-year**
  lead-time default. `run_yearly.py` explicitly sets
  `DEFAULT_LEAD_TIME_YEARS=4`; running it performs the documented 15 annual
  exact target-selection solves and 18 tiny exhaustive QUBO checks.
- `archived_7year_comparison/` is preserved for comparison only and is
  superseded by the current four-year default.
- Supplied `quantum_flip_years.csv` values are treated as input assumptions:
  they are not independently verified QAOA output, empirical observations,
  calibrated forecasts, or causal evidence.
- `scaling_plots/` contains **assumed/theoretical** scaling illustrations,
  including a linear-QAOA/quadratic-mincut assumption. Those assumptions are
  distinct from the measured CPU benchmark in
  `../../benchmarks/results/`.
- `white_plots/empirical_runtime_white.png` is preserved as an original
  user-provided recolor. Its label stating “median of 3 repeats” is not
  accurate for the larger QAOA points; use the corrected presentation plot
  `../../benchmarks/results/runtime_empirical.png` and raw CSV/JSON for
  repeat counts and measurements.

No files here trigger qBraid access, hardware work, paid jobs, or provider
submission.
