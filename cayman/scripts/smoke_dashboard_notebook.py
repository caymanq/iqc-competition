"""Execute the dashboard notebook headlessly without modifying its source."""
from pathlib import Path
from tempfile import TemporaryDirectory
import os
import nbformat
from nbclient import NotebookClient


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "notebooks" / "paperflip_dashboard.ipynb"


def main() -> None:
    os.environ["PAPERFLIP_DASHBOARD_SMOKE"] = "1"
    with TemporaryDirectory() as temp:
        output = Path(temp) / SOURCE.name
        notebook = nbformat.read(SOURCE, as_version=4)
        client = NotebookClient(notebook, timeout=30, interrupt_on_timeout=True, kernel_name="python3")
        client.on_cell_start = lambda cell, cell_index, **_: print(f"Executing notebook cell {cell_index}")
        client.execute(cwd=str(ROOT))
        nbformat.write(notebook, output)
    print("Dashboard notebook headless smoke test passed")


if __name__ == "__main__":
    main()
