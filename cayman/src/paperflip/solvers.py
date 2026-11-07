"""Classical SA and actual Qiskit/Aer circuit solvers. No classical polishing of circuit samples."""
from __future__ import annotations
from dataclasses import dataclass
import time
import numpy as np
from .model import IsingModel


@dataclass
class SolveResult:
    state: np.ndarray
    energy: int
    seconds: float
    method: str
    meta: dict
    samples: dict[str, int] | None = None


def simulated_annealing(model: IsingModel, year: int, seed: int, sweeps: int = 600, restarts: int = 12) -> SolveResult:
    start = time.perf_counter()
    rng = np.random.default_rng(seed)
    b, j = model.fields(year), model.ties
    best, best_e = None, np.iinfo(np.int64).max
    # Dimensionless beta calibrated to the integer energy scale.
    scale = max(1, int(np.max(np.abs(b)) + np.max(np.sum(j, axis=1))))
    for _ in range(restarts):
        s = rng.choice(np.array([-1, 1], dtype=np.int8), model.n)
        for beta in np.geomspace(0.01 / scale, 12.0 / scale, sweeps):
            for i in rng.permutation(model.n):
                local = int(b[i] + np.dot(j[i], s))
                delta = 2 * int(s[i]) * local
                if delta <= 0 or rng.random() < np.exp(-beta * delta):
                    s[i] *= -1
        e = model.energy(s, year)
        if e < best_e:
            best, best_e = s.copy(), e
    return SolveResult(best, int(best_e), time.perf_counter() - start, "sa",
                       {"seed": seed, "sweeps": sweeps, "restarts": restarts})


def _circuit(model: IsingModel, year: int, p: int, gamma: float, beta: float):
    from qiskit import QuantumCircuit
    b, j = model.fields(year), model.ties
    scale = float(max(1, np.max(np.abs(b)) + np.max(np.sum(j, axis=1))))
    q = QuantumCircuit(model.n)
    q.h(range(model.n))
    for _ in range(p):
        for i in range(model.n):
            q.rz(-2 * gamma * float(b[i]) / scale, i)
        for i in range(model.n):
            for k in range(i + 1, model.n):
                if j[i, k]:
                    q.rzz(-2 * gamma * float(j[i, k]) / scale, i, k)
        for i in range(model.n):
            q.rx(-2 * beta, i)
    return q


def dqa_circuit(model: IsingModel, year: int, p: int, total_time: float):
    """Unmeasured circuit for a linear H=(1-t)H_X+tH_problem schedule."""
    from qiskit import QuantumCircuit
    b, j = model.fields(year), model.ties
    scale = float(max(1, np.max(np.abs(b)) + np.max(np.sum(j, axis=1))))
    q = QuantumCircuit(model.n)
    q.h(range(model.n))  # ground state of H_X=-sum X
    dt = total_time / p
    for layer in range(1, p + 1):
        frac = layer / p
        for i in range(model.n):
            q.rz(-2 * dt * frac * float(b[i]) / scale, i)
        for i in range(model.n):
            for k in range(i + 1, model.n):
                if j[i, k]:
                    q.rzz(-2 * dt * frac * float(j[i, k]) / scale, i, k)
        for i in range(model.n):
            q.rx(-2 * dt * (1 - frac), i)
    return q


def dqa_statevector_numpy(model: IsingModel, year: int, p: int, total_time: float) -> np.ndarray:
    """Independent numpy implementation of the DQA circuit for convention tests."""
    n = model.n
    if n > 12:
        raise ValueError("numpy verification intentionally capped at 12 qubits")
    b, j = model.fields(year), model.ties
    scale = float(max(1, np.max(np.abs(b)) + np.max(np.sum(j, axis=1))))
    size = 1 << n
    indices = np.arange(size, dtype=np.uint32)
    spins = 1 - 2 * ((indices[:, None] >> np.arange(n)) & 1)  # |0> -> +1
    state = np.ones(size, dtype=np.complex128) / np.sqrt(size)
    dt = total_time / p
    for layer in range(1, p + 1):
        frac = layer / p
        phase_energy = np.einsum("bi,ij,bj->b", spins, np.triu(j, 1), spins) + spins @ b
        state *= np.exp(1j * dt * frac * phase_energy / scale)
        theta = -2 * dt * (1 - frac)
        c, off = np.cos(theta / 2), -1j * np.sin(theta / 2)
        for qubit in range(n):
            stride = 1 << qubit
            for first in range(0, size, 2 * stride):
                a = slice(first, first + stride)
                z = slice(first + stride, first + 2 * stride)
                old0, old1 = state[a].copy(), state[z].copy()
                state[a], state[z] = c * old0 + off * old1, off * old0 + c * old1
    return state


