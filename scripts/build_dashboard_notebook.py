"""Generate the qBraid-Lab-ready teaching notebook without notebook editor state."""
from pathlib import Path
import nbformat as nbf


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "notebooks" / "paperflip_dashboard.ipynb"


def code(source: str):
    return nbf.v4.new_code_cell(source.strip() + "\n")


def markdown(source: str):
    return nbf.v4.new_markdown_cell(source.strip() + "\n")


def build():
    nb = nbf.v4.new_notebook()
    nb.metadata.kernelspec = {"display_name": "Python 3", "language": "python", "name": "python3"}
    nb.metadata.language_info = {"name": "python", "version": "3.12"}
    nb.cells = [
        markdown("""# Paper Phase Transition: interactive teaching lab

**Purpose:** learn how an illustrative business-dependence story becomes an
Ising/QUBO/circuit model, then compare exact, classical, and cached quantum
sampling evidence. This notebook runs locally in qBraid Lab; it never starts a
server, authenticates, or submits a remote job. **Status: not deployed to
qBraid Lab.**

Use the tabs in order. **Predict before revealing** each answer. Coefficients
are challenge-suggested illustrations, not forecasts or causal estimates."""),
        code("""# qBraid Lab setup (run once in a fresh environment)
# %pip install -e ".[dashboard,quantum]"
#
# Launch locally:
# jupyter lab notebooks/paperflip_dashboard.ipynb
# In qBraid Lab, upload/open this repository and run this notebook. No deployment is claimed."""),
        code("""from __future__ import annotations
from pathlib import Path
import itertools, json
import numpy as np
import matplotlib.pyplot as plt
import ipywidgets as W
from IPython.display import display, Markdown, HTML, clear_output

from paperflip.model import load_model, IsingModel
from paperflip.exact import mincut, flip_intervals
from paperflip.solvers import simulated_annealing, _decode
from paperflip.dashboard import (
    tiny_business_model, model_with_pressure, exact_at_pressure,
    energy_breakdown, model_fingerprint,
)

ROOT = Path.cwd()
if not (ROOT / "configs" / "one_region.yaml").exists():
    ROOT = Path.cwd().parent
model, YEARS, CONFIG = load_model(ROOT / "configs" / "one_region.yaml")
CACHE_PATH = ROOT / "notebooks" / "data" / "quantum_cache_2033.json"
QCACHE = json.loads(CACHE_PATH.read_text())

# Centralized Aristotle notation/copy: update this single dictionary when theory wording evolves.
NOTATION = {
    "spin": r"$s_i=+1$ digital; $s_i=-1$ paper.",
    "bit": r"$x_i=0$ digital; $x_i=1$ paper; $s_i=1-2x_i$, equal to the $Z$ eigenvalue.",
    "field": r"$h_i(t)=A(t)-r_i$ (AI pressure minus resistance).",
    "energy": r"$E=-\\sum_{(i,j)\\in E}J_{ij}s_is_j-\\sum_i h_i s_i$; each edge occurs once.",
    "qubo": r"$E=C+\\sum_i(2h_i+2\\sum_jJ_{ij})x_i-4\\sum_{(i,j)}J_{ij}x_ix_j$, $C=-\\sum J-\\sum h$.",
    "cost": r"$H_C=-\\sum J_{ij}Z_iZ_j-\\sum h_iZ_i$.",
    "anneal": r"Annealing driver: $-\\sum X$; $|+\\rangle$ is its ground state.",
    "qaoa": r"QAOA convention: mixer $+\\sum X$, $|+\\rangle$ start (an eigenstate, not the mixer ground); $R_z=-2\\gamma h$, $R_{ZZ}=-2\\gamma J$, $R_x=2\\beta$.",
}

def pressure_from_year(year):
    return (year - 2026) * model.pressure_step

def title(text):
    return W.HTML(f"<h3 style='color:#173f5f;margin:8px 0'>{text}</h3>")

def caveat(text):
    return W.HTML(f"<div style='padding:9px;border-left:4px solid #f6ab6c;background:#fff8ef'>{text}</div>")"""),
        markdown("""## Notation and model card

<details><summary><b>Expand the math and glossary</b></summary>

- **Node:** industry in one region. A tie is mutual dependence, not causal proof.
- **Resistance $r_i$:** illustrative friction to digital adoption.
- **Pressure $A(t)$:** an illustrative external push; equilibrium is **not** an
  adoption-delay or switching-cost model.
- **Degeneracy:** more than one exact lowest-energy bitstring is a legitimate
  ambiguity. It creates a flip-year interval, not a numerical error.
- **Fragility:** a small gap can make a result sensitive; a nonzero energy
  error remains an error even when flagged as fragile.

</details>"""),
        code("""display(W.HTML("<br>".join([f"<b>{k.title()}</b>: {v}" for k, v in NOTATION.items()])))"""),
        markdown("""## 1. Tiny tangible example — Healthcare, Insurance, Pharma

**Predict first:** if Healthcare and Insurance are strongly tied, does matching
always mean an earlier digital flip? Try pressure with ties off, then ties on.
Matching pressure can also hold an eager node back; stronger ties align states,
not universally earlier adoption."""),
        code("""tiny_year = W.IntSlider(value=2033, min=2026, max=2040, description="Scenario year")
tiny_pressure = W.FloatSlider(value=0.49, min=0, max=1.1, step=.01, description="AI pressure A")
sync_tiny = W.Checkbox(value=True, description="lock A to challenge year")
r_health = W.FloatSlider(value=.75, min=0, max=1.1, step=.01, description="Healthcare r")
r_insure = W.FloatSlider(value=.55, min=0, max=1.1, step=.01, description="Insurance r")
r_pharma = W.FloatSlider(value=.60, min=0, max=1.1, step=.01, description="Pharma r")
j_hi = W.FloatSlider(value=.15, min=0, max=.35, step=.01, description="Health–Insurance J")
j_hp = W.FloatSlider(value=.105, min=0, max=.35, step=.01, description="Health–Pharma J")
tiny_predict = W.RadioButtons(options=["Ties always make flips earlier", "Ties align states; timing can go either way"],
                               description="Prediction")
tiny_reveal = W.Button(description="Reveal teaching answer", button_style="info")
tiny_reset = W.Button(description="Reset seeded scenario")
tiny_out = W.Output()

def sync_pressure(change=None):
    if sync_tiny.value:
        tiny_pressure.value = pressure_from_year(tiny_year.value) / model.unit
tiny_year.observe(sync_pressure, "value")
sync_tiny.observe(sync_pressure, "value")

def render_tiny(change=None):
    m = tiny_business_model(
        tuple(round(x.value * model.unit) for x in (r_health, r_insure, r_pharma)),
        round(j_hi.value * model.unit), round(j_hp.value * model.unit))
    p = round(tiny_pressure.value * model.unit)
    result = exact_at_pressure(m, p)
    states = np.array(list(itertools.product((-1, 1), repeat=3)), dtype=np.int8)
    energies = [m.energy(s, 2026) - 2 * p * 0 for s in states]  # replaced below using custom-pressure model
    pm = model_with_pressure(m, p)
    energies = [pm.energy(s, 2026) for s in states]
    breakdown = energy_breakdown(m, p, result.paper_state)
    labels = ["".join("D" if v == 1 else "P" for v in s) for s in states]
    with tiny_out:
        clear_output(wait=True)
        fig, ax = plt.subplots(figsize=(8, 3.1))
        ax.bar(labels, np.array(energies) / model.unit, color=["#2a9d8f" if e == result.energy else "#b8c4ce" for e in energies])
        ax.axhline(result.energy/model.unit, color="#e76f51", ls="--", label="exact minimum")
        ax.set(ylabel="absolute energy", title="All eight tiny-system states (D=digital, P=paper)")
        ax.legend(); plt.show()
        state_words = ", ".join(f"{n}: {'digital' if s==1 else 'paper'}" for n,s in zip(m.names, result.paper_state))
        print(f"Exact canonical state: {state_words}")
        print(f"Energy terms: ties={breakdown['tie_term']:.3f}, local preference={breakdown['local_preference_term']:.3f}, total={breakdown['total_energy']:.3f}")
        print("Green bars are exact minima. If there are several, the paper-tie canonical state is displayed.")

def reveal_tiny(_):
    answer = "Correct: ties align states; they can advance a flip or delay an eager industry surrounded by paper partners."
    display(caveat(answer + " At A=r with ties off, paper and digital are exactly tied."))

def reset_tiny(_):
    for widget, value in [(tiny_year,2033),(r_health,.75),(r_insure,.55),(r_pharma,.60),(j_hi,.15),(j_hp,.105)]:
        widget.value=value
    sync_tiny.value=True; sync_pressure()

for widget in [tiny_pressure,r_health,r_insure,r_pharma,j_hi,j_hp]:
    widget.observe(render_tiny, "value")
tiny_reveal.on_click(reveal_tiny); tiny_reset.on_click(reset_tiny)
sync_pressure(); render_tiny()
tiny_controls = W.VBox([W.HBox([tiny_year,tiny_pressure,sync_tiny,tiny_reset]), W.HBox([r_health,r_insure,r_pharma]), W.HBox([j_hi,j_hp]), tiny_predict, tiny_reveal])
tiny_tab = W.VBox([title("Change one assumption; see every energy recompute"), tiny_controls, tiny_out])"""),
        markdown("""## 2. Full 20-industry network — equilibrium and counterfactuals

The heatmap recomputes the exact min-cut equilibrium. The intervention changes
one resistance in a model-based scenario; it is not causal evidence."""),
        code("""full_year = W.IntSlider(value=2033, min=2026, max=2040, description="Scenario year")
full_pressure = W.FloatSlider(value=.49, min=0, max=1.1, step=.01, description="AI pressure A")
full_sync = W.Checkbox(value=True, description="lock A to year")
tie_multiplier = W.FloatSlider(value=1., min=0, max=2, step=.05, description="Tie multiplier")
target = W.Dropdown(options=model.names, value="Healthcare", description="Intervene on")
delta_r = W.FloatSlider(value=0., min=0, max=.4, step=.01, description="Lower r by")
full_predict = W.RadioButtons(options=["More ties always means earlier", "More ties means more alignment, not a universal earlier flip"],
                              description="Prediction")
full_reveal = W.Button(description="Reveal answer", button_style="info")
full_reset = W.Button(description="Reset")
full_out = W.Output()

def sync_full(change=None):
    if full_sync.value:
        full_pressure.value = pressure_from_year(full_year.value) / model.unit
full_year.observe(sync_full, "value"); full_sync.observe(sync_full, "value")

def render_full(change=None):
    ties = np.rint(model.ties * tie_multiplier.value).astype(np.int64)
    resist = model.resistance.copy(); index = model.names.index(target.value)
    resist[index] -= round(delta_r.value * model.unit)
    scenario = IsingModel(model.names, resist, ties, model.pressure_step, model.unit)
    p = round(full_pressure.value * model.unit)
    now = exact_at_pressure(scenario, p)
    # Fifteen cheap exact min-cuts are intentional: this is not a quantum re-run.
    schedule = {y: mincut(scenario, y).paper_state for y in YEARS}
    matrix = np.array([schedule[y] for y in YEARS]).T
    no_ties = IsingModel(scenario.names, scenario.resistance, np.zeros_like(scenario.ties), scenario.pressure_step, scenario.unit)
    no_ties_now = exact_at_pressure(no_ties, p)
    with full_out:
        clear_output(wait=True)
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 7), gridspec_kw={"width_ratios":[1.6,1]})
        ax1.imshow(matrix, aspect="auto", cmap="RdYlGn", vmin=-1, vmax=1)
        ax1.set(title="Exact yearly equilibrium: paper → digital", xlabel="year", ylabel="industry",
                xticks=range(0, len(YEARS), 2), xticklabels=list(YEARS)[::2],
                yticks=range(model.n), yticklabels=model.names)
        now_colors=["#2a9d8f" if s==1 else "#e76f51" for s in now.paper_state]
        ax2.barh(model.names, now.paper_state, color=now_colors)
        ax2.set(xlim=(-1.15,1.15), title=f"Current exact state at A={p/model.unit:.2f}")
        plt.tight_layout(); plt.show()
        changed = [n for n,a,b in zip(model.names, now.paper_state, no_ties_now.paper_state) if a != b]
        print("Network vs no-ties at this pressure differs for:", ", ".join(changed) if changed else "no industries")
        print(f"Intervention: lower {target.value} resistance by {delta_r.value:.2f}; this is a model scenario, not causal evidence.")

def reveal_full(_):
    display(caveat("Correct: stronger positive ties favor matching. They can pull a paper node forward or hold an eager node back; they do not universally make flips earlier."))
def reset_full(_):
    full_year.value=2033; full_sync.value=True; sync_full(); tie_multiplier.value=1.; target.value="Healthcare"; delta_r.value=0.
for widget in [full_pressure,tie_multiplier,target,delta_r]:
    widget.observe(render_full, "value")
full_reveal.on_click(reveal_full); full_reset.on_click(reset_full)
sync_full(); render_full()
full_tab = W.VBox([title("Explore ties, no ties, and a resistance intervention"), W.HBox([full_year,full_pressure,full_sync,full_reset]), W.HBox([tie_multiplier,target,delta_r]), full_predict, full_reveal, full_out])"""),
        markdown("""## 3. Circuit and sampled evidence

The quantum panel uses a **cached baseline Aer DQA result** only. Changing
model sliders does not silently resimulate it; a visible stale warning appears.
Imported qBraid counts are a separate workflow and are never labelled Aer."""),
        code("""quantum_year = W.IntSlider(value=2033, min=2026, max=2040, description="Cached year")
shot_budget = W.IntSlider(value=4096, min=50, max=8000, step=50, description="What-if shots")
mixer_angle = W.FloatSlider(value=.0, min=-3.14, max=3.14, step=.05, description="QAOA β what-if")
quantum_out = W.Output()

def render_quantum(change=None):
    expected_year = QCACHE["year"]
    baseline_controls = (
        full_year.value == expected_year
        and round(full_pressure.value, 2) == round(pressure_from_year(expected_year) / model.unit, 2)
        and tie_multiplier.value == 1.
        and delta_r.value == 0.
    )
    is_fresh = quantum_year.value == expected_year and baseline_controls and model_fingerprint(model) == QCACHE["model_fingerprint"]
    with quantum_out:
        clear_output(wait=True)
        display(caveat(
            f"Cached source: {QCACHE['source_label']}; p={QCACHE['p']}, T={QCACHE['total_time']}, shots={QCACHE['shots']}. "
            + ("Cache matches baseline controls." if is_fresh else "STALE: controls/year differ; no quantum simulation has been run for this setting.")))
        if not is_fresh:
            print("Return to 2033, A=0.49, tie multiplier=1 and no resistance intervention to inspect the cached histogram, or export new QASM for an authorized external run.")
            return
        hist = QCACHE["energy_histogram"]
        fig, ax = plt.subplots(figsize=(9,3.2))
        xs=np.array([float(k) for k in hist]); ys=np.array([hist[k] for k in hist])
        ax.bar(xs, ys, width=max(.01,(xs.max()-xs.min())/45), color="#457b9d")
        ax.axvline(QCACHE["exact_energy_model_units"], color="#e63946", ls="--", label="exact minimum")
        ax.set(title="Cached raw Aer samples by absolute energy", xlabel="energy (model units)", ylabel="shots")
        ax.legend(); plt.show()
        pground=QCACHE["ground_shot_probability"]
        chance=1-(1-pground)**shot_budget.value
        print(f"Mode energy error: {QCACHE['modal_energy_error_model_units']:.3f}; best measured error: {QCACHE['best_energy_error_model_units']:.3f}")
        print(f"Expected sampled energy: {QCACHE['expected_sampled_energy_model_units']:.3f}; exact energy: {QCACHE['exact_energy_model_units']:.3f}.")
        print(f"Probability any optimum in cached distribution: {pground:.3%}; with {shot_budget.value} independent shots: {chance:.3%}.")
        print("More shots improve the chance of observing an optimum; they do not change the underlying distribution.")
        print(f"QAOA mixer reminder: β={mixer_angle.value:.2f} is a teaching what-if only. No QAOA or DQA job runs when it changes.")
        print("DQA uses driver −ΣX (|+> ground). Standard QAOA uses mixer +ΣX (|+> is an eigenstate, not its ground).")
        comparison=QCACHE["sweep_comparison"]
        fig, ax = plt.subplots(figsize=(5.5,3.2))
        for label, values in comparison.items():
            ax.scatter(values["mean_energy_error_model_units"], values["flip_year_mismatch_count"], s=80, label=label)
            ax.annotate(label, (values["mean_energy_error_model_units"], values["flip_year_mismatch_count"]), xytext=(4,4), textcoords="offset points")
        ax.set(title="Energy error vs business flip-year mismatch", xlabel="mean energy error", ylabel="# flip-year mismatches")
        ax.legend(); plt.show()

for widget in [quantum_year,shot_budget,mixer_angle]:
    widget.observe(render_quantum, "value")
for widget in [full_year,full_pressure,tie_multiplier,delta_r]:
    widget.observe(render_quantum, "value")
render_quantum()
quantum_tab=W.VBox([title("Exact vs SA vs cached quantum sampling"), W.HBox([quantum_year,shot_budget,mixer_angle]), quantum_out,
                    caveat("Reported baseline: 12/15 DQA modal matches and 15/15 best-of-4096 Aer samples. This is simulator evidence, not hardware performance or speedup.")])"""),
        markdown("""## 4. qBraid results handoff

The dashboard does not call a provider. To score a submitted qBraid result,
save raw counts and use the repository command:

```bash
python -m paperflip.cli score-qbraid \\
  --manifest artifacts/qbraid_dqa_2033_20q.manifest.json \\
  --counts provider_counts.json
```

Keep imported qBraid outcomes labelled **qBraid imported**; keep Aer outcomes
labelled **Aer cached**; label actual hardware separately. Check entitlement,
transpilation, and billing before any future submission."""),
        code("""# Headless callback smoke: this exercises real widget observers without any remote call.
import os
if os.environ.get("PAPERFLIP_DASHBOARD_SMOKE") == "1":
    original_pressure = tiny_pressure.value
    tiny_pressure.value = round(original_pressure + .01, 2)
    tiny_pressure.value = original_pressure
    original_tie = tie_multiplier.value
    tie_multiplier.value = .75
    tie_multiplier.value = original_tie
    quantum_year.value = 2034  # intentionally renders the stale-cache warning
    quantum_year.value = 2033  # returns to the cached baseline
    assert "cache" in QCACHE["source_label"].lower()
    print("Widget callbacks exercised: tiny, full-network, and cache-staleness views.")"""),
    ]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    nbf.write(nb, OUT)


if __name__ == "__main__":
    build()
