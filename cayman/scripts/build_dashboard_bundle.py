"""Create a portable qBraid-Lab dashboard handoff ZIP (no network activity)."""
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


ROOT = Path(__file__).resolve().parents[1]
FILES = (
    "notebooks/paperflip_dashboard.ipynb",
    "notebooks/data/quantum_cache_2033.json",
    "notebooks/data/independent_region_views_2033.json",
    "artifacts/README.md",
    "artifacts/BUNDLE_NOT_STANDALONE.md",
    "artifacts/qbraid_dqa_2033_20q.qasm",
    "artifacts/qbraid_dqa_2033_20q.manifest.json",
    "artifacts/qbraid_dqa_2033_3q_smoke.qasm",
    "artifacts/qbraid_dqa_2033_3q_smoke.manifest.json",
    "artifacts/qbraid_runs/README.md",
    "artifacts/qbraid_runs/smoke_3q_counts.json",
    "artifacts/qbraid_runs/smoke_3q_verified_metrics.json",
    "artifacts/dashboard_pins/dqa_2033_aer_8000_seed20264139.json",
    "artifacts/dashboard_pins/dqa_2033_aer_8000_seed20264139.png",
    "artifacts/qaoa_landscape_pacific_nw_2033.png",
    "artifacts/qaoa_landscape_pacific_nw_2033.json",
    "artifacts/qaoa_yearly_probability_pacific_nw.png",
    "artifacts/qaoa_yearly_probability_pacific_nw.json",
    "artifacts/qaoa_p1_walkthrough_pacific_nw_2033.png",
    "README.md",
    "QBRAID_START_HERE.md",
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
