"""Create a reviewed, self-contained Cayman copy without moving root files."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
import sys
from zipfile import ZipFile


ROOT = Path(__file__).resolve().parents[1]
DESTINATION = ROOT / "cayman"
TOP_LEVEL = (
    "pyproject.toml",
    "README.md",
    "QBRAID_START_HERE.md",
    "configs",
    "docs",
    "notebooks",
    "src",
    "tests",
    "scripts",
)
ARTIFACTS = (
    "artifacts/README.md",
    "artifacts/BUNDLE_NOT_STANDALONE.md",
    "artifacts/dashboard_pins",
    "artifacts/qaoa_landscape_pacific_nw_2033.json",
    "artifacts/qaoa_landscape_pacific_nw_2033.png",
    "artifacts/qaoa_yearly_probability_pacific_nw.json",
    "artifacts/qaoa_yearly_probability_pacific_nw.png",
    "artifacts/qaoa_p1_walkthrough_pacific_nw_2033.png",
    "artifacts/qbraid_dqa_2033_20q.manifest.json",
    "artifacts/qbraid_dqa_2033_20q.qasm",
    "artifacts/qbraid_dqa_2033_3q_smoke.manifest.json",
    "artifacts/qbraid_dqa_2033_3q_smoke.qasm",
    "artifacts/qbraid_runs",
)
SKIP_NAMES = {".git", ".venv", "__pycache__", ".pytest_cache", "cayman"}


def copy_item(relative: str) -> None:
    source, target = ROOT / relative, DESTINATION / relative
    if source.is_dir():
        shutil.copytree(
            source, target,
            ignore=shutil.ignore_patterns(*SKIP_NAMES, "*.zip", "*.pyc"),
        )
    else:
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    if DESTINATION.exists():
        if "--refresh" not in sys.argv:
            raise SystemExit(
                "cayman/ already exists; refusing to overwrite a snapshot or recovered Lab files. "
                "Use --refresh only to update the reviewed copy while preserving cayman/lab_saved/."
            )
        for path in DESTINATION.iterdir():
            if path.name == "lab_saved":
                continue
            if path.is_dir():
                shutil.rmtree(path)
            else:
                path.unlink()
    else:
        DESTINATION.mkdir()
    for relative in (*TOP_LEVEL, *ARTIFACTS):
        copy_item(relative)

    (DESTINATION / "lab_saved").mkdir(exist_ok=True)
    lab_readme = DESTINATION / "lab_saved" / "README.md"
    if not lab_readme.exists():
        lab_readme.write_text(
            "# Recovered qBraid Lab originals\n\n"
            "No recovery attachment had arrived when this snapshot was created. "
            "Place any user-provided Lab ZIP/notebook/manifest here unchanged, with a "
            "provenance note. These originals are intentionally separate from "
            "`notebooks/paperflip_dashboard.ipynb`, the reviewed runnable copy.\n"
        )
    if "--lab-recovery" in sys.argv:
        position = sys.argv.index("--lab-recovery") + 1
        if position >= len(sys.argv):
            raise SystemExit("--lab-recovery requires a ZIP path")
        recovery = Path(sys.argv[position]).resolve()
        if not recovery.is_file() or recovery.suffix.lower() != ".zip":
            raise SystemExit("Lab recovery input must be an existing ZIP")
        with ZipFile(recovery) as archive:
            names = [name for name in archive.namelist() if not name.endswith("/")]
            if names != ["cayman-lab-recovery/MANIFEST.md"]:
                raise SystemExit(f"Expected manifest-only recovery ZIP, found: {names}")
            manifest_text = archive.read(names[0]).decode("utf-8")
        suspicious = ("password=", "api_key=", "token=", "secret=")
        if any(marker in manifest_text.lower() for marker in suspicious):
            raise SystemExit("Recovery manifest appears to contain a secret; refusing to copy it")
        copied_recovery = DESTINATION / "lab_saved" / recovery.name
        shutil.copy2(recovery, copied_recovery)
        (DESTINATION / "lab_saved" / "MANIFEST.md").write_text(manifest_text)
        (DESTINATION / "lab_saved" / "RECOVERY_PROVENANCE.md").write_text(
            "# Recovery provenance and gap\n\n"
            f"- Source attachment: `{recovery.name}` (manifest-only ZIP)\n"
            f"- SHA-256: `{digest(copied_recovery)}`\n"
            "- Connector recovery produced no Lab notebook or saved-file content.\n"
            "- This portable handoff therefore contains committed branch work only; "
            "it does **not** claim to capture the user's full qBraid Lab session.\n"
            "- The empty connector listing does not prove no saved Lab files exist. "
            "On-demand instance disks may not sync to cloud storage, and the connector "
            "storage coverage is unknown.\n"
            "- A later downloaded notebook may be added here unchanged as a separate "
            "preserved artifact; it must not silently replace the reviewed dashboard.\n"
        )
    (DESTINATION / "README_CAYMAN.md").write_text(
        "# Cayman self-contained dashboard copy\n\n"
        "This directory is a **copy**, not a move: the repository root remains the "
        "canonical project. It includes source, configs, docs, tests, the generated "
        "notebook, and committed static evidence. It intentionally excludes Git "
        "metadata, credentials, virtual environments, Python caches, and recursive ZIP bundles.\n\n"
        "## Jaxson: clone the exact branch\n\n"
        "```bash\n"
        "git clone --branch cursor/paper-phase-transition-plan-8ab6 --single-branch "
        "https://github.com/caymanq/iqc-competition.git\n"
        "cd iqc-competition/cayman\n"
        "```\n\n"
        "## Reliable path-independent setup\n\n"
        "From `iqc-competition/cayman/`, explicitly install into the active "
        "kernel/interpreter (this does not run when the notebook runs):\n\n"
        "```bash\n"
        "python - <<'PY'\n"
        "from pathlib import Path\n"
        "import subprocess, sys\n"
        "root = Path.cwd().resolve()\n"
        "if not (root / 'pyproject.toml').is_file():\n"
        "    raise SystemExit('Run this command from the cayman directory.')\n"
        "subprocess.run([sys.executable, '-m', 'pip', 'install', '-e', str(root) + '[dashboard,quantum,dev]'], check=True)\n"
        "PY\n"
        "python scripts/smoke_dashboard_notebook.py\n"
        "python -m pytest -q\n"
        "```\n\n"
        "Launch/open `notebooks/paperflip_dashboard.ipynb` in qBraid Lab. Its "
        "bootstrap resolves its own copy's `src/` path and checks dependencies "
        "without installing or accessing the network during Run All. It prints "
        "`pinned-artifacts-v1-2026-11-07`.\n\n"
        "## Saved evidence\n\n"
        "- `artifacts/dashboard_pins/`: fixed 2033 local-Aer DQA raw counts, "
        "provenance, and histogram.\n"
        "- `artifacts/qaoa_yearly_probability_pacific_nw.*`: fixed 2026–2040 "
        "local-statevector p=1 QAOA heatmap and provenance.\n"
        "- `lab_saved/`: preserved user-recovered Lab originals, never used to "
        "silently replace the reviewed notebook.\n"
        "\n## qBraid account boundary\n\n"
        "The saved dashboard and its remaining interactive teaching views use "
        "committed artifacts or local CPU/Aer statevectors only. They do not need "
        "Cayman's credentials, organization, qBraid account, provider access, or "
        "remote job submission. If Jaxson later chooses to submit a real qBraid "
        "job, that must be authorized from Jaxson's own account after separately "
        "checking provider entitlement and billing; it is optional and not needed "
        "for this dashboard.\n"
    )

    manifest = {}
    for path in sorted(DESTINATION.rglob("*")):
        if path.is_file():
            manifest[str(path.relative_to(DESTINATION))] = {
                "sha256": digest(path), "bytes": path.stat().st_size,
            }
    (DESTINATION / "SNAPSHOT_MANIFEST.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "source_commit": "ff76327",
                "copy_policy": "Copied from root; excludes .git, environments, caches, credentials, and ZIP bundles.",
                "files": manifest,
            },
            indent=2,
        )
        + "\n"
    )
    print(DESTINATION)


if __name__ == "__main__":
    main()
