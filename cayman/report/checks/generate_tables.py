"""Format saved evidence; no circuits or benchmarks are run."""
import csv
from pathlib import Path
root=Path(__file__).resolve().parents[1]
def read(n):return list(csv.DictReader((root/'metrics'/n).open()))
def save(n,rows): (root/'tables'/n).write_text('\n'.join(' & '.join(r)+r' \\' for r in rows)+'\n')
b=read('benchmark_summary.csv')
save('benchmark_rows.tex',[[r['n'],r['repeat_count'],f"{float(r['mincut_end_to_end_median_s']):.3e}",f"{float(r['qaoa_end_to_end_median_s']):.3e}",f"{float(r['qaoa_expected_energy_gap_median']):.5f}",f"{float(r['qaoa_ground_probability_median']):.3e}"] for r in b if r['family']=='common'])
a={r['year']:r for r in read('target_p1_yearly_metrics.csv')}
p=read('target_p2_yearly_metrics.csv')
f=lambda v:f'{max(0,float(v)):.4f}'
e=[];q=[];m=[]
for r in p:
 y=r['year'];s=a[y]
 if r['status']!='completed':
  
  if y=='2035':
   e.append(['2035--2040','0,0,0',*['---']*5]);q.append(['2035--2040',*['---']*6]);m.append(['2035--2040',*['---']*4])
  continue
 e.append([y,','.join(r[t] for t in ['eligible_industries','k','basis_dimension']),f(r['exact_optimum_value']),f(r['uniform_feasible_expected_value']),f(r['p1_expected_value']),f(r['p2_expected_value']),f(r['p2_gap'])])
 q.append([y,f(s['qaoa_gap']),f(s['qaoa_ratio']),f(r['p2_ratio']),f"{float(s['qaoa_optimum_probability_all_ties']):.6f}",f"{float(r['p2_optimum_probability_all_ties']):.6f}",f(r['p2_optimizer_seconds'])])
 m.append([y,f(r['p2_mode_value']),f(r['p2_mode_value_gap']),f"{float(r['p2_mode_probability']):.6f}",f"{float(r['p2_optimum_probability_all_ties']):.6f}"])
save('target_expected_rows.tex',e);save('target_quality_rows.tex',q);save('target_map_rows.tex',m)
print('Tables generated from saved CSVs')

# Update embedded table blocks for portable LaTeX engine compatibility.
import re
main=root/'main.tex'
s=main.read_text()
for t in (root/'tables').glob('*.tex'):
 marker='% Generated from metrics; audit copy: tables/'+t.name+'\n'
 pattern=re.escape(marker)+r'.*?(?=\n\\bottomrule)'
 s=re.sub(pattern,lambda m:marker+t.read_text().rstrip(),s,flags=re.S)
main.write_text(s)
