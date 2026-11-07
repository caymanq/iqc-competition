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
import itertools, json, threading
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
from matplotlib.patches import Patch
import ipywidgets as W
from IPython.display import display, Markdown, HTML, clear_output

from paperflip.model import load_model, IsingModel
from paperflip.exact import mincut, flip_intervals
from paperflip.solvers import simulated_annealing, _decode
from paperflip.dashboard import (
    tiny_business_model, model_with_pressure, exact_at_pressure,
    energy_breakdown, model_fingerprint,
)
from paperflip.region_views import nested_regions, compute_region_view
from paperflip.dashboard_runs import run_local_dqa_and_persist, latest_matching_run
from paperflip.qaoa_year_sweep import (
    DEFAULT_BETA_GRID, DEFAULT_GAMMA_GRID, compute_qaoa_year_sweep,
    latest_matching_qaoa_year_sweep, persist_qaoa_year_sweep,
)

ROOT = Path.cwd()
if not (ROOT / "configs" / "one_region.yaml").exists():
    ROOT = Path.cwd().parent
model, YEARS, CONFIG = load_model(ROOT / "configs" / "one_region.yaml")
CACHE_PATH = ROOT / "notebooks" / "data" / "quantum_cache_2033.json"
QCACHE = json.loads(CACHE_PATH.read_text())
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
        markdown("""## 3. Circuit and sampled evidence

The quantum panel uses a **cached baseline Aer DQA result** only. Changing
model sliders does not silently resimulate it; a visible stale warning appears.
Imported qBraid counts are a separate workflow and are never labelled Aer."""),
        code("""quantum_year = W.IntSlider(value=2033, min=2026, max=2040, description="Run year")
shot_budget = W.IntSlider(value=4096, min=50, max=8000, step=50, description="Run shots")
run_seed = W.BoundedIntText(value=20264139, min=0, max=2**31-1, description="Run seed")
run_selected = W.Button(description="Run selected year (local CPU)", button_style="warning")
run_status = W.HTML("<b style='color:#0b4f78'>Ready. Sliders do not run a simulation.</b>")
quantum_out = W.Output()
on_demand_runs = {}
run_lock = threading.Lock()

def current_quantum_model():
    ties = np.rint(model.ties * tie_multiplier.value).astype(np.int64)
    resist = model.resistance.copy()
    resist[model.names.index(target.value)] -= round(delta_r.value * model.unit)
    return IsingModel(model.names, resist, ties, model.pressure_step, model.unit)

def quantum_key(candidate):
    return (model_fingerprint(candidate), quantum_year.value, shot_budget.value, run_seed.value, 40, 20.0)

def display_histogram(hist, exact_energy, unit, title_text):
    fig, ax = plt.subplots(figsize=(9,3.2))
    xs=np.array(sorted(hist)); ys=np.array([hist[x] for x in xs])
    ax.bar(xs, ys, width=max(.01,(xs.max()-xs.min())/45), color="#457b9d")
    ax.axvline(exact_energy / unit, color="#e63946", ls="--", label="exact minimum")
    ax.set(title=title_text, xlabel="energy (model units)", ylabel="shots")
    ax.legend(); plt.show(); plt.close(fig)

def render_local_record(record, path):
    raw, exact = record["raw_result"], record["exact_same_graph"]
    candidate = current_quantum_model()
    histogram = {}
    for bitstring, count in raw["counts"].items():
        energy = candidate.energy(_decode(bitstring, candidate.n), quantum_year.value) / candidate.unit
        histogram[energy] = histogram.get(energy, 0) + count
    display_histogram(histogram, exact["energy_int"], candidate.unit, "New local Aer DQA raw samples (same graph/year exact reference)")
    print(f"NEW persisted local result: {path.name}")
    print(f"Expected energy={raw['expected_energy_model_units']:.3f}; mode error={raw['modal_energy_error_int']/candidate.unit:.3f}; "
          f"best measured error={raw['best_measured_energy_error_int']/candidate.unit:.3f}; exact optimum probability={raw['ground_shot_probability']:.3%}.")
    print(f"Actual sampling: {record['algorithm']['shots']} shots, seed={record['algorithm']['seed']}, CPU={raw['cpu_seconds']:.2f}s. "
          "Single-year runs do not imply flip-year error.")

def render_quantum(change=None):
    candidate = current_quantum_model()
    key = quantum_key(candidate)
    matching = on_demand_runs.get(key) or latest_matching_run(
        ROOT / "results" / "dashboard_runs", candidate, quantum_year.value, shot_budget.value,
        run_seed.value, 40, 20.0)
    baseline_controls = (
        quantum_year.value == QCACHE["year"] and tie_multiplier.value == 1. and delta_r.value == 0.
        and model_fingerprint(candidate) == QCACHE["model_fingerprint"] and shot_budget.value == QCACHE["shots"]
        and run_seed.value == QCACHE["seed"]
    )
    with quantum_out:
        clear_output(wait=True)
        if matching:
            display(caveat("Source: NEW local Aer DQA run saved with full counts/provenance. It is not qBraid or hardware."))
            render_local_record(*matching)
            return
        if baseline_controls:
            display(caveat(f"Source: CACHED local Aer baseline; p={QCACHE['p']}, T={QCACHE['total_time']}, shots={QCACHE['shots']}. "
                           "This is precomputed evidence, not a new run."))
            hist = {float(k): v for k,v in QCACHE["energy_histogram"].items()}
            display_histogram(hist, QCACHE["exact_energy_int"], model.unit, "Cached raw Aer samples by absolute energy")
            pground=QCACHE["ground_shot_probability"]
            print(f"Expected energy: {QCACHE['expected_sampled_energy_model_units']:.3f}; mode error: {QCACHE['modal_energy_error_model_units']:.3f}; "
                  f"best measured error: {QCACHE['best_energy_error_model_units']:.3f}; optimum probability: {pground:.3%}.")
            print("This is a complete baseline sweep cache, so its separate flip-year comparison is shown below.")
            comparison=QCACHE["sweep_comparison"]
            fig, ax = plt.subplots(figsize=(5.5,3.2))
            for label, values in comparison.items():
                ax.scatter(values["mean_energy_error_model_units"], values["flip_year_mismatch_count"], s=80, label=label)
                ax.annotate(label, (values["mean_energy_error_model_units"], values["flip_year_mismatch_count"]), xytext=(4,4), textcoords="offset points")
            ax.set(title="Complete-sweep energy vs flip-year mismatch", xlabel="mean energy error", ylabel="# flip-year mismatches")
            ax.legend(); plt.show(); plt.close(fig)
            return
        display(caveat("STALE / no matching local result. Changing year, ties, resistance, shots, seed, or algorithm parameters invalidates cache reuse. "
                       "Click Run selected year to create and save a new local CPU/Aer result."))
        print(f"The run uses A({quantum_year.value})={pressure_from_year(quantum_year.value)/model.unit:.2f} from the repository schedule and the current ties/resistance scenario.")
        print("DQA has no QAOA β control. Run shots are actual samples, not a what-if display. No flip-year metric is shown for a single-year run.")

def do_run(_):
    if run_lock.locked():
        return
    candidate = current_quantum_model()
    key = quantum_key(candidate)
    run_status.value = "<b style='color:#92400e'>Running local CPU/Aer DQA… controls are unchanged; no qBraid/provider task is being submitted.</b>"
    def worker():
        try:
            with run_lock:
                record, path = run_local_dqa_and_persist(candidate, quantum_year.value, shot_budget.value, run_seed.value,
                                                          ROOT / "results" / "dashboard_runs", p=40, total_time=20.0)
                on_demand_runs[key] = (record, path)
            run_status.value = f"<b style='color:#166534'>Saved new local run: {path.name}</b>"
        except Exception as exc:
            run_status.value = f"<b style='color:#b91c1c'>Run failed: {type(exc).__name__}: {exc}</b>"
        render_quantum()
    threading.Thread(target=worker, daemon=True).start()

for widget in [quantum_year,shot_budget,run_seed,full_year,full_pressure,tie_multiplier,target,delta_r]:
    widget.observe(render_quantum, "value")
run_selected.on_click(do_run)
render_quantum()
quantum_tab=W.VBox([title("Exact vs SA vs local Aer DQA results"), W.HBox([quantum_year,shot_budget,run_seed,run_selected]), run_status, quantum_out,
                    caveat("Cached Aer, new local Aer, imported qBraid counts, and hardware must remain distinct sources. "
                           "Reported baseline: 12/15 DQA modal matches and 15/15 best-of-4096 Aer samples; this is simulator evidence, not speedup.")])"""),
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
        code("""region_count = W.ToggleButtons(options=[1,2,5], value=1, description="Regions shown")
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
        labels = [item["bitstring_c_n_minus_1_to_c_0"][-8:] + "…" for item in records]
        exact_mask = np.array([item["is_exact_minimum"] for item in records])
        fig, axes = plt.subplots(2, 2, figsize=(12,7))
        for stage, axis, color in [("initial",axes[0,0],"#8ecae6"),("cost_only",axes[0,1],"#8ecae6"),("post_mixer",axes[1,0],"#457b9d")]:
            values=np.array([item[f"{stage}_probability"] for item in records])
            axis.bar(range(len(records)), values, color=color)
            axis.scatter(np.where(exact_mask)[0], values[exact_mask], color="#e63946", marker="*", s=80, label="exact minimum")
            axis.set(title=f"{stage.replace('_',' ')} P=|amplitude|²; included={view['stages'][stage]['included_mass']:.3f}, omitted={view['stages'][stage]['omitted_mass']:.3f}",
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
        print("Post-cost probability invariance is expected: cost-only phases change amplitudes’ phase, not computational-basis probabilities.")

def compute_region(_):
    view, _ = lookup_region_view(compute=True)
    render_region()

def reset_region(_):
    region_count.value=1; set_region_options(); region_select.value="Pacific NW"; region_year.value=2033; region_scenario.value="Independent same-20"; render_region()

region_count.observe(set_region_options,"value")
for widget in [region_select,region_year,region_scenario]:
    widget.observe(render_region,"value")
region_compute.on_click(compute_region); region_reset.on_click(reset_region)
year_sweep_compute = W.Button(description="Compute yearly probability heatmap (local CPU)", button_style="warning")
year_sweep_status = W.HTML("<b style='color:#0b4f78'>Yearly QAOA heatmap is not computed until requested.</b>")
year_sweep_out = W.Output()
year_sweep_memory, year_sweep_lock = {}, threading.Lock()

def year_sweep_key(selected):
    return (model_fingerprint(selected.model), selected.name, 20261106, tuple(YEARS),
            tuple(DEFAULT_GAMMA_GRID), tuple(DEFAULT_BETA_GRID))

def render_year_sweep(change=None):
    selected = selected_region_scenario()
    key = year_sweep_key(selected)
    result = year_sweep_memory.get(key)
    persisted = None
    if result is None:
        persisted = latest_matching_qaoa_year_sweep(
            ROOT / "results" / "qaoa_year_sweeps", selected.model, YEARS, region=selected.name,
            region_seed=20261106, gamma_grid=DEFAULT_GAMMA_GRID, beta_grid=DEFAULT_BETA_GRID,
        )
        if persisted:
            result, path = persisted
            year_sweep_memory[key] = result
    with year_sweep_out:
        clear_output(wait=True)
        display(caveat("Each cell is an exact local-statevector marginal P(bit_i=0): **digital**, because this notebook uses "
                       "x_i=0, s_i=+1 for digital. It is not a measured-shot estimate, empirical forecast, remote qBraid run, or hardware result. "
                       "Each of the 15 years independently optimizes a bounded 3×3 standard-p1-QAOA expected-energy grid on this one selected 20-node region."))
        if result is None:
            print("STALE / absent. Click ‘Compute yearly probability heatmap (local CPU)’ for the selected independent region/scenario. "
                  "Selectors never launch this 15-year calculation; only one selected region is computed.")
            return
        years = result["years"]
        probabilities = np.array([row["digital_probability_by_industry"] for row in result["rows"]]).T
        fig, ax = plt.subplots(figsize=(12, 7))
        image = ax.imshow(probabilities, vmin=0, vmax=1, cmap="viridis", aspect="auto")
        ax.set(title="QAOA digital probability by year — P(bit 0), not bit 1",
               xlabel="year", ylabel="industry", xticks=range(len(years)), xticklabels=years,
               yticks=range(selected.model.n), yticklabels=selected.model.names)
        for index, marker in enumerate(result["exact_flip_markers"]):
            early, late = marker["earliest_digital_year"], marker["latest_digital_year"]
            if marker["has_exact_degeneracy"]:
                left, right = years.index(marker["degenerate_years"][0]), years.index(marker["degenerate_years"][-1])
                ax.hlines(index, left, right, color="white", linewidth=1.5)
            if marker["never_digital_through_window"]:
                ax.scatter([len(years)-1], [index], marker=">", s=55, facecolors="none", edgecolors="white", linewidths=1.4)
            elif marker["already_digital_at_window_start"]:
                ax.scatter([0], [index], marker="<", s=55, color="white", linewidths=1.4)
            elif marker["degenerate_tipping_interval"]:
                left, right = years.index(early), years.index(late)
                ax.scatter([left, right], [index, index], marker="|", s=85, color="white", linewidths=1.5)
            else:
                ax.scatter([years.index(early)], [index], marker="x", s=32, color="white", linewidths=1.4)
        from matplotlib.lines import Line2D
        ax.legend(handles=[
            Line2D([0], [0], marker="x", color="white", linestyle="None", label="exact classical flip"),
            Line2D([0], [0], color="white", linewidth=1.5, label="exact degeneracy / flip-uncertainty range"),
            Line2D([0], [0], marker="<", color="white", linestyle="None", label="already digital at 2026"),
            Line2D([0], [0], marker=">", markerfacecolor="none", color="white", linestyle="None", label="never digital through 2040"),
        ], loc="upper right", fontsize=8, framealpha=.8)
        fig.colorbar(image, ax=ax, label="QAOA statevector P(industry is digital = bit 0)")
        plt.tight_layout(); plt.show(); plt.close(fig)
        angles = [(row["year"], row["selected_gamma"], row["selected_beta"]) for row in result["rows"]]
        print(f"{result['region']} | 15 independent same-20-node QAOA circuits | CPU={result['cpu_seconds']:.2f}s.")
        if persisted:
            print(f"Loaded matching persisted local result: {path.name}")
        print("Per-year selected (year, γ, β):", angles)
        print("Exact min-cut markers use extremal ground states: lines are legitimate degeneracy intervals; < and > denote left/right censoring.")
        print("Expected QAOA energy and exact reference are retained in persisted provenance; no probability is forced to match the exact solution.")

def do_year_sweep(_):
    if year_sweep_lock.locked():
        return
    selected = selected_region_scenario()
    key = year_sweep_key(selected)
    year_sweep_status.value = "<b style='color:#92400e'>Computing 15 × bounded 3×3 local CPU QAOA objectives… no provider job is being submitted.</b>"
    def worker():
        try:
            with year_sweep_lock:
                result = compute_qaoa_year_sweep(selected.model, YEARS, region=selected.name, region_seed=20261106)
                path = persist_qaoa_year_sweep(result, ROOT / "results" / "qaoa_year_sweeps")
                year_sweep_memory[key] = result
            year_sweep_status.value = f"<b style='color:#166534'>Saved local yearly heatmap provenance: {path.name}</b>"
        except Exception as exc:
            year_sweep_status.value = f"<b style='color:#b91c1c'>Yearly heatmap failed: {type(exc).__name__}: {exc}</b>"
        render_year_sweep()
    threading.Thread(target=worker, daemon=True).start()

for widget in [region_count,region_select,region_scenario]:
    widget.observe(render_year_sweep, "value")
year_sweep_compute.on_click(do_year_sweep)
set_region_options()  # defer plotting until the Tab is attached and visible
region_tab=W.VBox([title("Compare one, two and five regions without pretending they are one large quantum circuit"),
                   W.HBox([region_count,region_select,region_year,region_scenario,region_compute,region_reset]),region_out,
                   title("Primary QAOA teaching view: industry-by-year digital probability"), year_sweep_compute,year_sweep_status,year_sweep_out])"""),
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
    quantum_year.value = 2034  # intentionally renders the stale-cache warning
    quantum_year.value = 2033  # returns to the cached baseline
    region_count.value = 2
    region_select.value = "California"
    region_count.value = 1
    dashboard_tabs.selected_index = 3
    dashboard_tabs.selected_index = 0
    for label, output in [
        ("tiny", tiny_out), ("full-network", full_out), ("quantum", quantum_out),
        ("regions", region_out), ("yearly probability heatmap", year_sweep_out),
    ]:
        assert_output_clean(label, output)
    assert "cache" in QCACHE["source_label"].lower()
    print("Widget callbacks and all tab first activations passed without Output-captured rendering errors.")"""),
    ]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    nbf.write(nb, OUT)


if __name__ == "__main__":
    build()
