import numpy as np

from paperflip.model import IsingModel
from paperflip.qaoa_year_sweep import (
    compute_qaoa_year_sweep, latest_matching_qaoa_year_sweep,
    persist_qaoa_year_sweep, year_sweep_matches,
)


def test_year_sweep_reports_digital_bit_zero_marginals_and_matching_identity(tmp_path):
    # At zero angles the |+> state has exactly P(bit_i=0)=1/2. This directly
    # checks the dashboard convention (0=digital), not the inverted screenshot
    # convention of "bit 1 adoption".
    model = IsingModel(("a", "b"), np.array([4, 7]), np.array([[0, 2], [2, 0]]), 3, 10)
    result = compute_qaoa_year_sweep(
        model, [2026, 2027], region="test", region_seed=9,
        gamma_grid=(0.0,), beta_grid=(0.0,),
    )
    assert result["bit_convention"] == "digital=x_i=0=s_i=+1; each heatmap cell is P(bit_i=0)"
    assert all(np.isclose(row["statevector_probability_sum"], 1) for row in result["rows"])
    assert all(np.allclose(row["digital_probability_by_industry"], [.5, .5]) for row in result["rows"])
    assert year_sweep_matches(
        result, model, [2026, 2027], region="test", region_seed=9,
        gamma_grid=(0.0,), beta_grid=(0.0,),
    )
    assert not year_sweep_matches(
        result, model, [2026], region="test", region_seed=9,
        gamma_grid=(0.0,), beta_grid=(0.0,),
    )
    persist_qaoa_year_sweep(result, tmp_path)
    cached = latest_matching_qaoa_year_sweep(
        tmp_path, model, [2026, 2027], region="test", region_seed=9,
        gamma_grid=(0.0,), beta_grid=(0.0,),
    )
    assert cached is not None and cached[0]["model_fingerprint"] == result["model_fingerprint"]


def test_year_sweep_exact_markers_include_left_and_right_censoring_and_degeneracy():
    # Independent zero-field nodes have legitimate degenerate ground states:
    # their exact tipping interval spans the entire observation window.
    degenerate = IsingModel(("free",), np.array([0]), np.zeros((1, 1), dtype=int), 0, 10)
    marker = compute_qaoa_year_sweep(
        degenerate, [2026, 2027], region="test", region_seed=1,
        gamma_grid=(0.0,), beta_grid=(0.0,),
    )["exact_flip_markers"][0]
    assert marker["already_digital_at_window_start"]
    assert marker["has_exact_degeneracy"]
    assert marker["degenerate_years"] == [2026, 2027]

    never = IsingModel(("late",), np.array([100]), np.zeros((1, 1), dtype=int), 1, 10)
    marker = compute_qaoa_year_sweep(
        never, [2026, 2027], region="test", region_seed=1,
        gamma_grid=(0.0,), beta_grid=(0.0,),
    )["exact_flip_markers"][0]
    assert marker["never_digital_through_window"]
    assert marker["earliest_digital_year"] is None
