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


def test_generated_notebook_uses_pinned_digital_bit_zero_artifacts():
    notebook = nbformat.read(ROOT / "notebooks" / "paperflip_dashboard.ipynb", as_version=4)
    source = "\n".join(cell.source for cell in notebook.cells if cell.cell_type == "code")
    assert 'DASHBOARD_SOURCE_VERSION = "pinned-artifacts-v1-2026-11-07"' in source
    assert "dqa_2033_aer_8000_seed20264139.json" in source
    assert "fixed saved local CPU/Qiskit Aer DQA artifact" in source
    assert "Fixed saved QAOA yearly probability baseline" in source
    assert "P(bit 0 = digital)" in source
    assert "not a measured-shot or empirical adoption probability" in source
    assert "run_local_dqa_and_persist" not in source
    assert "compute_qaoa_year_sweep" not in source


def test_pinned_dashboard_artifacts_exist_and_are_not_rebuilt_by_notebook():
    source = (ROOT / "scripts" / "build_dashboard_notebook.py").read_text()
    assert (ROOT / "artifacts" / "dashboard_pins" / "dqa_2033_aer_8000_seed20264139.json").exists()
    assert (ROOT / "artifacts" / "dashboard_pins" / "dqa_2033_aer_8000_seed20264139.png").exists()
    assert (ROOT / "artifacts" / "qaoa_yearly_probability_pacific_nw.json").exists()
    assert "This notebook will not regenerate it." in source


def test_p1_qaoa_walkthrough_is_cached_stage_display_not_a_new_solver_call():
    source = (ROOT / "scripts" / "build_dashboard_notebook.py").read_text()
    assert 'title("Interactive p=1 QAOA circuit and statevector walk-through")' in source
    assert "def draw_p1_circuit(highlight):" in source
    assert "p=1: exactly one cost block and one mixer block" in source
    assert "def render_qaoa_walkthrough(change=None):" in source
    assert "lookup_region_view(compute=False)" in source
    assert "walkthrough_stage.observe(render_qaoa_walkthrough" in source
    assert "C{index+1:02d}" in source
    assert "included={mass['included_mass']:.3e}" in source
