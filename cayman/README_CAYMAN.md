# Cayman self-contained dashboard copy

This directory is a **copy**, not a move: the repository root remains the canonical project. It includes source, configs, docs, tests, the generated notebook, and committed static evidence. It intentionally excludes Git metadata, credentials, virtual environments, Python caches, and recursive ZIP bundles.

## Jaxson: clone the exact branch

```bash
git clone --branch cursor/paper-phase-transition-plan-8ab6 --single-branch https://github.com/caymanq/iqc-competition.git
cd iqc-competition/cayman
```

## Reliable path-independent setup

From `iqc-competition/cayman/`, explicitly install into the active kernel/interpreter (this does not run when the notebook runs):

```bash
python - <<'PY'
from pathlib import Path
import subprocess, sys
root = Path.cwd().resolve()
if not (root / 'pyproject.toml').is_file():
    raise SystemExit('Run this command from the cayman directory.')
subprocess.run([sys.executable, '-m', 'pip', 'install', '-e', str(root) + '[dashboard,quantum,dev]'], check=True)
PY
python scripts/smoke_dashboard_notebook.py
python -m pytest -q
```

Launch/open `notebooks/paperflip_dashboard.ipynb` in qBraid Lab. Its bootstrap resolves its own copy's `src/` path and checks dependencies without installing or accessing the network during Run All. It prints `pinned-artifacts-v1-2026-11-07`.

## Saved evidence

- `artifacts/dashboard_pins/`: fixed 2033 local-Aer DQA raw counts, provenance, and histogram.
- `artifacts/qaoa_yearly_probability_pacific_nw.*`: fixed 2026–2040 local-statevector p=1 QAOA heatmap and provenance.
- `lab_saved/`: preserved user-recovered Lab originals, never used to silently replace the reviewed notebook.

## qBraid account boundary

The saved dashboard and its remaining interactive teaching views use committed artifacts or local CPU/Aer statevectors only. They do not need Cayman's credentials, organization, qBraid account, provider access, or remote job submission. If Jaxson later chooses to submit a real qBraid job, that must be authorized from Jaxson's own account after separately checking provider entitlement and billing; it is optional and not needed for this dashboard.
