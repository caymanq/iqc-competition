# Convenience bundle, not a runnable repository

`paperflip_qbraid_lab_dashboard_bundle.zip` is for previewing the notebook,
cached evidence, QASM artifacts, and instructions. It intentionally does not
contain `src/`, `configs/`, `pyproject.toml`, or tests, so it cannot be used as
a standalone installation.

Use the authoritative Git branch instead:

```bash
git clone https://github.com/caymanq/iqc-competition.git
cd iqc-competition
git checkout cursor/paper-phase-transition-plan-8ab6
```

Then follow [`QBRAID_START_HERE.md`](../QBRAID_START_HERE.md).
