#!/usr/bin/env python3
"""20-industry Vasion QAOA, three-layer p=3 experiment, using Classiq SDK.

Keep this file with paper_phase_transition_20_industries.json and
paper_phase_transition_baseline.py.

Install: pip install classiq scipy pandas networkx
Log in:  python -c "import classiq; classiq.authenticate()"

Try one year first:
    python vasion_classiq_qaoa_p3.py --year 2036 --show
Then the unoptimized 15-year baseline:
    python vasion_classiq_qaoa_p3.py --all-years
Then COBYLA on one year:
    python vasion_classiq_qaoa_p3.py --year 2036 --optimize --shots 4096 --maxiter 100

This file was constructed against the Classiq SDK documentation (Nov 2026).
It has passed Python syntax and classical model checks, but Classiq cloud
synthesis and remote execution have not been tested in this environment.
"""
import argparse
import ast
import csv
import re
from pathlib import Path

import numpy as np
from scipy.optimize import minimize
from classiq import (
    qfunc, CReal, QBit, QArray, Output, allocate,
    H, CX, RX, RZ, synthesize, sample, show, authenticate,
)
from paper_phase_transition_baseline import exact_ground_state, energy

OUT_DIR = Path(__file__).resolve().parent
N = 20
# Warm start: the optimized p=2 angles from the 2036 screenshot.
# gamma3=beta3=0 makes the initial p=3 circuit equivalent to p=2.
ANGLES_0 = [0.9697583926673115, -0.4152319687520098,
            0.9461322572548342, -0.42202650302658545, 0.0, 0.0]
PARAM_KEYS = ('gamma_1', 'beta_1', 'gamma_2', 'beta_2', 'gamma_3', 'beta_3')


