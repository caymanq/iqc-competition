# Recorded run notes

- Completed on the VM described in `machine_metadata.json`; one process, no
  OpenMP, no swap.
- Common QAOA/min-cut sizes: 4–20 (3 repeats), 22 (2 repeats), 24 and 26
  (1 repeat each). Every recorded row completed; no timeout/censored run.
- Classical dense min-cut only reached 20, 40, 80, 120, 160, 200, 240, 500,
  1000, and 2000 with three repeats each.
- The 26-qubit ideal-statevector run used a 67,108,864-amplitude complex
  vector (~1 GiB) plus a 67,108,864-entry double energy table (~512 MiB),
  before allocator/runtime overhead. Its measured end-to-end median-equivalent
  single run was 47.81 s.
- A 28-qubit extension would require approximately 4 GiB for the complex
  statevector plus 2 GiB for energies before overhead. The VM had about
  4.5 GiB reported available and no swap after the 26-qubit run, so it was
  intentionally not attempted to avoid OOM/swap. This is the practical
  statevector ceiling for this run, not a hardware-qubit limit.
- The p=1 grid quality is intentionally reported as measured: expected-energy
  gap grows with n and exact-ground probability falls to `1.61e-09` at n=26.
  No classical polishing or exact-state injection was used.
