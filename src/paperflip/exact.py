"""Exact ferromagnetic ground states using s-t min-cut, with extremal degeneracy states."""
from __future__ import annotations

from dataclasses import dataclass
import itertools
import networkx as nx
import numpy as np
from .model import IsingModel


@dataclass
class ExactResult:
    energy: int
    paper_state: np.ndarray  # least digital minimum (source reachability)
    digital_state: np.ndarray  # most digital minimum (not sink-co-reachable)
    degenerate: np.ndarray


def _graph(model: IsingModel, year: int) -> nx.DiGraph:
    """Cut source side is s=+1. Capacity relation E=cut-sum(J)-sum(abs(b))."""
    g = nx.DiGraph()
    g.add_nodes_from(range(model.n))
    g.add_node("source")
    g.add_node("sink")
    b = model.fields(year)
    for i in range(model.n):
        if b[i] > 0:
            g.add_edge("source", i, capacity=int(2 * b[i]))
        elif b[i] < 0:
            g.add_edge(i, "sink", capacity=int(-2 * b[i]))
    for i in range(model.n):
        for j in range(i + 1, model.n):
            if model.ties[i, j]:
                # A directed arc with capacity 2J represents one undirected cut edge 2J.
                g.add_edge(i, j, capacity=int(2 * model.ties[i, j]))
                g.add_edge(j, i, capacity=int(2 * model.ties[i, j]))
    return g


def mincut(model: IsingModel, year: int) -> ExactResult:
    g = _graph(model, year)
    cut, flow = nx.maximum_flow(g, "source", "sink", flow_func=nx.algorithms.flow.preflow_push)
    # Build the residual ourselves from capacities-flow. For every ordered pair, add
    # forward residual and reverse residual. This makes the extremal min-cuts explicit.
    residual = nx.DiGraph()
    residual.add_nodes_from(g.nodes)
    for u, v, d in g.edges(data=True):
        f = flow[u][v]
        if d["capacity"] - f > 0:
            residual.add_edge(u, v)
        if f > 0:
            residual.add_edge(v, u)
    min_source = nx.descendants(residual, "source") | {"source"}
    can_reach_sink = nx.ancestors(residual, "sink") | {"sink"}
    paper = np.array([1 if i in min_source else -1 for i in range(model.n)], dtype=np.int8)
    digital = np.array([1 if i not in can_reach_sink else -1 for i in range(model.n)], dtype=np.int8)
    # Use direct energy, not only the cut identity, as a guard against graph construction mistakes.
    e = model.energy(paper, year)
    assert e == model.energy(digital, year)
    return ExactResult(e, paper, digital, paper != digital)


def enumerate_ground(model: IsingModel, year: int) -> tuple[int, np.ndarray, np.ndarray]:
    """Slow validator for n <= 20; not part of the normal sweep."""
    if model.n > 20:
        raise ValueError("enumeration is capped at 20 nodes")
    states = np.asarray(list(itertools.product((-1, 1), repeat=model.n)), dtype=np.int8)
    energies = np.array([model.energy(s, year) for s in states], dtype=np.int64)
    gs = states[energies == energies.min()]
    return int(energies.min()), gs.min(axis=0), gs.max(axis=0)


def flip_intervals(results: dict[int, ExactResult]) -> dict[str, np.ndarray]:
    years = np.array(sorted(results))
    n = len(next(iter(results.values())).paper_state)
    early = np.full(n, -1, dtype=int)
    late = np.full(n, -1, dtype=int)
    for i in range(n):
        for y in years:
            if early[i] < 0 and results[y].digital_state[i] == 1:
                early[i] = y
            if late[i] < 0 and results[y].paper_state[i] == 1:
                late[i] = y
    return {"early": early, "late": late}
