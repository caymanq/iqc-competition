import numpy as np

from paperflip.model import IsingModel, load_model
from paperflip.qaoa_landscape import compute_qaoa_landscape, landscape_matches, persist_landscape


def test_landscape_uses_actual_spacings_for_finite_difference_gradient(tmp_path):
    model = IsingModel(("a", "b"), np.array([4, 7]), np.array([[0, 2], [2, 0]]), 3, 10)
    gamma, beta = np.array([0.1, 0.4, 1.0]), np.array([0.2, 0.8, 1.7])
    view = compute_qaoa_landscape(model, 2027, gamma, beta)
    energy = np.asarray(view["expected_energy_model_units"])
    gradient = np.asarray(view["gradient_norm_model_units_per_radian"])
    # Independent second-order interior finite differences on the uneven grids.
    # This is the same nonuniform formula used by numpy.gradient, rather than
    # silently treating the actual angle samples as uniformly spaced.
    def nonuniform_middle(f0, f1, f2, x0, x1, x2):
        left, right = x1 - x0, x2 - x1
        return (-right * f0 / (left * (left + right))
                + (right - left) * f1 / (left * right)
                + left * f2 / (right * (left + right)))
    manual_gamma = nonuniform_middle(energy[1, 0], energy[1, 1], energy[1, 2], *gamma)
    manual_beta = nonuniform_middle(energy[0, 1], energy[1, 1], energy[2, 1], *beta)
    assert np.isclose(gradient[1, 1], np.hypot(manual_gamma, manual_beta))
    assert view["exact_minimum_model_units"] == model.energy(np.array([-1, -1]), 2027) / model.unit
    assert landscape_matches(view, model, 2027, gamma, beta)
    path = persist_landscape(view, tmp_path)
    assert path.exists() and not landscape_matches(view, model, 2026, gamma, beta)


def test_bounded_representative_20_node_landscape():
    model, _, _ = load_model("configs/one_region.yaml")
    view = compute_qaoa_landscape(model, 2031, np.array([0.2, 0.8]), np.array([0.2, 0.7]))
    energy, gradient = np.asarray(view["expected_energy_model_units"]), np.asarray(view["gradient_norm_model_units_per_radian"])
    assert energy.shape == gradient.shape == (2, 2)
    assert np.isfinite(energy).all() and np.isfinite(gradient).all()
