"""Tiny illustrative algebra only; no project simulation or benchmark."""
import cmath, math, json
from pathlib import Path
rows=[]
for b1,b2 in [(0,0),(0,1),(1,0),(1,1)]:
 s1,s2=1-2*b1,1-2*b2
 E=-4*s1*s2-3*s1+2*s2
 cut=8*(b1!=b2)+6*b1+4*(1-b2)
 assert E==cut-9
 rows.append({'bits':f'{b1}{b2}','energy':E,'cut':cut})
assert [r['energy'] for r in rows]==[-5,-1,9,-3]
maxerr=0
for beta,gamma in [(0,0),(.2,.7),(-.6,.31),(math.pi/4,-math.pi/4)]:
 c,s=math.cos(beta),math.sin(beta)
 a0=(c*cmath.exp(-1j*gamma)-1j*s*cmath.exp(1j*gamma))/math.sqrt(2)
 a1=(c*cmath.exp(1j*gamma)-1j*s*cmath.exp(-1j*gamma))/math.sqrt(2)
 p0=(1+math.sin(2*beta)*math.sin(2*gamma))/2
 maxerr=max(maxerr,abs(abs(a0)**2-p0),abs(abs(a1)**2-(1-p0)))
 assert abs(abs(a0)**2-p0)<1e-12
assert abs(a0)<1e-12 and abs(abs(a1)-1)<1e-12
out={'illustrative_not_empirical':True,'two_qubit_rows':rows,'toy_probability_max_error':maxerr,'toy_ground_probability':abs(a1)**2}
print(json.dumps(out,indent=2))
Path(__file__).with_name('algebra-checks.json').write_text(json.dumps(out,indent=2)+'\n')
