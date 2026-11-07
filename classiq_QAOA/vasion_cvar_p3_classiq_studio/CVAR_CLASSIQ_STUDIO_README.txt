VASION / IQC 2026 — CVaR-QAOA + known-target diagnostic (p=3)
================================================================

WHAT IT DOES
- Keeps your original 20-industry Classiq Hamiltonian and p=3 circuit unchanged.
- Locally simulates the exact 20-qubit p=3 statevector (Numba accelerated).
- Runs SciPy COBYLA to minimize CVaR energy of the lowest-energy 10% of outcomes.
- Separately runs a diagnostic maximizing P(11111111111111111111).
- Sends the selected angles to your existing Classiq quantum program for 4,096
  measurement shots per experiment, and saves both comparisons.

HOW TO INSTALL IN YOUR EXISTING CLASSIQ STUDIO PROJECT
1. Open the folder containing vasion_classiq_qaoa_p3.py.
2. Upload vasion_qaoa_p3_cvar.py into that SAME folder.
3. Check that these files are still in the same folder:
       vasion_classiq_qaoa_p3.py
       paper_phase_transition_baseline.py
       paper_phase_transition_20_industries.json
4. In Classiq Studio's terminal, navigate to that folder.
5. Install the one extra acceleration dependency if necessary:
       python -m pip install numba
   (numpy, scipy, networkx and classiq are also needed, as in your old project.)

FIRST RUN (CVaR only)
    python vasion_qaoa_p3_cvar.py --year 2036 --mode cvar --restarts 1 --maxiter 50 --shots 4096

SECOND RUN (both objectives)
    python vasion_qaoa_p3_cvar.py --year 2036 --mode both --restarts 2 --maxiter 100 --shots 4096

LIGHTWEIGHT TEST WITHOUT CLOUD EXECUTION
    python vasion_qaoa_p3_cvar.py --year 2036 --mode both --restarts 1 --maxiter 20 --no-classiq

OUTPUTS (NEW NAMES; DOES NOT OVERWRITE ORIGINAL P2/P3 FILES)
    cvar_2036_history.csv                 COBYLA objective history
    target_2036_history.csv               Known-target optimization history
    cvar_2036_classiq_measurements.csv    Measurement table from Classiq
    target_2036_classiq_measurements.csv  Measurement table from Classiq
    cvar_vs_target_2036_local_summary.csv Exact statevector calculations
    cvar_vs_target_2036_summary.csv       Statevector + Classiq comparison

SCIENCE / JUDGING
- CVaR objective: sum of E(z) weighted by P(z) over the LOWEST 10% of
  probability mass; it does not tell COBYLA which bitstring is optimal.
- The target diagnostic explicitly favors the 20-ones state and SHOULD NOT
  be described as independently solving the Ising problem.
- All exact statevector optimizations run on a classical laptop/server.
- A Classiq statevector simulation is not hardware quantum advantage.
- Both local and Classiq calculations are compared against the identical
  Ising Hamiltonian. You can present exact/classical, standard QAOA, and CVaR.
- Increasing CVaR performance does not necessarily improve mean energy or
  exact-ground-state probability; compare all metrics honestly.