@qfunc
def cost_layer(gamma: CReal, pressure: CReal, v: QArray[QBit]):
    """Implements exp(-i gamma H_C); RZ(theta)=exp(-i theta Z/2)."""
    RZ(2 * gamma * (pressure - 0.10000000), v[0])  # Technology
    RZ(2 * gamma * (pressure - 0.20000000), v[1])  # Media
    RZ(2 * gamma * (pressure - 0.25000000), v[2])  # Telecom
    RZ(2 * gamma * (pressure - 0.30000000), v[3])  # Retail
    RZ(2 * gamma * (pressure - 0.35000000), v[4])  # Hospitality
    RZ(2 * gamma * (pressure - 0.40000000), v[5])  # Logistics
    RZ(2 * gamma * (pressure - 0.45000000), v[6])  # Banking
    RZ(2 * gamma * (pressure - 0.50000000), v[7])  # Accounting
    RZ(2 * gamma * (pressure - 0.50000000), v[8])  # Manufacturing
    RZ(2 * gamma * (pressure - 0.55000000), v[9])  # Insurance
    RZ(2 * gamma * (pressure - 0.55000000), v[10])  # Energy
    RZ(2 * gamma * (pressure - 0.60000000), v[11])  # Pharma
    RZ(2 * gamma * (pressure - 0.60000000), v[12])  # Education
    RZ(2 * gamma * (pressure - 0.65000000), v[13])  # Nonprofit
    RZ(2 * gamma * (pressure - 0.65000000), v[14])  # Real Estate
    RZ(2 * gamma * (pressure - 0.70000000), v[15])  # Construction
    RZ(2 * gamma * (pressure - 0.70000000), v[16])  # Agriculture
    RZ(2 * gamma * (pressure - 0.75000000), v[17])  # Healthcare
    RZ(2 * gamma * (pressure - 0.85000000), v[18])  # Government
    RZ(2 * gamma * (pressure - 0.90000000), v[19])  # Legal

    # Healthcare - Insurance, J=0.15000
    CX(v[17], v[9])
    RZ(-0.30000000 * gamma, v[9])
    CX(v[17], v[9])
    # Manufacturing - Logistics, J=0.13500
    CX(v[8], v[5])
    RZ(-0.27000000 * gamma, v[5])
    CX(v[8], v[5])
    # Banking - Real Estate, J=0.12000
    CX(v[6], v[14])
    RZ(-0.24000000 * gamma, v[14])
    CX(v[6], v[14])
    # Retail - Logistics, J=0.12000
    CX(v[3], v[5])
    RZ(-0.24000000 * gamma, v[5])
    CX(v[3], v[5])
    # Construction - Real Estate, J=0.12000
    CX(v[15], v[14])
    RZ(-0.24000000 * gamma, v[14])
    CX(v[15], v[14])
    # Healthcare - Pharma, J=0.10500
    CX(v[17], v[11])
    RZ(-0.21000000 * gamma, v[11])
    CX(v[17], v[11])
    # Legal - Real Estate, J=0.10500
    CX(v[19], v[14])
    RZ(-0.21000000 * gamma, v[14])
    CX(v[19], v[14])
    # Healthcare - Government, J=0.09000
    CX(v[17], v[18])
    RZ(-0.18000000 * gamma, v[18])
    CX(v[17], v[18])
    # Legal - Government, J=0.09000
    CX(v[19], v[18])
    RZ(-0.18000000 * gamma, v[18])
    CX(v[19], v[18])
    # Accounting - Banking, J=0.09000
    CX(v[7], v[6])
    RZ(-0.18000000 * gamma, v[6])
    CX(v[7], v[6])
    # Government - Education, J=0.09000
    CX(v[18], v[12])
    RZ(-0.18000000 * gamma, v[12])
    CX(v[18], v[12])
    # Agriculture - Logistics, J=0.09000
    CX(v[16], v[5])
    RZ(-0.18000000 * gamma, v[5])
    CX(v[16], v[5])
    # Telecom - Technology, J=0.09000
    CX(v[2], v[0])
    RZ(-0.18000000 * gamma, v[0])
    CX(v[2], v[0])
    # Insurance - Banking, J=0.07500
    CX(v[9], v[6])
    RZ(-0.15000000 * gamma, v[6])
    CX(v[9], v[6])
    # Legal - Banking, J=0.07500
    CX(v[19], v[6])
    RZ(-0.15000000 * gamma, v[6])
    CX(v[19], v[6])
    # Energy - Manufacturing, J=0.07500
    CX(v[10], v[8])
    RZ(-0.15000000 * gamma, v[8])
    CX(v[10], v[8])
    # Technology - Media, J=0.07500
    CX(v[0], v[1])
    RZ(-0.15000000 * gamma, v[1])
    CX(v[0], v[1])
    # Insurance - Legal, J=0.06000
    CX(v[9], v[19])
    RZ(-0.12000000 * gamma, v[19])
    CX(v[9], v[19])
    # Accounting - Nonprofit, J=0.06000
    CX(v[7], v[13])
    RZ(-0.12000000 * gamma, v[13])
    CX(v[7], v[13])
    # Construction - Government, J=0.06000
    CX(v[15], v[18])
    RZ(-0.12000000 * gamma, v[18])
    CX(v[15], v[18])
    # Hospitality - Retail, J=0.06000
    CX(v[4], v[3])
    RZ(-0.12000000 * gamma, v[3])
    CX(v[4], v[3])
    # Pharma - Logistics, J=0.06000
    CX(v[11], v[5])
    RZ(-0.12000000 * gamma, v[5])
    CX(v[11], v[5])
    # Nonprofit - Education, J=0.06000
    CX(v[13], v[12])
    RZ(-0.12000000 * gamma, v[12])
    CX(v[13], v[12])
    # Media - Retail, J=0.04500
    CX(v[1], v[3])
    RZ(-0.09000000 * gamma, v[3])
    CX(v[1], v[3])

@qfunc
def mixer_layer(beta: CReal, v: QArray[QBit]):
    RX(2 * beta, v[0])
    RX(2 * beta, v[1])
    RX(2 * beta, v[2])
    RX(2 * beta, v[3])
    RX(2 * beta, v[4])
    RX(2 * beta, v[5])
    RX(2 * beta, v[6])
    RX(2 * beta, v[7])
    RX(2 * beta, v[8])
    RX(2 * beta, v[9])
    RX(2 * beta, v[10])
    RX(2 * beta, v[11])
    RX(2 * beta, v[12])
    RX(2 * beta, v[13])
    RX(2 * beta, v[14])
    RX(2 * beta, v[15])
    RX(2 * beta, v[16])
    RX(2 * beta, v[17])
    RX(2 * beta, v[18])
    RX(2 * beta, v[19])

