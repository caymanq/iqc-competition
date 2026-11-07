"""Refresh the Cayman copy inventory after adding preserved Lab files."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "SNAPSHOT_MANIFEST.json"


def main() -> None:
    files = {}
    for path in sorted(ROOT.rglob("*")):
        if path.is_file() and path != OUTPUT:
            files[str(path.relative_to(ROOT))] = {
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "bytes": path.stat().st_size,
            }
    OUTPUT.write_text(json.dumps({
        "schema_version": 1,
        "source_commit": "ff76327",
        "copy_policy": "Copied from root; excludes .git, environments, caches, credentials, and recursive ZIP bundles.",
        "files": files,
    }, indent=2) + "\n")


if __name__ == "__main__":
    main()
