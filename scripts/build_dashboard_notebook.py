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
        code("""# Deterministic notebook bootstrap — this cell never installs or downloads packages.
from pathlib import Path
import importlib.util, sys

DASHBOARD_SOURCE_VERSION = "pinned-artifacts-v1-2026-11-07"
ROOT = Path.cwd()
if not (ROOT / "pyproject.toml").exists():
    ROOT = ROOT.parent
SRC = ROOT / "src"
if not (ROOT / "pyproject.toml").exists() or not SRC.exists():
    raise RuntimeError("Open this notebook from the repository's notebooks/ directory or repository root.")
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))  # source bootstrap only; no package install/network action
missing = [name for name in ("numpy", "matplotlib", "networkx", "yaml", "ipywidgets", "qiskit", "qiskit_aer")
           if importlib.util.find_spec(name) is None]
if missing:
    raise RuntimeError(
        "Missing kernel packages: " + ", ".join(missing) +
        '. In a separate user-approved cell run: %pip install -e "{ROOT}[dashboard,quantum,dev]" '
        "then restart the kernel. This notebook never installs packages during Run All."
    )
print(f"PaperFlip dashboard source version: {DASHBOARD_SOURCE_VERSION}")
print(f"Repository root: {ROOT}")
# In qBraid Lab, explicitly install only when you choose to:
# %pip install -e "{ROOT}[dashboard,quantum,dev]"
# Then Kernel → Restart Kernel and Run All Cells. No deployment is claimed."""),
        code("""from __future__ import annotations
from pathlib import Path
import itertools, json, threading
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
from matplotlib.patches import Patch
import ipywidgets as W
from IPython.display import display, Markdown, HTML, Image, clear_output

from paperflip.model import load_model, IsingModel
from paperflip.exact import mincut, flip_intervals
from paperflip.solvers import simulated_annealing
from paperflip.dashboard import (
    tiny_business_model, model_with_pressure, exact_at_pressure,
    energy_breakdown, model_fingerprint,
)
from paperflip.region_views import nested_regions, compute_region_view
model, YEARS, CONFIG = load_model(ROOT / "configs" / "one_region.yaml")
PINNED_DQA_PATH = ROOT / "artifacts" / "dashboard_pins" / "dqa_2033_aer_8000_seed20264139.json"
PINNED_DQA_PNG = ROOT / "artifacts" / "dashboard_pins" / "dqa_2033_aer_8000_seed20264139.png"
PINNED_QAOA_PATH = ROOT / "artifacts" / "qaoa_yearly_probability_pacific_nw.json"
PINNED_QAOA_PNG = ROOT / "artifacts" / "qaoa_yearly_probability_pacific_nw.png"
REGION_CACHE_PATH = ROOT / "notebooks" / "data" / "independent_region_views_2033.json"
REGION_PRECOMPUTED = json.loads(REGION_CACHE_PATH.read_text())

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
    return W.HTML(f"<h3 style='color:#0b4f78;background:#f3f9fc;padding:7px;margin:8px 0'>{text}</h3>")

def caveat(text):
    return W.HTML(f"<div style='padding:9px;border-left:4px solid #b45309;background:#fff8ef;color:#202124 !important;line-height:1.5'>{text}</div>")"""),
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
        ax.legend(); plt.show(); plt.close(fig)
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
        paper_red, digital_blue = "#b65b5b", "#5b7fa3"
        binary_states = ((matrix + 1) // 2).astype(int)  # 0=paper s=-1, 1=digital s=+1
        ax1.imshow(binary_states, aspect="auto", cmap=ListedColormap([paper_red, digital_blue]),
                   vmin=0, vmax=1)
        ax1.set(title="Exact yearly equilibrium: paper → digital", xlabel="year", ylabel="industry",
                xticks=range(0, len(YEARS), 2), xticklabels=list(YEARS)[::2],
                yticks=range(model.n), yticklabels=model.names)
        ax1.legend(handles=[Patch(facecolor=paper_red, label="paper (s=-1)"),
                            Patch(facecolor=digital_blue, label="digital (s=+1)")],
                   loc="upper right", fontsize=8)
        now_colors=[digital_blue if s==1 else paper_red for s in now.paper_state]
        ax2.barh(model.names, now.paper_state, color=now_colors)
        ax2.set(xlim=(-1.15,1.15), title=f"Current exact state at A={p/model.unit:.2f}",
                xlabel="paper (−1) ← state → digital (+1)")
        ax2.legend(handles=[Patch(facecolor=paper_red, label="paper (s=-1)"),
                            Patch(facecolor=digital_blue, label="digital (s=+1)")],
                   loc="lower right", fontsize=8)
        plt.tight_layout(); plt.show(); plt.close(fig)
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
        markdown("""## 3. Fixed saved local-Aer DQA evidence

This panel always displays one committed, read-only 2033 baseline: the
illustrative one-region configuration, 8,000 Aer shots, seed 20264139, 40
Trotter steps, normalized time 20. It does not respond to model controls and
never runs a solver in the notebook."""),
        code("""pinned_dqa_out = W.Output()

def render_pinned_dqa():
    with pinned_dqa_out:
        clear_output(wait=True)
        if not PINNED_DQA_PATH.exists() or not PINNED_DQA_PNG.exists():
            display(caveat("Pinned DQA artifact is missing. This notebook will not regenerate it. "
                           "From a clean repository checkout run: .venv/bin/python scripts/build_pinned_dashboard_artifacts.py"))
            return
        record = json.loads(PINNED_DQA_PATH.read_text())
        raw, exact, algorithm = record["raw_result"], record["exact_same_graph"], record["algorithm"]
        display(caveat("Source: fixed saved local CPU/Qiskit Aer DQA artifact—not a new run, not qBraid, and not hardware. "
                       "Interactive model controls elsewhere do not alter this pinned baseline."))
        display(Image(filename=str(PINNED_DQA_PNG)))
        print(f"Generated {record['created_at_utc']} | baseline year={record['model']['year']} | model={record['model']['fingerprint']}")
        print(f"{algorithm['shots']} shots | seed={algorithm['seed']} | p={algorithm['p']} | T={algorithm['normalized_total_time']} | CPU={raw['cpu_seconds']:.2f}s")
        print(f"Expected energy={raw['expected_energy_model_units']:.3f}; mode error={raw['modal_energy_error_int']/model.unit:.3f}; "
              f"best measured error={raw['best_measured_energy_error_int']/model.unit:.3f}; exact optimum probability={raw['ground_shot_probability']:.3%}.")
        print("Raw counts, exact same-graph reference, and provenance are committed beside this static panel.")

render_pinned_dqa()
quantum_tab=W.VBox([title("Fixed 2033 local Aer DQA baseline"), pinned_dqa_out,
                    caveat("This is fixed saved simulator evidence, not a forecast, hardware result, speedup claim, or interactive what-if. "
                           "The other teaching panels remain interactive.")])"""),
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
        markdown("""## 4. One, two, and five independent regions

These are **separate 20-node simulations** of the same industry topology,
never a 40- or 100-node circuit. Synthetic region shifts/noise are nested from
one stable seed; no cross-region ties exist in this quantum scenario. The
exact min-cut shown uses the same independent graph as the selected circuit."""),
        markdown(r"""### p=1 QAOA: physics and notation

For the selected independent region, \(x_i=0\) means **digital** and
\(s_i=+1\); \(x_i=1\) means paper and \(s_i=-1\), so
\(s_i=1-2x_i\). With \(h_i(t)=A(t)-r_i\),

\[
H_C=-\sum_{(i,j)}J_{ij}Z_iZ_j-\sum_i h_i(t)Z_i,\qquad H_M=+\sum_iX_i.
\]

The general \(p\)-layer recurrence is
\[
|\psi_0\rangle=H^{\otimes n}|0\ldots0\rangle,\qquad
|\psi_\ell\rangle=e^{-i\beta_\ell H_M}e^{-i\gamma_\ell H_C}|\psi_{\ell-1}\rangle.
\]
This dashboard's current regional calculation is explicitly **p=1**—one cost
block and one \(+\sum X\) mixer block—not the multi-layer architecture drawn
in the generic diagram. It begins in the equal-amplitude superposition:
each 20-qubit basis state has \(P(z)=2^{-20}\).

For a computational-basis configuration \(z\), the cost block changes
\(a_z\mapsto e^{-i\gamma E(z)}a_z\): it changes phase but not
\(|a_z|^2\). The mixer applies \(R_x(2\beta)\) on each qubit, so final
amplitudes are interference sums over transitions—not a greedy energy rule.
Measurement gives \(P(z)=|a_z|^2\), while the bounded classical angle search
minimizes \(\sum_zP(z)E(z)\). Exact ferromagnetic min-cut remains an
independent benchmark; optimum probability and industry marginals are
different quantities.

With model-energy units used here, the cost gates are
\(R_z(-2\gamma h_i)\) and \(R_{ZZ}(-2\gamma J_{ij})\); a standard
\(R_{ZZ}\) decomposition is CX–\(R_z\)–CX. \(\gamma\) is therefore in
radians per the normalized model-energy scale used by the circuit. This is
not DQA: the saved DQA histogram uses annealing driver \(-\sum_iX_i\), whereas
standard QAOA here uses mixer \(+\sum_iX_i\)."""),
        code(r"""region_count = W.ToggleButtons(options=[1,2,5], value=1, description="Regions shown")
region_select = W.Dropdown(description="Selected region")
region_year = W.IntSlider(value=2033, min=2026, max=2040, description="Year")
region_scenario = W.Dropdown(options=["Independent same-20", "Independent no-ties"], description="Scenario")
region_compute = W.Button(description="Compute selected 20-node view", button_style="warning")
region_reset = W.Button(description="Reset cached view")
region_out = W.Output()
region_memory_cache = {view["scenario_key"]: view for view in REGION_PRECOMPUTED["views"]}

def set_region_options(change=None):
    scenarios = nested_regions(model, seed=20261106, count=region_count.value)
    region_select.options = [scenario.name for scenario in scenarios]
    if region_select.value not in region_select.options:
        region_select.value = region_select.options[0]

def selected_region_scenario():
    scenarios = nested_regions(model, seed=20261106, count=region_count.value)
    selected = next(s for s in scenarios if s.name == region_select.value)
    if region_scenario.value == "Independent no-ties":
        selected = type(selected)(selected.name, IsingModel(selected.model.names, selected.model.resistance,
            np.zeros_like(selected.model.ties), selected.model.pressure_step, selected.model.unit),
            selected.regional_shift_int, selected.noise_int)
    return selected

def lookup_region_view(compute=False):
    selected = selected_region_scenario()
    probe = compute_region_view if compute else None
    # Keys include region model, year and bounded objective grid; no stale reuse.
    from paperflip.region_views import scenario_key
    key = scenario_key(selected, region_year.value, (.2,.6,1.0), (.2,.5,.8))
    if key in region_memory_cache:
        return region_memory_cache[key], False
    if not compute:
        return None, True
    view = compute_region_view(selected, region_year.value)
    region_memory_cache[key] = view
    return view, False

def render_region(change=None):
    view, stale = lookup_region_view(compute=False)
    with region_out:
        clear_output(wait=True)
        display(caveat("Independent regional quantum scenario: exactly one 20-node circuit is selected. "
                       "No 40/100-node circuit and no inter-region tie exists. CPU simulator only; not qBraid/hardware."))
        if stale:
            print("STALE / not precomputed for these selectors. Click ‘Compute selected 20-node view’ for an explicit local CPU recompute; sliders never auto-run it.")
            return
        records = view["fixed_configurations"]
        labels = [f"C{index+1:02d}" for index in range(len(records))]
        exact_mask = np.array([item["is_exact_minimum"] for item in records])
        fig, axes = plt.subplots(2, 2, figsize=(12,7))
        for stage, axis, color in [("initial",axes[0,0],"#8ecae6"),("cost_only",axes[0,1],"#8ecae6"),("post_mixer",axes[1,0],"#457b9d")]:
            values=np.array([item[f"{stage}_probability"] for item in records])
            axis.bar(range(len(records)), values, color=color)
            axis.scatter(np.where(exact_mask)[0], values[exact_mask], color="#e63946", marker="*", s=80, label="exact minimum")
            axis.set(title=f"{stage.replace('_',' ')} P=|amplitude|²; included={view['stages'][stage]['included_mass']:.3e}, omitted={view['stages'][stage]['omitted_mass']:.3e}",
                     xticks=range(len(records)), xticklabels=labels, ylabel="probability")
            axis.tick_params(axis="x", rotation=65); axis.legend(loc="upper right")
        phases=np.ma.masked_invalid(np.array([[item["cost_only_phase_relative_radians"] if item["cost_only_phase_relative_radians"] is not None else np.nan for item in records]]))
        image=axes[1,1].imshow(phases, cmap="twilight", vmin=-np.pi, vmax=np.pi, aspect="auto")
        axes[1,1].set(title="Cost-only relative phase (cyclic; zero-amplitude masked)", yticks=[], xticks=range(len(records)), xticklabels=labels)
        axes[1,1].tick_params(axis="x", rotation=65); fig.colorbar(image, ax=axes[1,1], label="radians")
        plt.tight_layout(); plt.show(); plt.close(fig)
        fig, ax = plt.subplots(figsize=(10,2.8))
        matrix=np.array([view["stages"][stage]["sector_digital_marginals"] for stage in ["initial","cost_only","post_mixer"]])
        im=ax.imshow(matrix, vmin=0, vmax=1, cmap="viridis", aspect="auto")
        ax.set(yticks=range(3), yticklabels=["initial","cost only","post mixer"], xticks=range(model.n), xticklabels=model.names,
               title="Sector marginals: P(industry is digital)")
        ax.tick_params(axis="x", rotation=70, labelsize=7); fig.colorbar(im, ax=ax); plt.tight_layout(); plt.show(); plt.close(fig)
        mode=max(records, key=lambda item: item["post_mixer_probability"])
        print(f"{view['region']} | year {view['year']} | objective grid chose γ={view['optimization']['gamma']}, β={view['optimization']['beta']}.")
        print(f"CPU simulator time={view['cpu_seconds']:.2f}s. Exact optimum probability={view['exact_optimum_probability_post_mixer']:.3e}; "
              f"mode energy={mode['energy_model_units']:.3f}. Best sample: not computed (this is an exact statevector distribution, not sampled shots).")
        print("Bars show one fixed selected configuration subset only; included/omitted mass is relative to all 2²⁰ configurations and bars are never renormalized.")
        print("Post-cost probability invariance is expected: cost-only phases change amplitudes’ phase, not computational-basis probabilities. Phase colors are cyclic relative phases, not probabilities.")
        table_rows = "".join(
            f"<tr><td>{label}</td><td><code>{item['bitstring_c_n_minus_1_to_c_0']}</code></td><td>{item['energy_model_units']:.3f}</td>"
            f"<td>{'yes' if item['is_exact_minimum'] else 'no'}</td></tr>"
            for label, item in zip(labels, records)
        )
        display(HTML("<details><summary>Selected configuration IDs (same set in all three stage plots)</summary>"
                     "<table><tr><th>ID</th><th>full c[n−1]…c[0] bitstring</th><th>energy</th><th>exact minimum</th></tr>"
                     f"{table_rows}</table></details>"))

def compute_region(_):
    view, _ = lookup_region_view(compute=True)
    render_region()
    render_qaoa_walkthrough()

def reset_region(_):
    region_count.value=1; set_region_options(); region_select.value="Pacific NW"; region_year.value=2033; region_scenario.value="Independent same-20"; render_region()

walkthrough_stage = W.ToggleButtons(
    options=["Hadamards: uniform start", "Cost phase", "Mixer interference", "Measurement and objective"],
    value="Hadamards: uniform start", description="p=1 stage"
)
walkthrough_out = W.Output()

def draw_p1_circuit(highlight):
    blocks = [
        ("Hadamards", .12, "#bfc7cf"), ("Cost $e^{-iγH_C}$", .34, "#b28af0"),
        ("Mixer $e^{-iβH_M}$", .57, "#d1b5f7"), ("Measure", .82, "#76a5ea"),
    ]
    fig, ax = plt.subplots(figsize=(11, 2.9))
    for y in np.linspace(.18, .82, 6):
        ax.plot([.02,.95], [y,y], color="#4e5660", lw=1)
    for name, x, color in blocks:
        active = name.startswith(highlight)
        rect = plt.Rectangle((x,.1), .14, .8, facecolor=color, edgecolor="#17212b",
                             linewidth=3 if active else 1.2, alpha=1 if active else .55)
        ax.add_patch(rect)
        ax.text(x+.07, .5, name, ha="center", va="center", fontsize=10)
    ax.text(.02, .96, "20 logical wires abstracted (not a 20-wire gate-level drawing)", fontsize=9)
    ax.text(.41, .02, "p=1: exactly one cost block and one mixer block", ha="center", fontsize=9)
    ax.set(xlim=(0,1), ylim=(0,1)); ax.axis("off")
    plt.show(); plt.close(fig)

def render_qaoa_walkthrough(change=None):
    view, stale = lookup_region_view(compute=False)
    with walkthrough_out:
        clear_output(wait=True)
        display(caveat("This walkthrough only reads the cached/explicitly computed selected-region statevector view. "
                       "Changing the stage selector never invokes a solver, submits a job, or changes the fixed saved DQA/QAOA evidence above."))
        if stale:
            print("No matching selected-region stage data is cached. Use the separate ‘Compute selected 20-node view’ button; this stage selector does not compute.")
            return
        selected = walkthrough_stage.value
        if selected.startswith("Hadamards"):
            stage, block = "initial", "Hadamards"
            explanation = (r"**Initial state:** \(H^{\otimes20}|0\ldots0\rangle=|+\rangle^{\otimes20}\). "
                           r"Every basis amplitude is \(1/\sqrt{2^{20}}\), so every configuration has \(P=2^{-20}\).")
        elif selected.startswith("Cost"):
            stage, block = "cost_only", "Cost"
            explanation = (r"**Cost phase:** \(a_z\rightarrow e^{-i\gamma E(z)}a_z\). "
                           r"This changes relative phase (shown separately, relative to a fixed reference) but preserves each computational-basis probability.")
        elif selected.startswith("Mixer"):
            stage, block = "post_mixer", "Mixer"
            explanation = (r"**Mixer:** \(R_x(2\beta)=e^{-i\beta X}\) on each qubit implements \(H_M=+\sum_iX_i\). "
                           r"Amplitudes interfere as sums over bit-flip transition paths; this is not a greedy local energy update.")
        else:
            stage, block = "post_mixer", "Measure"
            explanation = (r"**Measurement/objective:** \(P(z)=|a_z|^2\); the bounded 3×3 classical grid selected angles by minimizing "
                           r"\(\langle H_C\rangle=\sum_zP(z)E(z)\). Exact min-cut is an independent benchmark, not injected into the statevector.")
        draw_p1_circuit(block)
        display(Markdown(explanation))
        records = view["fixed_configurations"]
        labels = [f"C{index+1:02d}" for index in range(len(records))]
        values = np.array([item[f"{stage}_probability"] for item in records])
        exact_mask = np.array([item["is_exact_minimum"] for item in records])
        fig, ax = plt.subplots(figsize=(10,3.3))
        ax.bar(range(len(records)), values, color="#457b9d")
        ax.scatter(np.where(exact_mask)[0], values[exact_mask], color="#e63946", marker="*", s=80, label="exact minimum")
        mass = view["stages"][stage]
        ax.set(title=f"Actual selected {stage.replace('_',' ')} probabilities; included={mass['included_mass']:.3e}, omitted={mass['omitted_mass']:.3e}",
               xticks=range(len(records)), xticklabels=labels, ylabel="P(configuration)")
        ax.tick_params(axis="x", rotation=0); ax.legend(); plt.tight_layout(); plt.show(); plt.close(fig)
        if stage == "cost_only":
            phases = [item["cost_only_phase_relative_radians"] for item in records]
            print("Relative phases (radians; fixed reference; None means numerically zero amplitude):", phases)
        print(f"Actual view: {view['region']}, year {view['year']}, p=1; bounded objective chose γ={view['optimization']['gamma']}, β={view['optimization']['beta']}.")
        print("The selected C01… subset is fixed across stages and not renormalized; omitted probability belongs to the other configurations in the full 2²⁰ state space.")

region_count.observe(set_region_options,"value")
for widget in [region_select,region_year,region_scenario]:
    widget.observe(render_region,"value")
    widget.observe(render_qaoa_walkthrough,"value")
walkthrough_stage.observe(render_qaoa_walkthrough, "value")
region_compute.on_click(compute_region); region_reset.on_click(reset_region)
pinned_qaoa_out = W.Output()

def render_pinned_qaoa():
    with pinned_qaoa_out:
        clear_output(wait=True)
        if not PINNED_QAOA_PATH.exists() or not PINNED_QAOA_PNG.exists():
            display(caveat("Pinned yearly QAOA artifact is missing. This notebook will not regenerate it. "
                           "From a clean repository checkout run: .venv/bin/python scripts/render_qaoa_year_heatmap_preview.py"))
            return
        result = json.loads(PINNED_QAOA_PATH.read_text())
        display(caveat("Source: fixed saved local CPU statevector standard-p1-QAOA baseline—not a new run, not qBraid, and not hardware. "
                       "It is the Pacific NW independent 20-node illustrative scenario, anchored at 2033 and swept across 2026–2040. "
                       "Each cell is P(bit 0 = digital), not a measured-shot or empirical adoption probability."))
        display(Image(filename=str(PINNED_QAOA_PNG)))
        algorithm = result["algorithm"]
        print(f"{result['region']} | model={result['model_fingerprint']} | region seed={result['region_seed']} | CPU={result['cpu_seconds']:.2f}s")
        print(f"15 years; bounded expected-energy grid γ={algorithm['gamma_grid']}, β={algorithm['beta_grid']}; "
              "per-year angles, expected energies, exact references, and runtimes are committed in the JSON.")
        print("This pinned heatmap deliberately remains unchanged when the independent-region stage controls below change.")

render_pinned_qaoa()
set_region_options()  # defer plotting until the Tab is attached and visible
render_qaoa_walkthrough()
region_tab=W.VBox([title("Compare one, two and five regions without pretending they are one large quantum circuit"),
                   title("Fixed saved QAOA yearly probability baseline"), pinned_qaoa_out,
                   caveat("The static baseline above is deliberately detached from the controls below. These controls only affect the separate interactive, selected-region stage demonstration."),
                   title("Interactive p=1 QAOA circuit and statevector walk-through"), walkthrough_stage, walkthrough_out,
                   W.HBox([region_count,region_select,region_year,region_scenario,region_compute,region_reset]),region_out])"""),
        code("""# Headless callback smoke: this exercises real widget observers without any remote call.
import os
dashboard_tabs = W.Tab(children=[tiny_tab, full_tab, quantum_tab, region_tab])
for index, label in enumerate(["1. Tiny tangible example", "2. 20-industry network", "3. Cached quantum evidence", "4. Independent regions"]):
    dashboard_tabs.set_title(index, label)
dashboard_tabs.selected_index = int(os.environ.get("PAPERFLIP_DASHBOARD_TAB", "0"))
display(dashboard_tabs)
def activate_region_on_first_display(change=None):
    if dashboard_tabs.selected_index == 3:
        render_region()
        render_qaoa_walkthrough()
dashboard_tabs.observe(activate_region_on_first_display, "selected_index")
activate_region_on_first_display()
if os.environ.get("PAPERFLIP_DASHBOARD_SMOKE") == "1":
    # A widget Output can capture a callback exception without failing the
    # notebook cell. Render each tab in this fresh kernel and reject both
    # structured error outputs and textual tracebacks.
    def assert_output_clean(label, output):
        errors = [
            item for item in output.outputs
            if item.get("output_type") == "error"
            or "Traceback" in item.get("text", "")
        ]
        assert not errors, f"{label} widget output contains rendering errors: {errors}"

    for tab in range(len(dashboard_tabs.children)):
        dashboard_tabs.selected_index = tab
    render_full()  # direct Section 2 first-render/legend regression
    original_pressure = tiny_pressure.value
    tiny_pressure.value = round(original_pressure + .01, 2)
    tiny_pressure.value = original_pressure
    original_tie = tie_multiplier.value
    tie_multiplier.value = .75
    tie_multiplier.value = original_tie
    pinned_dqa_before = tuple(pinned_dqa_out.outputs)
    pinned_qaoa_before = tuple(pinned_qaoa_out.outputs)
    # These model changes drive the interactive panels only, never a solver or
    # stale state for either pinned artifact.
    full_pressure.value = round(full_pressure.value + .01, 2)
    full_pressure.value = round(full_pressure.value - .01, 2)
    assert tuple(pinned_dqa_out.outputs) == pinned_dqa_before
    assert tuple(pinned_qaoa_out.outputs) == pinned_qaoa_before
    region_count.value = 2
    region_select.value = "California"
    region_count.value = 1
    dashboard_tabs.selected_index = 3
    walkthrough_stage.value = "Cost phase"
    walkthrough_stage.value = "Mixer interference"
    walkthrough_stage.value = "Measurement and objective"
    walkthrough_stage.value = "Hadamards: uniform start"
    dashboard_tabs.selected_index = 0
    for label, output in [
        ("tiny", tiny_out), ("full-network", full_out), ("pinned DQA", pinned_dqa_out),
        ("regions", region_out), ("pinned yearly QAOA", pinned_qaoa_out), ("QAOA walkthrough", walkthrough_out),
    ]:
        assert_output_clean(label, output)
    assert PINNED_DQA_PATH.exists() and PINNED_QAOA_PATH.exists()
    print("Widget callbacks, pinned-artifact invariance, and all tab first activations passed without Output-captured rendering errors.")"""),
    ]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    nbf.write(nb, OUT)


if __name__ == "__main__":
    build()
