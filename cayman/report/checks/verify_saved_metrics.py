"""Consistency checks of existing evidence only; no project jobs."""
import csv,json,math,hashlib
from pathlib import Path
root=Path(__file__).resolve().parents[1]
def read(name):return list(csv.DictReader((root/'metrics'/name).open()))
p1={r['year']:r for r in read('target_p1_yearly_metrics.csv')}
p2=read('target_p2_yearly_metrics.csv'); rec=read('target_p2_yearly_recommendations.csv')
assert len(p2)==15
for r in p2:
 if r['status']!='completed':continue
 a=p1[r['year']];n=int(r['eligible_industries']);k=int(r['k'])
 assert int(r['basis_dimension'])==math.comb(n,k)
 assert abs(float(r['p2_feasibility_mass'])-1)<1e-10
 assert abs(float(r['p2_marginal_sum'])-k)<1e-10
 assert float(r['p2_expected_value'])>=float(a['qaoa_expected_value'])-1e-10
 assert abs(float(r['p2_gap'])-(float(r['exact_optimum_value'])-float(r['p2_expected_value'])))<1e-10
 rs=[s for s in rec if s['year']==r['year']]
 exact=sum(float(s['value'])*int(s['exact_representative_recommended']) for s in rs)
 MAP=sum(float(s['value'])*int(s['p2_map_feasible_recommended']) for s in rs)
 assert abs(exact-float(r['exact_optimum_value']))<1e-10
 assert abs(MAP-float(r['p2_mode_value']))<1e-10
 assert sum(int(s['p2_map_feasible_recommended']) for s in rs)==k
b=read('benchmark_summary.csv'); assert max(int(r['n']) for r in b if r['family']=='common')==26
assert max(int(r['n']) for r in b)==8000
q=json.loads((root/'metrics/qbraid_3q_verified_metrics.json').read_text())
assert q['ground_shots']/q['shots']==q['ground_shot_probability']==0.805
out={'checks_passed':True,'target_years':len(p2),'eligible_target_years':sum(r['status']=='completed' for r in p2),'no_eligible_years':sum(r['status']!='completed' for r in p2),'qbraid_ground_fraction':q['ground_shot_probability'],'metric_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((root/'metrics').iterdir())}}
Path(__file__).with_name('saved-metrics-checks.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps(out,indent=2))
