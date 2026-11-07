"""Solve a small target-selection QUBO using the five-region flip-year CSV.

Input columns: industry, region, base_resistance, flip_year. The flip-year CSV
provides the transition map, but it does not provide sales values or regional
costs. The editable neutral demo assumptions below therefore give every region
cost 1 and attractiveness 1.0, use
    value = BASE_VALUE * (1 - base_resistance) * urgency,
and include no sales pair bonuses. These are planning assumptions, not values
reported by the source model.

The QUBO is minimized by exhaustive classical enumeration for small instances.
This is not a QAOA run or a quantum-hardware result.
"""
from __future__ import annotations

import argparse
import csv
from itertools import combinations
from math import ceil, log2
from pathlib import Path


CURRENT_YEAR = 2026
LEAD_TIME_YEARS = 4
BUDGET = 5
BASE_VALUE = 8.0

# The report names these regions but does not provide sales costs or
# attractiveness scores. Set business-specific values here when available.
REGIONS = ["California", "Pacific NW", "Texas", "Mountain West", "Southwest"]
REGION_COST = {region: 1 for region in REGIONS}
REGION_ATTRACTIVENESS = {region: 1.0 for region in REGIONS}


def load_rows(path: Path):
    rows = []
    seen = set()
    with path.open("r", newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        required = {"industry", "region", "base_resistance", "flip_year"}
        fields = {name.strip() for name in (reader.fieldnames or [])}
        if not required.issubset(fields):
            raise ValueError(
                "CSV must contain industry, region, base_resistance, and "
                f"flip_year columns. Found: {reader.fieldnames or []}"
            )
        for line, row in enumerate(reader, start=2):
            industry = (row.get("industry") or "").strip()
            region = (row.get("region") or "").strip()
            try:
                resistance = float(row.get("base_resistance", ""))
                flip_year = int(row.get("flip_year", ""))
            except ValueError as exc:
                raise ValueError(f"Invalid numeric value on CSV line {line}.") from exc
            if not industry or not region:
                raise ValueError(f"Missing industry or region on CSV line {line}.")
            if region not in REGION_COST:
                raise ValueError(f"Unknown region {region!r} on CSV line {line}.")
            if not 0.0 <= resistance <= 1.0:
                raise ValueError(f"base_resistance must be in [0, 1] on line {line}.")
            key = (industry, region)
            if key in seen:
                raise ValueError(f"Duplicate industry-region pair {key} in CSV.")
            seen.add(key)
            rows.append({
                "industry": industry,
                "region": region,
                "base_resistance": resistance,
                "flip_year": flip_year,
            })
    if not rows:
        raise ValueError(f"No rows found in {path}.")
    return rows


def make_candidates(rows):
    candidates = []
    for row in rows:
        years_until_flip = row["flip_year"] - CURRENT_YEAR
        if not 1 <= years_until_flip <= LEAD_TIME_YEARS:
            continue
        urgency = (LEAD_TIME_YEARS + 1 - years_until_flip) / LEAD_TIME_YEARS
        region = row["region"]
        value = (
            BASE_VALUE
            * (1 - row["base_resistance"])
            * REGION_ATTRACTIVENESS[region]
            * urgency
        )
        candidates.append({
            "id": f"{row['industry']}|{region}",
            "industry": row["industry"],
            "region": region,
            "flip_year": row["flip_year"],
            "cost": REGION_COST[region],
            "value": value,
        })
    return candidates


def build_qubo(candidates, budget):
    """Build a QUBO with budget equality and at-most-one-region constraints."""
    if budget < 0:
        raise ValueError("Budget must be nonnegative.")
    slack_count = ceil(log2(budget + 1)) if budget else 0
    slack = [(f"slack_{k}", 2**k) for k in range(slack_count)]
    variables = [c["id"] for c in candidates] + [name for name, _ in slack]
    order = {name: i for i, name in enumerate(variables)}
    Q = {}

    def add(a, b, amount):
        if order[a] > order[b]:
            a, b = b, a
        Q[(a, b)] = Q.get((a, b), 0.0) + amount

    penalty = sum(max(0.0, c["value"]) for c in candidates) + 1.0
    for c in candidates:
        add(c["id"], c["id"], -c["value"])

    by_industry = {}
    for c in candidates:
        by_industry.setdefault(c["industry"], []).append(c["id"])
    for ids in by_industry.values():
        for a, b in combinations(ids, 2):
            add(a, b, penalty)

    budget_terms = [(c["id"], int(c["cost"])) for c in candidates] + slack
    for name, cost in budget_terms:
        add(name, name, penalty * (cost * cost - 2 * budget * cost))
    for (a, cost_a), (b, cost_b) in combinations(budget_terms, 2):
        add(a, b, 2 * penalty * cost_a * cost_b)
    return Q, variables, penalty


def solve_qubo_exact(Q, variables, max_variables=24):
    n = len(variables)
    if n > max_variables:
        raise ValueError(
            f"Exact solver limit is {max_variables} variables; this QUBO has {n}."
        )
    index = {name: i for i, name in enumerate(variables)}
    terms = [(index[a], index[b], value) for (a, b), value in Q.items()]
    best_energy = float("inf")
    best_assignment = None
    for mask in range(1 << n):
        energy = sum(
            value for i, j, value in terms
            if ((mask >> i) & 1) and ((mask >> j) & 1)
        )
        if energy < best_energy:
            best_energy = energy
            best_assignment = {
                name: (mask >> i) & 1 for i, name in enumerate(variables)
            }
    return best_energy, best_assignment


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--flip-years-csv", type=Path,
        default=Path("quantum_flip_years.csv"),
        help="Five-region CSV path (default: quantum_flip_years.csv)",
    )
    parser.add_argument("--budget", type=int, default=BUDGET)
    args = parser.parse_args(argv)

    rows = load_rows(args.flip_years_csv)
    candidates = make_candidates(rows)
    if not candidates:
        raise SystemExit(
            f"No candidates flip from {CURRENT_YEAR + 1} through "
            f"{CURRENT_YEAR + LEAD_TIME_YEARS}."
        )
    Q, variables, penalty = build_qubo(candidates, args.budget)
    energy, assignment = solve_qubo_exact(Q, variables)
    selected = [c for c in candidates if assignment.get(c["id"], 0)]
    cost = sum(c["cost"] for c in selected)
    value = sum(c["value"] for c in selected)

    print(f"Loaded {len(rows)} industry-region rows, "
          f"{len({r['industry'] for r in rows})} industries, "
          f"{len({r['region'] for r in rows})} regions.")
    print(f"Candidates within {LEAD_TIME_YEARS} years: {len(candidates)}")
    print("Assumptions: equal region attractiveness and cost, one region per "
          "industry, and no sales pair bonuses.")
    print("\nBest target plan (exact QUBO minimization):")
    for c in selected:
        print(f"  {c['industry']} in {c['region']} "
              f"(flip {c['flip_year']}, cost {c['cost']}, value {c['value']:.2f})")
    print(f"Total cost: {cost} / {args.budget}")
    print(f"Total value under these assumptions: {value:.2f}")
    print(f"Minimum QUBO energy (constant offset omitted): {energy:.4f}")
    print("Slack assignment:", {
        n: bit for n, bit in assignment.items() if n.startswith("slack_")
    })
    print(f"QUBO variables: {len(variables)}; penalty strength: {penalty:.2f}")


if __name__ == "__main__":
    main()
