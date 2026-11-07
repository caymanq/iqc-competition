# Original empirical benchmark source and saved results

Actual source copies from immutable commit e02f5fba57be8279aadc7f0ed7c597a61271f102 of caymanq/iqc-competition, `cayman/benchmarks/`. Retrieved with narrow sanctioned GitHub file reads, not a clone. File-level immutable raw URLs and SHA-256 hashes are in SOURCE_PROVENANCE.json. Transport wrappers were removed and terminal newlines normalized; no algorithm/source edits were made. README_ORIGINAL.md is the repository's original README.

## What produces what
- `ising_benchmark.cpp`: C++20 exact Dinic min-cut and ideal p=1 CPU statevector timing/quality measurements. Direct diagonal phases and in-place RX kernels, not dense unitary matrices; Gray-code energy precomputation. No provider SDK/jobs.
- `plot_results.py`: Python/Matplotlib reads saved CSVs, computes summaries and renders figures. It does NOT run the C++ benchmark. It writes raw.json, summary.csv, runtime_empirical.png/.svg, qaoa_components.png, runtime_common_zoom.png and qaoa_quality.png under results/.
- `run_benchmark.sh`: original orchestration: compile, C++ tests, tiny Qiskit reference check, collect machine metadata, run the EXPENSIVE benchmark, then plot. It overwrites results/raw.csv and metadata/plots.
- `qaoa_python_reference_check.py`: original NumPy/Qiskit tiny sign-convention check, included because the runner depends on it. Not run for the report.
- `extend_classical.py`: original guarded classical-only extension (90s timeout, 3.5 GiB cap). Separate optional script; not automatically called by run_benchmark.sh. Linux /proc and resource module required. Not run for the report; no guarantee of portability beyond the recorded environment.

## Dependencies
Build needs g++ with C++20 support (recorded original g++ 13.3.0), bash and standard C++ library; no BLAS/OpenMP. Plot-only needs Python 3 and Matplotlib. Full runner's reference check additionally needs NumPy and Qiskit. Dependency names are in requirements.txt; historical Python package versions were not recovered, so this is not an exact environment lock. Linux is needed for the guarded extension and original metadata collection.

## Plot saved results only (no new benchmarks)
Use a SCRATCH COPY of this directory if preserving the supplied files; plotting writes/overwrites files in results/.

```bash
python3 -m venv .venv
.venv/bin/pip install matplotlib
.venv/bin/python plot_results.py
```

Saved inputs already included with original expected filenames:
- results/raw.csv = ../metrics/benchmark_raw.csv
- results/summary.csv = ../metrics/benchmark_summary.csv
- results/classical_extension.csv = ../metrics/classical_extension.csv
- results/machine_metadata.json = ../metrics/machine_metadata.json

## Optional expensive reproduction (not executed)
These commands launch NEW local CPU tests/measurements and overwrite saved results. Do not run automatically. Work in a scratch copy and install all requirements first (`python3 -m pip install -r requirements.txt`, preferably inside a virtual environment).

```bash
g++ -O3 -std=c++20 -DNDEBUG ising_benchmark.cpp -o ising_benchmark
PYTHON_BIN=python3 bash run_benchmark.sh
# OPTIONAL separate large classical extension, after base results exist:
python3 extend_classical.py
python3 plot_results.py
```

## Correct aggregation and repeat caveats
The original plotting source sums component medians for end-to-end timing. Its reported quality gap is median expected energy minus median exact energy, which need not be the median paired-run gap. Current report tables preserve these values.

Three repeats apply through 20q, two at 22q, ONE each at 24q and 26q. Classical-only 40–2000 sizes have three repeats; the 4000/6000/8000 guarded extension has ONE repeat each. The 10000 attempt stopped before solve at the memory cap; 28q QAOA was not attempted. An older screenshot saying “median 3 repeats” everywhere is inaccurate for the current larger-size records. No new benchmark, C++ compilation or source reference-check run was performed for report production. These are CPU simulator results, not hardware or quantum advantage.
