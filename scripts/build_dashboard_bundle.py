"""Create a portable qBraid-Lab dashboard handoff ZIP (no network activity)."""
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


ROOT = Path(__file__).resolve().parents[1]
FILES = (
    "notebooks/paperflip_dashboard.ipynb",
    "notebooks/data/quantum_cache_2033.json",
    "notebooks/data/independent_region_views_2033.json",
    "artifacts/README.md",
    "artifacts/qbraid_dqa_2033_20q.qasm",
    "artifacts/qbraid_dqa_2033_20q.manifest.json",
    "artifacts/qbraid_dqa_2033_3q_smoke.qasm",
    "artifacts/qbraid_dqa_2033_3q_smoke.manifest.json",
    "README.md",
)


def main() -> None:
    output = ROOT / "artifacts" / "paperflip_qbraid_lab_dashboard_bundle.zip"
    with ZipFile(output, "w", ZIP_DEFLATED) as archive:
        for relative in FILES:
            path = ROOT / relative
            if not path.exists():
                raise FileNotFoundError(f"generate missing dashboard asset first: {relative}")
            archive.write(path, relative)
    print(output)


if __name__ == "__main__":
    main()
