import numpy as np

from paperflip.model import IsingModel, load_model
from paperflip.region_views import compute_region_view, has_inter_region_edges, nested_regions, standard_qaoa_circuit
from qiskit.quantum_info import Statevector


def test_nested_regions_are_reproducible_same20_and_independent():
    base, _, _ = load_model("configs/one_region.yaml")
    first = nested_regions(base, seed=9, count=5)
    second = nested_regions(base, seed=9, count=5)
    assert [scenario.name for scenario in first[:2]] == [scenario.name for scenario in nested_regions(base, seed=9, count=2)]
    for left, right in zip(first, second):
        assert left.model.names == base.names and left.model.n == 20
        assert np.array_equal(left.model.ties, base.ties)
        assert np.array_equal(left.model.resistance, right.model.resistance)
    assert not has_inter_region_edges(first)


def test_three_stage_view_preserves_cost_probabilities_and_normalization():
    model = IsingModel(("a", "b", "c"), np.array([6, 7, 8]),
                       np.array([[0, 2, 0], [2, 0, 3], [0, 3, 0]]), 4, 10)
    scenario = nested_regions(model, seed=3, count=1)[0]
    view = compute_region_view(scenario, 2027, gamma_grid=(.2,), beta_grid=(.4,), top_k=8)
    assert view["n_qubits"] == 3
    assert all(abs(stage["normalization"] - 1) < 1e-12 for stage in view["stages"].values())
    for record in view["fixed_configurations"]:
        assert abs(record["initial_probability"] - record["cost_only_probability"]) < 1e-12
        assert record["cost_only_phase_relative_radians"] is None or -np.pi <= record["cost_only_phase_relative_radians"] < np.pi
    assert abs(view["stages"]["post_mixer"]["included_mass"] + view["stages"]["post_mixer"]["omitted_mass"] - 1) < 1e-12


def test_standard_qaoa_has_plus_x_mixer_rotation():
    model = IsingModel(("a",), np.array([4]), np.zeros((1, 1), dtype=int), 1, 10)
    circuit = standard_qaoa_circuit(model, 2026, gamma=.2, beta=.3)
    assert any(instruction.operation.name == "rx" and np.isclose(float(instruction.operation.params[0]), .6)
               for instruction in circuit.data)
