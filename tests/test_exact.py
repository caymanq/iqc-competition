import numpy as np
from paperflip.model import IsingModel, load_model
from paperflip.exact import mincut, enumerate_ground, flip_intervals
from paperflip.metrics import flip_comparison


def tiny() -> IsingModel:
    return IsingModel(("a", "b", "c"), np.array([5, 10, 15]), np.array([[0, 3, 0], [3, 0, 2], [0, 2, 0]]), 5, 100)


def test_mincut_matches_enumeration_and_extremes():
    model = tiny()
    for year in range(2026, 2032):
        e, low, high = enumerate_ground(model, year)
        result = mincut(model, year)
        assert result.energy == e
        assert np.array_equal(result.paper_state, low)
        assert np.array_equal(result.digital_state, high)


def test_random_ferromagnetic_extremal_mincuts():
    rng = np.random.default_rng(42)
    for _ in range(40):
        n = 6
        ties = rng.integers(0, 5, size=(n, n))
        ties = np.triu(ties, 1)
        ties = ties + ties.T
        model = IsingModel(tuple(map(str, range(n))), rng.integers(0, 20, n), ties, 3, 100)
        for year in (2026, 2029, 2033):
            e, low, high = enumerate_ground(model, year)
            actual = mincut(model, year)
            assert (actual.energy == e and np.array_equal(actual.paper_state, low)
                    and np.array_equal(actual.digital_state, high))


def test_qubo_energy_consistency():
    model = tiny()
    q, const = model.qubo(2029)
    for bits in range(8):
        x = np.array([(bits >> i) & 1 for i in range(3)])
        s = 2 * x - 1
        assert model.energy(s, 2029) == int(np.dot(x, q @ x) + const)


def test_zero_field_is_degenerate_not_float_flip():
    # r=0.35 and 0.07/year means exactly zero field in 2031.
    model = IsingModel(("hospitality",), np.array([3500]), np.zeros((1, 1), dtype=int), 700, 10000)
    results = {y: mincut(model, y) for y in range(2026, 2033)}
    spans = flip_intervals(results)
    assert spans["early"][0] == 2031
    assert spans["late"][0] == 2032


def test_censored_metric_has_no_numeric_error():
    records = flip_comparison(np.array([-1, 2029]), np.array([-1, 2030]), np.array([-1, 2031]))
    assert records[0]["category"] == "MATCH_CENSORED"
    assert records[0]["year_error"] is None
    assert records[1]["category"] == "EARLY"


def test_aer_circuit_returns_a_raw_measured_state():
    from paperflip.solvers import dqa_aer
    model = tiny()
    result = dqa_aer(model, 2029, seed=3, shots=64, p=2, total_time=1)
    assert set(result.state) <= {-1, 1}
    assert result.energy == model.energy(result.state, 2029)
    assert result.meta["modal_count"] >= 1


def test_quantum_spin_decode_and_one_qubit_annealing_direction():
    # Challenge convention: Z=+1 / |0> is digital, Z=-1 / |1> is paper.
    from paperflip.solvers import _decode, dqa_aer
    assert np.array_equal(_decode("0", 1), np.array([1]))
    assert np.array_equal(_decode("1", 1), np.array([-1]))
    model = IsingModel(("x",), np.array([100]), np.zeros((1, 1), dtype=int), 1, 100)
    # At 2026 b=-r, H_problem=+Z; its ground state is |1> / s=-1.
    result = dqa_aer(model, 2026, seed=1, shots=512, p=40, total_time=20)
    assert result.state[0] == -1
    assert result.energy == -100


def test_qiskit_and_independent_numpy_dqa_statevectors_agree():
    from qiskit.quantum_info import Statevector
    from paperflip.solvers import dqa_circuit, dqa_statevector_numpy
    model = tiny()
    qiskit = Statevector.from_instruction(dqa_circuit(model, 2029, p=5, total_time=2.5)).data
    numpy_state = dqa_statevector_numpy(model, 2029, p=5, total_time=2.5)
    # Global phase is irrelevant; align to the first nonzero amplitude.
    phase = qiskit[np.argmax(np.abs(qiskit))] / numpy_state[np.argmax(np.abs(qiskit))]
    assert np.allclose(qiskit, phase * numpy_state, atol=1e-10)


def test_quantum_ferromagnetic_tie_has_aligned_ground_probability():
    from qiskit.quantum_info import Statevector
    from paperflip.solvers import dqa_circuit
    # At b=0, H_problem=-J Z0 Z1: |00> and |11> are its (aligned) ground states.
    model = IsingModel(("a", "b"), np.zeros(2, dtype=int),
                       np.array([[0, 100], [100, 0]]), 1, 100)
    vec = Statevector.from_instruction(dqa_circuit(model, 2026, p=80, total_time=40)).data
    assert abs(vec[0]) ** 2 + abs(vec[3]) ** 2 > 0.99
