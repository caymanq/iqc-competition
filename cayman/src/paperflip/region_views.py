"""Independent 20-node regional QAOA teaching views.

This module intentionally never builds a 40- or 100-node quantum circuit.
Each region is an independent, same-topology 20-node scenario with no
cross-region edges.  The "multi-region" view compares separate simulations.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import time
from typing import Any
import numpy as np
from qiskit import QuantumCircuit
from qiskit.quantum_info import Statevector

from .exact import mincut
from .model import IsingModel


REGION_NAMES = ("Pacific NW", "California", "Mountain West", "Southwest", "Texas")


@dataclass(frozen=True)
class RegionScenario:
    name: str
    model: IsingModel
    regional_shift_int: int
    noise_int: tuple[int, ...]


def nested_regions(base: IsingModel, seed: int = 20261106, count: int = 5) -> tuple[RegionScenario, ...]:
    """Stable, nested synthetic scenarios: N=1 is a prefix of N=2 and N=5."""
    if not 1 <= count <= len(REGION_NAMES):
        raise ValueError(f"count must be between 1 and {len(REGION_NAMES)}")
    rng = np.random.default_rng(seed)
    shifts = np.rint(np.linspace(-0.12, 0.12, len(REGION_NAMES)) * base.unit).astype(np.int64)
    scenarios = []
    for index, name in enumerate(REGION_NAMES):
        noise = np.rint(rng.normal(0, 0.02 * base.unit, base.n)).astype(np.int64)
        regional = IsingModel(
            base.names,
            base.resistance + shifts[index] + noise,
            base.ties.copy(),  # same 20-industry topology; explicitly no cross-region edges
            base.pressure_step,
            base.unit,
        )
        scenarios.append(RegionScenario(name, regional, int(shifts[index]), tuple(int(v) for v in noise)))
    return tuple(scenarios[:count])


def has_inter_region_edges(scenarios: tuple[RegionScenario, ...]) -> bool:
    """Separate models hold no inter-region graph at all; retained for explicit tests/UI."""
    return False


def scenario_key(scenario: RegionScenario, year: int, gamma_grid: tuple[float, ...],
                 beta_grid: tuple[float, ...]) -> str:
    payload = {
        "name": scenario.name, "year": year, "resistance": scenario.model.resistance.tolist(),
        "ties": scenario.model.ties.tolist(), "gamma": gamma_grid, "beta": beta_grid,
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()[:20]


def _scale(model: IsingModel, year: int) -> float:
    return float(max(1, np.max(np.abs(model.fields(year))), np.max(np.sum(model.ties, axis=1))))


def _energy_vector(model: IsingModel, year: int) -> np.ndarray:
    """Energies in Qiskit little-endian computational-basis index order."""
    indices = np.arange(1 << model.n, dtype=np.uint32)
    energies = np.zeros(1 << model.n, dtype=np.int64)
    fields = model.fields(year)
    spins = []
    for i in range(model.n):
        si = (1 - 2 * ((indices >> i) & 1)).astype(np.int8)  # 0 -> +1 digital
        spins.append(si)
        energies -= fields[i] * si
    for i in range(model.n):
        for j in range(i + 1, model.n):
            if model.ties[i, j]:
                energies -= model.ties[i, j] * spins[i] * spins[j]
    return energies


def standard_qaoa_circuit(model: IsingModel, year: int, gamma: float, beta: float,
                          include_mixer: bool = True) -> QuantumCircuit:
    """p=1 standard QAOA: H_C then H_M=+sum X, from |+>."""
    scale, h = _scale(model, year), model.fields(year)
    circuit = QuantumCircuit(model.n)
    circuit.h(range(model.n))
    for i in range(model.n):
        circuit.rz(-2 * gamma * float(h[i]) / scale, i)
    for i in range(model.n):
        for j in range(i + 1, model.n):
            if model.ties[i, j]:
                circuit.rzz(-2 * gamma * float(model.ties[i, j]) / scale, i, j)
    if include_mixer:
        for i in range(model.n):
            circuit.rx(2 * beta, i)  # +sum X mixer, deliberately unlike DQA driver
    return circuit


def _phase_relative_at(amplitudes: np.ndarray, index: int, reference_index: int = 0,
                       epsilon: float = 1e-12) -> float | None:
    reference = np.angle(amplitudes[reference_index]) if abs(amplitudes[reference_index]) > epsilon else 0.0
    if abs(amplitudes[index]) < epsilon:
        return None
    value = (np.angle(amplitudes[index]) - reference + np.pi) % (2 * np.pi) - np.pi
    return float(value)


def _bits(index: int, n: int) -> str:
    """Displayed QASM/count order c[n-1]...c[0]."""
    return format(index, f"0{n}b")


def _sector_marginals(probabilities: np.ndarray, n: int) -> list[float]:
    indices = np.arange(1 << n, dtype=np.uint32)
    return [float(np.sum(probabilities[((indices >> i) & 1) == 0])) for i in range(n)]


def _fixed_configurations(stage_probabilities: dict[str, np.ndarray], exact_state: np.ndarray,
                          k: int = 12) -> list[int]:
    chosen = {int(sum((1 if spin == -1 else 0) << i for i, spin in enumerate(exact_state)))}
    for probabilities in stage_probabilities.values():
        chosen.update(np.argpartition(probabilities, -k)[-k:].tolist())
    return sorted(chosen)


def compute_region_view(scenario: RegionScenario, year: int,
                        gamma_grid: tuple[float, ...] = (0.2, 0.6, 1.0),
                        beta_grid: tuple[float, ...] = (0.2, 0.5, 0.8),
                        top_k: int = 12) -> dict[str, Any]:
    """Bounded p=1 objective optimization and three pedagogical circuit stages."""
    started = time.perf_counter()
    model = scenario.model
    energies = _energy_vector(model, year)
    exact = mincut(model, year)
    best: tuple[float, float, float] | None = None
    # This optimizes expected energy, never forces the exact mode or modifies samples.
    for gamma in gamma_grid:
        for beta in beta_grid:
            vector = Statevector.from_instruction(standard_qaoa_circuit(model, year, gamma, beta)).data
            expected = float(np.dot(np.abs(vector) ** 2, energies))
            candidate = (expected, gamma, beta)
            if best is None or candidate < best:
                best = candidate
    assert best is not None
    expected, gamma, beta = best
    initial = np.ones(1 << model.n, dtype=np.complex128) / np.sqrt(1 << model.n)
    cost = Statevector.from_instruction(standard_qaoa_circuit(model, year, gamma, beta, include_mixer=False)).data
    mixed = Statevector.from_instruction(standard_qaoa_circuit(model, year, gamma, beta)).data
    probabilities = {"initial": np.abs(initial) ** 2, "cost_only": np.abs(cost) ** 2, "post_mixer": np.abs(mixed) ** 2}
    fixed = _fixed_configurations(probabilities, exact.paper_state, top_k)
    records = []
    for index in fixed:
        spin = np.array([1 if ((index >> i) & 1) == 0 else -1 for i in range(model.n)], dtype=np.int8)
        records.append({
            "bitstring_c_n_minus_1_to_c_0": _bits(index, model.n),
            "energy_model_units": float(energies[index] / model.unit),
            "is_exact_minimum": bool(energies[index] == exact.energy),
            "initial_probability": float(probabilities["initial"][index]),
            "cost_only_probability": float(probabilities["cost_only"][index]),
            "post_mixer_probability": float(probabilities["post_mixer"][index]),
            "cost_only_phase_relative_radians": _phase_relative_at(cost, index),
        })
    stages = {}
    for name, values in probabilities.items():
        stages[name] = {
            "included_mass": float(sum(values[index] for index in fixed)),
            "omitted_mass": float(1 - sum(values[index] for index in fixed)),
            "sector_digital_marginals": _sector_marginals(values, model.n),
            "normalization": float(values.sum()),
        }
    return {
        "status": "LOCAL_CPU_SIMULATOR_CACHE_NOT_QBRAID_NOT_HARDWARE",
        "scenario_key": scenario_key(scenario, year, gamma_grid, beta_grid),
        "region": scenario.name,
        "year": year,
        "n_qubits": model.n,
        "assumption": "Independent same-20-node region; no cross-region ties or quantum circuit.",
        "regional_shift_model_units": scenario.regional_shift_int / model.unit,
        "noise_model_units": [value / model.unit for value in scenario.noise_int],
        "optimization": {
            "objective": "minimize p=1 standard-QAOA expected Ising energy over bounded 3×3 grid",
            "gamma_grid": gamma_grid, "beta_grid": beta_grid,
            "gamma": gamma, "beta": beta,
            "expected_energy_model_units": expected / model.unit,
        },
        "exact": {
            "energy_model_units": exact.energy / model.unit,
            "paper_tie_ground_state": [int(value) for value in exact.paper_state],
            "digital_extreme_ground_state": [int(value) for value in exact.digital_state],
        },
        "fixed_configurations": records,
        "stages": stages,
        "exact_optimum_probability_post_mixer": float(sum(
            probabilities["post_mixer"][index] for index, value in enumerate(energies) if value == exact.energy)),
        "cpu_seconds": time.perf_counter() - started,
    }