def _decode(bitstring: str, n: int) -> np.ndarray:
    """Map Qiskit's displayed bits to Ising spins.

    The circuit Hamiltonian uses Z, whose |0> eigenvalue is +1 (digital), and
    |1> eigenvalue is -1 (paper). Qiskit's displayed string is big-endian.
    This is deliberately the inverse of a QUBO x bit convention.
    """
    return np.array([1 if x == "0" else -1 for x in bitstring[::-1]], dtype=np.int8)


def _sample_summary(model: IsingModel, year: int, counts: dict[str, int]) -> tuple[np.ndarray, int, int, str]:
    """Return modal state plus best *measured* sample; no local optimisation."""
    bit, count = max(counts.items(), key=lambda item: item[1])
    modal = _decode(bit, model.n)
    best_bit, best_energy = min(
        ((candidate, model.energy(_decode(candidate, model.n), year)) for candidate in counts),
        key=lambda item: item[1],
    )
    return modal, count, int(best_energy), best_bit


def dqa_aer(model: IsingModel, year: int, seed: int, shots: int = 2048, p: int = 4,
            total_time: float = 5.0) -> SolveResult:
    """Digitized transverse-field quantum annealing, sampled directly from Aer."""
    from qiskit_aer import AerSimulator
    start = time.perf_counter()
    q = dqa_circuit(model, year, p, total_time)
    q.measure_all()
    counts = AerSimulator(seed_simulator=seed).run(q, shots=shots).result().get_counts()
    # Raw measured samples only: choose its modal state, never a separately polished state.
    state, count, best_energy, best_bit = _sample_summary(model, year, counts)
    return SolveResult(state, model.energy(state, year), time.perf_counter() - start, "dqa_aer",
                       {"seed": seed, "shots": shots, "p": p, "total_time": total_time,
                        "modal_count": count, "distinct_states": len(counts), "depth": q.depth(),
                        "two_qubit_gates": sum(1 for ins in q.data if ins.operation.name == "rzz"),
                        "best_observed_energy": best_energy, "best_observed_bitstring": best_bit},
                       counts)


def qaoa_aer(model: IsingModel, year: int, seed: int, shots: int = 2048) -> SolveResult:
    """p=1 QAOA, with a small deterministic expectation-value grid search then raw sampling."""
    from qiskit.quantum_info import Statevector
    from qiskit_aer import AerSimulator
    start = time.perf_counter()
    grid = np.linspace(0.15, 1.45, 4)
    best = (float("inf"), 0.0, 0.0)
    # The grid only chooses circuit parameters; reported state is still an unmodified raw sample.
    for gamma in grid:
        for beta in grid:
            vec = Statevector.from_instruction(_circuit(model, year, 1, float(gamma), float(beta))).data
            indices = np.arange(1 << model.n, dtype=np.uint32)
            # Index bit i is qubit i, exactly matching Qiskit Statevector ordering.
            spins = 1 - 2 * ((indices[:, None] >> np.arange(model.n)) & 1)
            # Qiskit's computational |0> has Z=+1, matching s=+1.
            # Chunk-free at n=20 (~160MB temporary); intended for 20q only.
            energies = -np.einsum("bi,ij,bj->b", spins, np.triu(model.ties, 1), spins) - spins @ model.fields(year)
            exp = float(np.dot(np.abs(vec) ** 2, energies))
            if exp < best[0]:
                best = (exp, float(gamma), float(beta))
    _, gamma, beta = best
    q = _circuit(model, year, 1, gamma, beta)
    q.measure_all()
    counts = AerSimulator(seed_simulator=seed).run(q, shots=shots).result().get_counts()
    state, count, best_energy, best_bit = _sample_summary(model, year, counts)
    return SolveResult(state, model.energy(state, year), time.perf_counter() - start, "qaoa_aer",
                       {"seed": seed, "shots": shots, "p": 1, "gamma": gamma, "beta": beta,
                        "modal_count": count, "distinct_states": len(counts), "depth": q.depth(),
                        "two_qubit_gates": sum(1 for ins in q.data if ins.operation.name == "rzz"),
                        "best_observed_energy": best_energy, "best_observed_bitstring": best_bit},
                       counts)
