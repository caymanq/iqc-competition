20-industry Vasion QAOA p=3 experiment (Classiq Studio)

Place vasion_classiq_qaoa_p3.py NEXT TO the existing:
- paper_phase_transition_baseline.py
- paper_phase_transition_20_industries.json

Do not delete or edit your working p=2 Python file.

From the existing Studio terminal folder:
  python vasion_classiq_qaoa_p3.py --year 2036 --shots 4096 --show
  python vasion_classiq_qaoa_p3.py --year 2036 --optimize --shots 4096 --maxiter 100

p=3 has 6 angles, starting from your latest p=2 optimized angles
and an identity third layer (gamma3=beta3=0). COBYLA can adjust all six.

New results are written into separate p3 files:
- vasion_qaoa_p3_optimized_summary.csv
- vasion_qaoa_p3_optimized_measurements.csv
- cobyla_history_p3_2036.csv

Note: This script passed Python syntax checks, but has not been executed
against Classiq cloud in this environment. If the SDK reports an error,
share the full traceback.
