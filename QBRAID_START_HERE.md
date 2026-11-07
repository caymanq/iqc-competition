# qBraid start here

**Authoritative handoff:** this Git branch, not the convenience ZIP:
[`cursor/paper-phase-transition-plan-8ab6`](https://github.com/caymanq/iqc-competition/tree/cursor/paper-phase-transition-plan-8ab6).
The ZIP deliberately does not contain the full Python source/config tree.

## Clone the exact branch

```bash
git clone https://github.com/caymanq/iqc-competition.git
cd iqc-competition
git checkout cursor/paper-phase-transition-plan-8ab6
```

## qBraid Lab notebook setup

Open `notebooks/paperflip_dashboard.ipynb`. In its first code cell, run this
from either the repository root **or** the `notebooks/` directory:

```python
from pathlib import Path
repo = Path.cwd()
if not (repo / "pyproject.toml").exists():
    repo = repo.parent
%pip install -e "{repo}[dashboard,quantum,dev]"
```

Then use **Kernel → Restart Kernel and Run All Cells**. The dashboard performs
only local CPU/Aer simulation. It does not authenticate to qBraid, submit a
job, purchase credits, or start a server.

## Safely update an existing Lab checkout

If you have edited the notebook in Lab, do **not** reset, force-pull, or
overwrite it. First save it in the Lab UI, then make a backup/copy:

```bash
git status
cp notebooks/paperflip_dashboard.ipynb notebooks/paperflip_dashboard.local-backup.ipynb
git diff > local-lab-changes.patch
```

Only when `git status` is clean, update without rewriting history:

```bash
git fetch origin
git merge --ff-only origin/cursor/paper-phase-transition-plan-8ab6
```

If it is not clean, keep the backup and ask for help merging the notebook
changes; do not run `git reset`, `git checkout --`, force-pull, or overwrite
the Lab notebook.

## Dashboard controls

- Tabs 1–3 teach the tiny model, 20-industry exact scenarios, and a cached
  Aer distribution. Changes mark cache-backed evidence stale rather than
  silently launching a simulator.
- Tab 3 **Run selected year (local CPU)** creates a new persisted result under
  `results/dashboard_runs/` for the selected 2026–2040 year, current
  ties/resistance scenario, actual shot count, and seed. It never runs
  automatically on slider changes. Each record retains raw counts, model
  fingerprint, exact same-graph reference, algorithm parameters and CPU
  timing. Single-year results deliberately do not show flip-year errors.
- Tab 4 compares one, two, and five nested synthetic regions. Every displayed
  quantum model is an independent 20-node circuit, with no cross-region ties.
  The yellow **Compute selected 20-node view** button is the only action that
  may run a new local CPU statevector calculation; it does not contact qBraid.
- Tab 4's **Compute yearly probability heatmap (local CPU)** is separately
  explicit. It runs one selected independent 20-node region for 2026–2040:
  each year uses a bounded 3×3 standard-p1-QAOA expected-energy grid, then
  displays exact-statevector `P(bit_i=0)` marginals, where bit 0 is digital.
  It persists provenance under `results/qaoa_year_sweeps/`, never submits a
  provider job, and does not imply empirical adoption probabilities.
- Save with **File → Save Notebook** or Ctrl/Cmd+S. When finished, use
  **Kernel → Shut Down Kernel** and stop the Lab session in the qBraid UI.

## Verify before demonstrating

From the repository root:

```bash
python -m pytest -q
python scripts/smoke_dashboard_notebook.py
```

The smoke test executes the current notebook headlessly and exercises its
widget callbacks. It is bounded and does not use remote compute.

## Existing qBraid run evidence

`artifacts/qbraid_runs/` contains sanitized provenance and raw counts supplied
by the parent executor:

- 3-qubit smoke is completed and independently scored against the committed
  manifest/config at **80.5% exact-optimum probability**.
- The 20-qubit 2033 DQA job is **RUNNING/PENDING**. No results or derived
  metrics are claimed for it.

## Copy/paste task for a qBraid AI agent

```text
Clone https://github.com/caymanq/iqc-competition.git and checkout
cursor/paper-phase-transition-plan-8ab6. Open
notebooks/paperflip_dashboard.ipynb, run:

from pathlib import Path
repo = Path.cwd()
if not (repo / "pyproject.toml").exists(): repo = repo.parent
%pip install -e "{repo}[dashboard,quantum,dev]"

Restart the kernel and Run All. Then run `python -m pytest -q` and
`python scripts/smoke_dashboard_notebook.py` from the repo root. Do not
submit qBraid/hardware jobs, buy credits, request credentials, start a server,
or modify the model. Keep all quantum work local to the existing cached or
explicit 20-node CPU simulations.
```
