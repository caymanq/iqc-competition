"""Execute current dashboard tabs and export standalone HTML previews.

No server is launched: Chrome opens the resulting local HTML files directly.
The files preserve widget state for rendered preview, but static HTML cannot
run Python callbacks after it has been opened outside Jupyter.
"""
from pathlib import Path
import os
import shutil
import nbformat
from nbclient import NotebookClient
from nbconvert import HTMLExporter


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "notebooks" / "paperflip_dashboard.ipynb"
DESTINATION = ROOT / "artifacts" / "dashboard_previews"
WIDGET_ASSETS = ROOT / "scripts" / "widget_preview_assets"


def render(tab: int, slug: str) -> None:
    os.environ["PAPERFLIP_DASHBOARD_TAB"] = str(tab)
    os.environ.pop("PAPERFLIP_DASHBOARD_SMOKE", None)
    notebook = nbformat.read(SOURCE, as_version=4)
    client = NotebookClient(notebook, timeout=60, interrupt_on_timeout=True, kernel_name="python3")
    client.execute(cwd=str(ROOT))
    DESTINATION.mkdir(parents=True, exist_ok=True)
    nbformat.write(notebook, DESTINATION / f"{slug}.ipynb")
    exporter = HTMLExporter()
    exporter.exclude_input = True
    exporter.exclude_input_prompt = True
    exporter.exclude_output_prompt = True
    body, _ = exporter.from_notebook_node(notebook)
    # nbconvert's default CDN scripts do not load from a file:// preview in
    # this VM. Ship the compatible renderer locally so copied HTML previews
    # work without Python or a Jupyter server.
    assets = DESTINATION / "assets"
    assets.mkdir(parents=True, exist_ok=True)
    for filename in ("embed-amd.js", "require.js"):
        shutil.copy2(WIDGET_ASSETS / filename, assets / filename)
    body = body.replace(
        "https://cdnjs.cloudflare.com/ajax/libs/require.js/2.1.10/require.min.js",
        "assets/require.js",
    ).replace(
        "https://unpkg.com/@jupyter-widgets/html-manager@*/dist/embed-amd.js",
        "assets/embed-amd.js",
    )
    (DESTINATION / f"{slug}.html").write_text(body)


def main() -> None:
    for tab, slug in ((0, "01_tiny_teaching_view"), (1, "02_network_view"),
                      (2, "03_quantum_evidence_view")):
        render(tab, slug)
    print(DESTINATION)


if __name__ == "__main__":
    main()
