"""Guarded dense-mincut-only scale extension; never invokes QAOA."""
from __future__ import annotations
import csv
import json
import os
from pathlib import Path
import resource
import subprocess
import time

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "results" / "classical_extension.csv"
SIZES = (4000, 6000, 8000, 10000)
MEMORY_CAP_BYTES = int(3.5 * 1024**3)
TIMEOUT_SECONDS = 90

def cap_memory() -> None:
    resource.setrlimit(resource.RLIMIT_AS, (MEMORY_CAP_BYTES, MEMORY_CAP_BYTES))

def main() -> None:
    subprocess.run(["g++", "-O3", "-std=c++20", "-DNDEBUG", "ising_benchmark.cpp", "-o", "ising_benchmark"],
                   cwd=ROOT, check=True)
    with OUT.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=[
            "family","n","repeat","seed","graph_build_s","energy_precompute_s","mincut_s",
            "qaoa_one_eval_s","qaoa_optimizer_s","qaoa_eval_count","exact_energy",
            "qaoa_expected_energy","qaoa_ground_probability","qaoa_norm","status",
            "peak_rss_kb","timeout_s","memory_cap_bytes","stderr",
        ])
        writer.writeheader()
        for n in SIZES:
            command = [str(ROOT / "ising_benchmark"), "--classical-one", str(n)]
            started = time.monotonic()
            process = subprocess.Popen(command, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                       preexec_fn=cap_memory)
            peak = 0
            timed_out = False
            while process.poll() is None:
                try:
                    for line in Path(f"/proc/{process.pid}/status").read_text().splitlines():
                        if line.startswith("VmRSS:"):
                            peak = max(peak, int(line.split()[1]))
                except FileNotFoundError:
                    pass
                if time.monotonic() - started > TIMEOUT_SECONDS:
                    timed_out = True
                    process.kill()
                    break
                time.sleep(.02)
            stdout, stderr = process.communicate()
            elapsed = time.monotonic() - started
            row = {"family":"classical_extension","n":n,"repeat":0,"seed":20261107 + 1000*n,
                   "energy_precompute_s":0,"qaoa_one_eval_s":0,"qaoa_optimizer_s":0,
                   "qaoa_eval_count":0,"qaoa_expected_energy":0,"qaoa_ground_probability":0,
                   "qaoa_norm":0,"peak_rss_kb":peak,"timeout_s":TIMEOUT_SECONDS,
                   "memory_cap_bytes":MEMORY_CAP_BYTES,"stderr":stderr.replace("\n"," | ")}
            if not timed_out and process.returncode == 0:
                data = json.loads(stdout)
                row.update(graph_build_s=data["graph_build_s"], mincut_s=data["mincut_s"],
                           exact_energy=data["exact_energy"], status="completed")
            elif timed_out:
                row.update(graph_build_s=elapsed, mincut_s="", exact_energy="", status="timeout")
            elif process.returncode == 3:
                row.update(graph_build_s=elapsed, mincut_s="", exact_energy="", status="memory_cap")
            else:
                row.update(graph_build_s=elapsed, mincut_s="", exact_energy="", status=f"failed_{completed.returncode}")
            writer.writerow(row); handle.flush()
            print(f"n={n}: {row['status']}, rss_kb={peak}, elapsed_s={elapsed:.2f}")
            if row["status"] != "completed":
                break

if __name__ == "__main__":
    main()
