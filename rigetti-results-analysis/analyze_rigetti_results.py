import re, subprocess, itertools, json
from pathlib import Path
import csv, numpy as np

def write_csv(path, rows):
    keys=list(rows[0].keys()) if rows else []
    with open(path,'w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=keys); w.writeheader(); w.writerows(rows)
from qbraid.runtime import load_job

OUT=Path(__file__).parent/'results_analysis'; OUT.mkdir(exist_ok=True)
industries=['Technology','Media','Telecom','Retail','Hospitality','Logistics','Banking','Accounting','Manufacturing','Insurance','Energy','Pharma','Education','Nonprofit','Real Estate','Construction','Agriculture','Healthcare','Government','Legal']
resistance=np.array([.10,.20,.25,.30,.35,.40,.45,.50,.50,.55,.55,.60,.60,.65,.65,.70,.70,.75,.85,.90])
ties=[('Healthcare','Insurance',1.0),('Manufacturing','Logistics',.9),('Banking','Real Estate',.8),('Retail','Logistics',.8),('Construction','Real Estate',.8),('Healthcare','Pharma',.7),('Legal','Real Estate',.7),('Healthcare','Government',.6),('Legal','Government',.6),('Accounting','Banking',.6),('Government','Education',.6),('Agriculture','Logistics',.6),('Telecom','Technology',.6),('Insurance','Banking',.5),('Legal','Banking',.5),('Energy','Manufacturing',.5),('Technology','Media',.5),('Insurance','Legal',.4),('Accounting','Nonprofit',.4),('Construction','Government',.4),('Hospitality','Retail',.4),('Pharma','Logistics',.4),('Nonprofit','Education',.4),('Media','Retail',.3)]
idx={x:i for i,x in enumerate(industries)}
# Locate the exact named jobs, no submission.
txt=subprocess.check_output(['qbraid','jobs','list','--limit','100'],text=True)
ids=re.findall(r'aws:rigetti:qpu:cepheus-1-108q-426f-qjob-[0-9a-f]+',txt)
jobs={}
for jid in ids:
    j=load_job(jid); md=j.metadata(); name=md.get('name','')
    m=re.fullmatch(r'paper-qaoa-(20(?:2[6-9]|3[0-9]|40))-20node',name)
    if m: jobs[int(m.group(1))]=(jid,j,md)
missing=sorted(set(range(2026,2041))-set(jobs))
if missing: raise RuntimeError(f'Missing named jobs: {missing}')
rows=[]; heat=[]; flips=[]; summaries=[]; params=[]
# Exact model parameters are decoded from each submitted QASM, not challenge guesses.
for year in range(2026,2041):
    jid,j,md=jobs[year]; qasm=md['program'].data
    # regex above returns tuples; correct extraction
    rz_pairs=[(float(v),int(i)) for v,i in re.findall(r'\nrz\(([-+0-9.eE]+)\) q\[(\d+)\];',qasm)]
    fields=np.array([v for v,i in sorted(rz_pairs,key=lambda x:x[1])])
    rx=float(re.search(r'\nrx\(([-+0-9.eE]+)\) q\[0\];',qasm).group(1))
    beta=rx/2
    # coupling scale and gamma from first edge, using original strength and exact submitted RZZ angle
    rzz=float(re.search(r'rzz\(([-+0-9.eE]+)\) q\[17\], q\[9\];',qasm).group(1))
    gamma=abs(rzz)/(2*.15*1.0)
    # fields = 2 gamma (r_i - A)
    A=float(np.mean(resistance-fields/(2*gamma)))
    J=[(.15*s,idx[a],idx[b]) for a,b,s in ties]
    def energy(bits):
        z=1-2*np.array(bits,dtype=int); return float(np.dot(fields/(2*gamma),z)-sum(w*z[a]*z[b] for w,a,b in J))
    # equivalent original energy: fields/(2gamma)=r-A and w=.15*s
    ns=np.arange(1<<20,dtype=np.uint32); B=((ns[:,None]>>np.arange(20))&1).astype(np.int8); Z=1-2*B
    E=Z.dot(fields/(2*gamma))
    for w,a,b in J: E-=w*Z[:,a]*Z[:,b]
    bestE=float(E.min()); bi=np.flatnonzero(np.isclose(E,bestE,atol=1e-12)); best=B[bi].tolist()
    counts=j.result().measurement_counts()
    scored=[]
    for raw,count in counts.items():
        bits=[int(raw[-1-i]) for i in range(20)]
        scored.append((energy(bits),raw,bits,int(count)))
    min_sample=min(x[0] for x in scored); winners=[x for x in scored if abs(x[0]-min_sample)<1e-12]
    # deterministic representative; preserve all tied sampled minima in CSV
    win=min(winners,key=lambda x:x[1]); qb=win[2]
    classical=best[0]
    for i,name in enumerate(industries):
        states={x[2][i] for x in winners}; bit=qb[i]
        ambiguous=len(states)>1
        heat.append({'year':year,'industry':name,'node':i,'qubit':i,'digital':1-bit if not ambiguous else '', 'paper':bit if not ambiguous else '', 'state': 'ambiguous' if ambiguous else ('paper' if bit else 'digital')})
    rows.append({'year':year,'job_qrn':jid,'shots':md['shots'],'gamma':gamma,'beta':beta,'A':A,'sampled_min_energy':min_sample,'sampled_min_bitstrings':'|'.join(x[1] for x in winners),'sampled_min_count':sum(x[3] for x in winners),'classical_min_energy':bestE,'classical_min_bitstrings':'|'.join(''.join(map(str,b)) for b in best),'energy_gap':min_sample-bestE,'state_agreement':qb==classical,'sampled_min_paper_count':sum(qb),'classical_paper_count':sum(classical),'cost_credits':float(md['cost'])})
    params.append({'year':year,'job_qrn':jid,'gamma':gamma,'beta':beta,'A':A,'rz_angles_q0_to_q19':json.dumps(fields.tolist()),'node_order':'q[i]=industry[i]','count_mapping':'industry i = returned_string[-1-i]','shots':md['shots']})
    if year>2026:
        prev=rows[-2]; pb=next(r['paper'] for r in heat if r['year']==year-1 and r['industry']==industries[0]) # overwritten below
        for i,name in enumerate(industries):
            old=next(r['paper'] for r in heat if r['year']==year-1 and r['industry']==name); new=qb[i]
            if old!=new: flips.append({'from_year':year-1,'to_year':year,'industry':name,'from_state':'paper' if old else 'digital','to_state':'paper' if new else 'digital','flip':'digital_to_paper' if new else 'paper_to_digital','reversal_flag': year>=2028 and old != (next(r['paper'] for r in heat if r['year']==year-2 and r['industry']==name)) if year>2027 else False,'tied_minimum':len(winners)>1})
# summaries first digital
for name in industries:
 d=[r for r in heat if r['industry']==name and r['digital']==1]
 summaries.append({'industry':name,'first_digital_year':min(r['year'] for r in d) if d else None,'never_digital':not bool(d)})
write_csv(OUT/'industry_year_heatmap.csv',heat); write_csv(OUT/'quantum_classical_energy_gaps.csv',rows)
write_csv(OUT/'submitted_parameters.csv',params); write_csv(OUT/'year_to_year_flips.csv',flips); write_csv(OUT/'first_digital_year_summary.csv',summaries)
# wide heatmap CSV and HTML heat map
years=list(range(2026,2041)); by={(r['industry'],r['year']):r['state'] for r in heat}
with open(OUT/'industry_by_year_paper_digital.csv','w',newline='') as f:
 w=csv.writer(f); w.writerow(['industry']+years)
 for name in industries: w.writerow([name]+[by[(name,y)] for y in years])
html=['<table><caption>Industry-by-year paper/digital heat map</caption><tr><th>Industry</th>'+''.join(f'<th>{y}</th>' for y in years)+'</tr>']
for name in industries: html.append('<tr><th>'+name+'</th>'+''.join(f'<td class="{by[(name,y)]}">{by[(name,y)]}</td>' for y in years)+'</tr>')
html.append('</table><style>td{padding:4px;text-align:center}.paper{background:#f6b26b}.digital{background:#93c47d}</style>')
(OUT/'industry_by_year_paper_digital.html').write_text(''.join(html))
(OUT/'README.md').write_text('# Rigetti results analysis\n\nResults retrieved from existing completed jobs only. Node order and mapping are decoded from submitted QASM metadata. Returned bitstrings use industry i = string[-1-i].\n')
print(f'Analyzed {len(rows)} jobs; outputs in {OUT}')
