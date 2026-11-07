"""Regression checks for generated notebook-only callback dependencies."""
from pathlib import Path

import nbformat


ROOT = Path(__file__).resolve().parents[1]


def test_full_network_render_has_patch_import_and_binary_legend():
    notebook = nbformat.read(ROOT / "notebooks" / "paperflip_dashboard.ipynb", as_version=4)
    source = "\n".join(cell.source for cell in notebook.cells if cell.cell_type == "code")
    assert "from matplotlib.patches import Patch" in source
    assert 'paper_red, digital_blue = "#b65b5b", "#5b7fa3"' in source
    assert "ListedColormap([paper_red, digital_blue])" in source
    assert 'Patch(facecolor=paper_red, label="paper (s=-1)")' in source
    assert 'Patch(facecolor=digital_blue, label="digital (s=+1)")' in source


def test_smoke_rejects_output_captured_callback_tracebacks():
    source = (ROOT / "scripts" / "build_dashboard_notebook.py").read_text()
    assert "def assert_output_clean(label, output):" in source
    assert 'item.get("output_type") == "error"' in source
    assert '"Traceback" in item.get("text", "")' in source
    assert 'render_full()  # direct Section 2 first-render/legend regression' in source


def test_generated_notebook_uses_digital_bit_zero_yearly_heatmap():
    notebook = nbformat.read(ROOT / "notebooks" / "paperflip_dashboard.ipynb", as_version=4)
    source = "\n".join(cell.source for cell in notebook.cells if cell.cell_type == "code")
    assert "Compute yearly probability heatmap (local CPU)" in source
    assert "P(bit_i=0): **digital**" in source
    assert "QAOA digital probability by year — P(bit 0), not bit 1" in source
    assert "exact degeneracy / flip-uncertainty range" in source
    assert "never digital through 2040" in source