@qfunc
def main(pressure: CReal,
         gammaone: CReal, betaone: CReal,
         gammatwo: CReal, betatwo: CReal,
         gammathree: CReal, betathree: CReal,
         v: Output[QArray[QBit]]):
    allocate(N, v)
    H(v[0])
    H(v[1])
    H(v[2])
    H(v[3])
    H(v[4])
    H(v[5])
    H(v[6])
    H(v[7])
    H(v[8])
    H(v[9])
    H(v[10])
    H(v[11])
    H(v[12])
    H(v[13])
    H(v[14])
    H(v[15])
    H(v[16])
    H(v[17])
    H(v[18])
    H(v[19])
    cost_layer(gammaone, pressure, v)
    mixer_layer(betaone, v)
    cost_layer(gammatwo, pressure, v)
    mixer_layer(betatwo, v)
    cost_layer(gammathree, pressure, v)
    mixer_layer(betathree, v)


def make_parameters(year: int, angles):
    if len(angles) != 6:
        raise ValueError("p=3 requires six angles")
    return {
        "pressure": 0.07 * (year - 2026),
        "gammaone": float(angles[0]), "betaone": float(angles[1]),
        "gammatwo": float(angles[2]), "betatwo": float(angles[3]),
        "gammathree": float(angles[4]), "betathree": float(angles[5]),
    }


def parse_bits(row):
    """Classiq often returns qubit-index order in the 'v' array.
    Its displayed 'bitstring' is typically reversed (MSB-first).
    """
    val = row.get('v', None)
    if val is not None:
        if isinstance(val, str):
            try:
                val = ast.literal_eval(val)
            except (ValueError, SyntaxError):
                val = None
        if val is not None:
            try:
                bits = tuple(int(b) for b in val)
                if len(bits) == N and set(bits) <= {0,1}:
                    return bits
            except (ValueError, TypeError):
                pass
    raw = str(row.get('bitstring', '')).strip()
    if raw.lower().startswith('0x'):
        text = format(int(raw, 16), f'0{N}b')
    else:
        text = raw[2:] if raw.lower().startswith('0b') else raw
        text = text.zfill(N)
    if len(text) != N or not re.fullmatch(r'[01]+', text):
        raise ValueError(f'Could not parse qubit array/bitstring: {row}')
    return tuple(int(b) for b in reversed(text))


def probabilities(df):
    """Map v0..v19 tuple -> measured probability.

    'count' takes precedence, as it gives exact empirical shot weights.
    """
    result={}
    if 'count' in df.columns:
        total = float(df['count'].sum())
        if total <= 0: raise ValueError('No measurement counts in sample')
        for _, row in df.iterrows():
            bits = parse_bits(row)
            result[bits] = result.get(bits, 0) + float(row['count'])/total
    else:
        for _, row in df.iterrows():
            bits = parse_bits(row)
            result[bits] = result.get(bits, 0) + float(row['probability'])
        total=sum(result.values())
        if total <= 0: raise ValueError('No probabilities in sample')
        result={key: value/total for key, value in result.items()}
    return result


def mean_energy(df, year):
    return sum(p * energy(bits, year) for bits, p in probabilities(df).items())


def analyze(df, year, angles):
    hist = probabilities(df)
    exact_bits, e_min = exact_ground_state(year)
    exact_bits=tuple(exact_bits)
    best_bits = min(hist, key=lambda b: energy(b, year))
    most_likely_bits = max(hist, key=hist.get)
    e_best = energy(best_bits, year)
    exp_e = sum(p * energy(b,year) for b,p in hist.items())
    return {
        'year': year,
        'depth': 3,
        'pressure': round(0.07*(year-2026),4),
        'gamma_1': float(angles[0]), 'beta_1': float(angles[1]),
        'gamma_2': float(angles[2]), 'beta_2': float(angles[3]),
        'gamma_3': float(angles[4]), 'beta_3': float(angles[5]),
        'exact_min_energy': e_min,
        'qaoa_mean_energy': exp_e,
        'qaoa_best_sampled_energy': e_best,
        'qaoa_best_energy_gap': e_best-e_min,
        'qaoa_mean_energy_gap': exp_e-e_min,
        'exact_digital_count': sum(exact_bits),
        'qaoa_best_digital_count': sum(best_bits),
        'qaoa_best_bits_index_order': ''.join(map(str,best_bits)),
        'most_likely_bits_index_order': ''.join(map(str,most_likely_bits)),
        'most_likely_probability': hist[most_likely_bits],
        'exact_state_probability': hist.get(exact_bits, 0.0),
        'unique_observed_states': len(hist),
    }


