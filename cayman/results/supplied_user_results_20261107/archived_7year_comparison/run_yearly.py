"""Exact classical annual target selection for the supplied equal-cost model."""
from pathlib import Path
import csv, json, time
import target_selection_original as model
ROOT=Path(__file__).resolve().parent
model.LEAD_TIME_YEARS=7
rows=model.load_rows(ROOT/'quantum_flip_years.csv')
summary=[]; selections=[]; all_candidates=[]
for year in range(2026,2041):
    model.CURRENT_YEAR=year
    start=time.perf_counter()
    candidates=model.make_candidates(rows)
    assert all(c['cost']==1 for c in candidates)
    # With unit costs, nonnegative values, no pair bonuses, and at most one
    # region per industry: keep each industry's best region, then top B.
    best={}
    for c in candidates:
        if c['industry'] not in best or c['value']>best[c['industry']]['value']:
            best[c['industry']]=c
    ranked=sorted(best.values(),key=lambda c:-c['value'])
    chosen=[c for c in ranked[:model.BUDGET] if c['value']>0]
    selected_ids={c['id'] for c in chosen}
    Q,variables,penalty=model.build_qubo(candidates,model.BUDGET)
    slack=model.BUDGET-len(chosen)
    assignment={v:int(v in selected_ids) for v in variables}
    for k in range(slack.bit_length()):
        assignment[f'slack_{k}']=(slack>>k)&1
    energy=sum(v*assignment[a]*assignment[b] for (a,b),v in Q.items())
    value=sum(c['value'] for c in chosen)
    assert abs(energy-(-value-penalty*model.BUDGET**2))<1e-7
    assert len({c['industry'] for c in chosen})==len(chosen)
    elapsed=time.perf_counter()-start
    summary.append(dict(year=year,candidate_count=len(candidates),eligible_industries=len(best),selected_count=len(chosen),total_cost=len(chosen),budget=model.BUDGET,total_value=value,unused_budget=slack,qubo_variables=len(variables),penalty=penalty,minimum_qubo_energy_without_constant=energy,minimum_energy_including_budget_constant=-value,solve_and_qubo_check_seconds=elapsed))
    selections.extend(dict(year=year,**c) for c in chosen)
    all_candidates.extend(dict(year=year,selected=int(c['id'] in selected_ids),**c) for c in candidates)
for name,records in [('yearly_summary.csv',summary),('yearly_selected_targets.csv',selections),('yearly_all_candidates.csv',all_candidates)]:
    with (ROOT/name).open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(records[0]));w.writeheader();w.writerows(records)
# Validate the analytical reduction against exhaustive QUBO enumeration on
# several small subsets (including duplicate industries and unused budget).
checks=0
for year in (2026,2028,2030,2033,2035,2040):
    model.CURRENT_YEAR=year
    cs=model.make_candidates(rows)[:8]
    for budget in (0,1,3):
        Q,vs,A=model.build_qubo(cs,budget)
        exact,_=model.solve_qubo_exact(Q,vs)
        best={}
        for c in cs: best[c['industry']]=max(best.get(c['industry'],0),c['value'])
        val=sum(sorted(best.values(),reverse=True)[:budget])
        assert abs(exact-(-val-A*budget**2))<1e-7
        checks+=1
(ROOT/'validation.json').write_text(json.dumps(dict(exhaustive_small_qubo_checks=checks,passed=True,years=15),indent=2))
print('Validation:',checks,'exhaustive small-QUBO checks passed')
for s in summary: print(s['year'],s['candidate_count'],s['selected_count'],round(s['total_value'],6))
