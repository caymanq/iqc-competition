VASION IQC 2026 — CVaR alpha sweep + 2026–2040 Classiq comparison
====================================================================

This is a SEPARATE, complete Classiq Studio Python project. It does not replace
or modify any existing p=2/p=3 scripts or CSVs in your old workspace.

FILES (KEEP ALL FIVE FILES TOGETHER)
  vasion_cvar_alpha_timeline.py            <-- new controller script
  vasion_qaoa_p3_cvar.py                   <-- validated exact statevector engine
  vasion_classiq_qaoa_p3.py                <-- existing 20-qubit Classiq circuit
  paper_phase_transition_baseline.py       <-- exact minimum-cut answer
  paper_phase_transition_20_industries.json

STUDIO SETUP
  1. Upload the extracted folder "vasion_cvar_alpha_project" into Classiq Studio.
  2. Right-click that folder and select "Open in Integrated Terminal".
     Alternatively, cd to the folder in the terminal yourself.
  3. If dependencies are missing:
       python -m pip install numpy scipy numba networkx matplotlib
     Classiq's SDK should already be available in Classiq Studio.

STEP 1 — TUNE CVaR ALPHA ON 2036
  python vasion_cvar_alpha_timeline.py --phase tune --restarts 2 --maxiter 75 --shots 4096 --classiq

  Tests alpha = 0.05, 0.10 and 0.20 with the SAME initial starts for a fair
  comparison. It minimizes CVaR using exact statevectors, computes the mean
  energy and exact classical ground-state probability, and checks each tuned
  result using 4096 Classiq measurement shots. By default it selects alpha by
  the LOWEST expected energy, not by the known answer.

  If you specifically want to select alpha by the chance of measuring the 2036
  classical ground state, add: --select-by probability
  CAUTION: that is benchmark-guided hyperparameter tuning. The optimizer
  still uses only CVaR energy, but the alpha selection uses the known answer.

STEP 2 — FULL YEARLY RUN, 2026 THROUGH 2040
  python vasion_cvar_alpha_timeline.py --phase timeline --restarts 1 --maxiter 40 --shots 4096 --classiq

  This recalculates AI pressure, optimizes all six gamma/beta angles for every
  year, and executes one verification Classiq job per year with 4096 shots.
  Because it runs exact 20-qubit statevectors over 15 years, it is CPU-heavy.
  Results are saved after EACH year so partial progress is preserved.

OPTIONAL — TRY JUST 2035 AND 2036 BEFORE RUNNING ALL 15 YEARS
  python vasion_cvar_alpha_timeline.py --phase timeline --start-year 2035 --end-year 2036 --maxiter 20 --classiq

OPTIONAL — NO CLASSIQ JOBS, JUST LOCAL EXACT STATEVECTOR
  Remove --classiq from either command. This is good for code testing, but
  isn't a second independent Classiq verification.

OUTPUTS (IN A NEW SUBFOLDER: cvar_alpha_timeline_outputs/)
  cvar_alpha_2036_tuning.csv             side-by-side alpha comparison
  cvar_alpha_2036_history.csv            complete COBYLA evaluation history
  selected_alpha.json                    chosen alpha and angles
  tune_2036_alpha_XX_classiq_measurements.csv  raw Classiq outcome tables
  cvar_timeline_2026_2040.csv            full year-by-year comparison
  cvar_timeline_2026_2040_optimization_history.csv
  timeline_YYYY_classiq_measurements.csv Classiq measurement data for each year
  energy_comparison.png                  classical energy vs QAOA expectations
  digital_adoption_comparison.png        counts from classical and most likely
  ground_state_probability.png           ground-state sampling probability

EXPERIMENT DESIGN
  - QAOA p=3: six angles, 20 qubits, 24 edges, original README values.
  - CVaR alpha is the fraction of lowest-energy probability mass included in
    the CVaR energy. alpha=0.05/0.10/0.20 does NOT mean the top 5/10/20 states.
  - COBYLA sees ONLY CVaR energy, not the bitstring of the correct answer.
  - For each year, the classical minimum-cut solution is used for E_min and
    to EVALUATE the probability of the true ground state.
  - At 2036, the exact minimum is E=-5.55 (all 20 digital).
  - The exact statevector optimizer is purely classical simulation, NOT a
    physical quantum machine. Classiq verification is also a simulator.
  - Exact p_ground is a statevector probability, while Classiq p_ground is
    an empirical frequency from a finite number of shots.
  - Compare CVaR QAOA to classical baseline honestly. Do not claim quantum
    speedup or a hardware advantage from these simulations.

IMPORTANT
  Don't paste these scripts into Classiq's native Qmod Model tab. Run them as
  PYTHON files in Classiq Studio (the VS Code-like interface).
