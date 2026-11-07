#!/usr/bin/env python3
"""Exact min-cut classical benchmark for Vasion IQC 2026 one-region model.
Usage: pip install networkx && python paper_phase_transition_baseline.py
Reads paper_phase_transition_20_industries.json from same directory.
"""
import json
from pathlib import Path
import networkx as nx

MODEL = json.loads((Path(__file__).with_name("paper_phase_transition_20_industries.json")).read_text())
NODES = MODEL["industries"]
EDGES = MODEL["edges"]
NAME = {node["id"]: node["name"] for node in NODES}

def energy(bits, year):
    """bits[i] = 0 paper or 1 digital."""
    A = 0.07*(year-2026)
    s = [2*int(b)-1 for b in bits]
    return (-sum(edge["J"]*s[edge["i"]]*s[edge["j"]] for edge in EDGES)
            -sum((A-node["resistance"])*s[node["id"]] for node in NODES))

def exact_ground_state(year):
    """Ferromagnetic Ising min via source-sink min cut.

    Node on source side = digital; on sink side = paper.
    Minimizes E up to an additive constant, with J >= 0.
    """
    A = 0.07*(year-2026)
    g = nx.DiGraph()
    source, sink = "source", "sink"
    g.add_nodes_from([source,sink]+[node["id"] for node in NODES])
    for node in NODES:
        i=node["id"]
        h=A-node["resistance"]
        g.add_edge(source,i,capacity=max(0.,h))
        g.add_edge(i,sink,capacity=max(0.,-h))
    for edge in EDGES:
        i,j,J=edge["i"],edge["j"],edge["J"]
        g.add_edge(i,j,capacity=J)
        g.add_edge(j,i,capacity=J)
    _,(S,T)=nx.minimum_cut(g,source,sink)
    bits=[int(node["id"] in S) for node in NODES]
    return bits,energy(bits,year)

def main():
    print("year  A(year)  digital/20  exact_min_energy  newly_digital")
    prev=set()
    flips={name:None for name in NAME.values()}
    for year in range(MODEL["years"]["start"],MODEL["years"]["end"]+1):
        bits,e=exact_ground_state(year)
        current={NAME[i] for i,bit in enumerate(bits) if bit}
        new=current-prev
        for name in new:
            if flips[name] is None: flips[name]=year
        print(f"{year}   {0.07*(year-2026):.2f}       {len(current):2}/20    {e: .4f}    {', '.join(name for name in NAME.values() if name in new) or '—'}")
        prev=current
    print("\nIndustry flip years:")
    for name in NAME.values():print(f"  {name:15s} {flips[name]}")

if __name__=="__main__":main()