def write_csv(path, rows):
    if not rows: return
    with Path(path).open('w', newline='', encoding='utf-8') as handle:
        writer=csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader(); writer.writerows(rows)


def main_cli():
    ap=argparse.ArgumentParser(description='Vasion Classiq QAOA 20-industry model')
    group=ap.add_mutually_exclusive_group(required=True)
    group.add_argument('--year', type=int, help='Run just one year, e.g. 2035')
    group.add_argument('--all-years', action='store_true', help='Run 2026 through 2040 (15 years)')
    ap.add_argument('--shots', type=int, default=1024)
    ap.add_argument('--optimize', action='store_true', help='Optimize 6 angles by SciPy COBYLA')
    ap.add_argument('--maxiter', type=int, default=60, help='Maximum COBYLA objective evaluations per year')
    ap.add_argument('--show', action='store_true', help='Open synthesized circuit in Classiq Studio')
    args=ap.parse_args()
    if args.year is not None and not 2026 <= args.year <= 2040:
        ap.error('Year must be 2026..2040')
    if args.shots < 1 or args.maxiter < 1:
        ap.error('shots and maxiter must be positive')
    years=list(range(2026,2041)) if args.all_years else [args.year]

    # This is the only synthesis call for the entire 15-year sweep.
    authenticate()
    print('Synthesizing p=3 20-qubit QAOA model once...')
    qp = synthesize(main)
    if args.show:
        show(qp)

    summary=[]
    raw=[]
    for year in years:
        angles=ANGLES_0.copy()
        if args.optimize:
            evaluations=[]
            def objective(x):
                params=make_parameters(year, x)
                data=sample(qp, parameters=params, num_shots=args.shots,
                            backend='simulator', verbose=False)
                e=mean_energy(data, year)
                evaluations.append({'year':year,'evaluation':len(evaluations)+1,
                                    'energy':e, **{k:float(v) for k,v in zip(PARAM_KEYS,x)}})
                return e
            fit=minimize(objective, x0=angles, method='COBYLA',
                         options={'maxiter':args.maxiter, 'rhobeg':0.25})

            # Validate promising parameter sets independently; noisy optimization
            # energies can make a lucky trial look better than it really is.
            top=sorted(evaluations,key=lambda r:r['energy'])[:5]
            validated=[]
            for candidate in top:
                test_angles=[candidate[k] for k in PARAM_KEYS]
                trial=sample(qp,
                             parameters=make_parameters(year,test_angles),
                             num_shots=8192,backend='simulator',verbose=False)
                trial_e=mean_energy(trial,year)
                validated.append((trial_e,test_angles))
                print(f'{year} validation energy: {trial_e:.4f}')
            best_validation_energy,angles=min(validated,key=lambda a:a[0])
            print(f'{year} selected angles: {angles}')
            print(f'{year} validated energy: {best_validation_energy:.4f}')
            write_csv(OUT_DIR/f'cobyla_history_p3_{year}.csv', evaluations)
            print(f'{year} COBYLA: {len(evaluations)} evaluations; optimizer message: {fit.message}')

        data=sample(qp, parameters=make_parameters(year,angles), num_shots=args.shots,
                    backend='simulator', verbose=False)
        row=analyze(data,year,angles)
        summary.append(row)
        for bits,p in probabilities(data).items():
            raw.append({'year':year,'qubit_index_0_to_19':''.join(map(str,bits)),
                        'display_bitstring':''.join(map(str,reversed(bits))),
                        'probability':p,'ising_energy':energy(bits,year)})
        print(f"{year}: classical min={row['exact_min_energy']:.4f} | "
              f"QAOA mean={row['qaoa_mean_energy']:.4f} | "
              f"best sampled={row['qaoa_best_sampled_energy']:.4f} | "
              f"digital best={row['qaoa_best_digital_count']}/20")

    suffix='optimized' if args.optimize else 'baseline'
    path_summary=OUT_DIR/f'vasion_qaoa_p3_{suffix}_summary.csv'
    path_raw=OUT_DIR/f'vasion_qaoa_p3_{suffix}_measurements.csv'
    write_csv(path_summary,summary)
    write_csv(path_raw,raw)
    print(f'Finished {len(summary)} of {len(years)} requested years.')
    print(f'Summary: {path_summary}')
    print(f'Full measurements: {path_raw}')


if __name__=='__main__':
    main_cli()

