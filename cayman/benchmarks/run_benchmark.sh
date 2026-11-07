#!/usr/bin/env bash
set -euo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
python_bin="${PYTHON_BIN:-python3}"
mkdir -p "$root/results"
g++ -O3 -std=c++20 -DNDEBUG "$root/ising_benchmark.cpp" -o "$root/ising_benchmark"
"$root/ising_benchmark" --test
{
  echo '{'
  printf '  "compiler": '; g++ --version | "$python_bin" -c 'import json,sys; print(json.dumps(sys.stdin.readline().strip()))'; echo ','
  printf '  "kernel": '; uname -srmo | "$python_bin" -c 'import json,sys; print(json.dumps(sys.stdin.read().strip()))'; echo ','
  printf '  "cpu_model": '; (awk -F: '/model name/{print $2; exit}' /proc/cpuinfo || true) | "$python_bin" -c 'import json,sys; print(json.dumps(sys.stdin.read().strip()))'; echo ','
  echo '  "thread_policy": "single process; no OpenMP/threaded libraries",'
  echo '  "qaoa": "ideal p=1 statevector; exact expectation; 3x3 gamma/beta grid (9 optimizer evaluations)",'
  echo '  "instance_family": "seeded dense ferromagnetic J>=0; mixed-sign h; bit 0=digital; E=-sum J ss-sum h s"'
  echo '}'
} > "$root/results/machine_metadata.json"
"$root/ising_benchmark" run "$root/results/raw.csv"
"$python_bin" "$root/plot_results.py"
