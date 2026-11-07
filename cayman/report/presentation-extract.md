
## Slide 1


Quantum Approaches to the Paper Phase Transition
Cayman Quinn, Jaxon Kindred, Luke Papenfuss, Michael Hannesson
NOTES: 

## Slide 2
Introduction to the Problem
Various pressures push industries in the direction of digitization (AI, collaborators, etc…).
Some may resist the pressures, and some may jump in early.
How can Vasion predict the market? How will they know when and where to sell?
Create predictive algorithms to solve this optimization problem. Similar problems can be described by the Ising model.
We investigate quantum algorithms in various contexts to solve these problems, and show how they compare to known classical alternatives.
NOTES: 

## Slide 3
Data / Model
Started with the given test model:
20 industries, used given ties and resistances
Extended it to multiple regions (with biases)
Integrated real data-sets for a more appropriate model
U.S. Census Business Trends and Outlook Survey, 
Bureau of Economic Analysis — Input-Output Accounts, 
Eurostat — E-invoicing by economic activity
Industry AI adoption rate

NOTES: 

## Slide 4
Quantum Approximate Optimization Algorithm (QAOA)
Start with n qubits
Put them into equal superposition
Apply the cost evaluation as a phase
Mix phase into probabilities
Repeat p times
Measure!
Tune classically between layers
NOTES: 

## Slide 5
Getting Some Results with classiq!
We were able to use the classiq studio creatively to create a hybrid quantum and classical circuit and run on simulated bits.
NOTES: 

## Slide 6
Quantum Results with qBraid
Quantum Hardware · QAOA
Simulated Data · QAOA
NOTES: 

## Slide 7
Quantum vs Classical: 20 nodes
Quantum Hardware · QAOA
Original inputs · Exact min-cut
NOTES: Both maps are exact classical annual states for the same 20-node, 24-edge network, 2026–2040. Only the resistance vector changes. New vector: illustrative_blended_resistance_model from the notebook's saved cell 18 table, four-decimal precision. It corrects the prior new-data cell's accidental selection of starter_resistance_unmeasured. Sixteen of 20 first digital dates change. New counts: 2029:3; 2033:1; 2034:6; 2035:10. AI-adoption proxy inputs are illustrative, not calibrated paper-resistance measurements. No quantum execution on this new vector has been supplied.



## Slide 8
Quantum vs Classical: 20 nodes
Original inputs · Exact min-cut
qBraid Simulated Data
classiq  Simulated Data
NOTES: Both maps are exact classical annual states for the same 20-node, 24-edge network, 2026–2040. Only the resistance vector changes. New vector: illustrative_blended_resistance_model from the notebook's saved cell 18 table, four-decimal precision. It corrects the prior new-data cell's accidental selection of starter_resistance_unmeasured. Sixteen of 20 first digital dates change. New counts: 2029:3; 2033:1; 2034:6; 2035:10. AI-adoption proxy inputs are illustrative, not calibrated paper-resistance measurements. No quantum execution on this new vector has been supplied.



## Slide 9
100-node classical: improved data
20 industries × 5 regions · Blended resistance inputs · Exact min-cut
NOTES: READABILITY UPDATE: full-width exact classical map using illustrative_blended_resistance_model, saved notebook display at four-decimal precision. Same topology, paired seed-42 regional noise, and pressure schedule as the original regional instance. Same industry/region order and discrete 2028–2036 scale as the previous slide. These are classical proxy-scenario results, not quantum results or calibrated forecasts.

Both maps are exact classical 100-node, five-region, 15-year sweeps; neither is a 100-qubit quantum result. Original model: audited ClassicalModel (1).ipynb with seed 42. New model: explicitly selected illustrative_blended_resistance_model values from saved cell 18 at four-decimal display precision; raw external CSV unavailable. Paired regional noise draws and other network settings retained. Fixed industry and region order, full 2026–2041 color scale; darker means later. New model: 15 switches in 2028, 16 in 2033, 39 in 2034, 30 in 2035. Assumed/proxy resistances, not calibrated forecasts. Prior circles and Early Flips annotation were removed because they referred to the replaced plots.



## Slide 10
Story: the new 20-industry model
2029 — Digital goes first: Technology, Media and Telecom lead with the lowest resistance.
2033–2034 — Finance opens the next wave: Accounting flips, then Banking and Insurance; Banking’s ties pull Real Estate and Legal into 2034.
2035 — Floodgates open: 10 of 20 industries switch, including Retail, Logistics, Manufacturing, Healthcare and Government.
Why? Rising AI pressure combines with partner pull. Without ties, Government waits until 2039; without its Logistics tie, Agriculture waits until 2036.
NOTES: ADOPTION STORY — NEW BLENDED RESISTANCES
This slide describes the 20-node single-region exact classical model using illustrative_blended_resistance_model, not the original starter scenario or an unperformed quantum run on the new inputs.
Sequence: 2029 Technology/Media/Telecom; 2033 Accounting; 2034 Banking, Insurance, Education, Nonprofit, Real Estate, Legal; 2035 Retail, Hospitality, Logistics, Manufacturing, Energy, Pharma, Construction, Agriculture, Healthcare, Government. All 20 are digital by 2035. Annual AI pressure is 0.63 in 2035; Government resistance is 0.85, so pressure alone does not explain its transition.
WHY / CONTROLLED MODEL TESTS: Newly computed exact classical sweeps hold all other inputs fixed. Removing Banking–Real Estate delays Real Estate and Legal from 2034 to 2035, while Banking itself moves earlier (2033): ties can both help and hold back. Removing Logistics–Agriculture delays Agriculture from 2035 to 2036. Removing all partner ties moves Government from 2035 to 2039. Forcing Accounting to stay paper (resistance 10 mathematical stress test) delays Banking, Insurance, Education, Real Estate and Legal from 2034 to 2035, and Nonprofit to 2036. These are causal effects within the stated model, not real-world customer guarantees.
REGIONAL EXTENSION: In the 100-node model, the digital trio switches across regions in 2028. The busiest regional year is 2034 (39/100 nodes), followed by 2035 (30/100); do not call 2035 the busiest year of that different model. Retail/Hospitality/Logistics move in 2034 in CA/PNW and 2035 elsewhere.
Provenance: new-data-mincut-results.json and new-data-story-counterfactuals.json; exact min-cut on the notebook's saved four-decimal blended inputs, with fixed challenge ties. The adoption proxy and resistance mapping are illustrative, not calibrated forecasts. Older notes below are superseded by this scope and narrative.

UPDATED STORY — BLENDED RESISTANCE SCENARIO
The bullets on this slide now describe newly computed exact classical sweeps using illustrative_blended_resistance_model, not the old starter-resistance scenario. Twenty-node flip counts: 2029:3, 2033:1 (Accounting), 2034:6, 2035:10. Sixteen of twenty dates change. Regional consumer and supply-chain example: Retail, Hospitality, Logistics switch in 2034 in CA/PNW and 2035 in TX/MW/SW. All other network settings retained, including paired seed-42 regional noise. Inputs use the notebook's saved four-decimal display because raw CSV is unavailable. Results are proxy scenarios, not validated forecasts. Existing simulator and Rigetti executions used earlier inputs and do not validate these new models. Older notes below describe the original scenario, not the revised bullets.

Evidence and interpretation:
Original 20-node scenario: the supplied 2026–2040 QAOA simulator sweep reports the same 20 first-digital dates as the notebook-backed exact min-cut reproduction. Eleven industries switch in 2036. The source report supplies flip dates and expectations, not raw quantum sampled bitstrings.
Regional exact notebook model: Legal, Government, Construction, and Real Estate switch in 2035 in California/Pacific NW versus 2036 in Texas, Mountain West, and Southwest. Resistance shifts, noise, and cross-region ties vary together, so this is not an isolated causal experiment.
Rigetti: user-supplied annual classifications contain 31 direct digital-to-paper reversals across 16 industries and six ambiguous cells. Device/job IDs, shots, classification rule, and runtimes were not supplied; do not attribute discrepancies to a particular mechanism.
Practical context: the saved 100-node min-cut full sweep took 0.1668 s; simulator annual jobs were reported at ~5–8 min including unspecified runtime/queue components. No quantum speed advantage is established.
Business action is a hypothesis for outreach planning, not a validated sales forecast or a guarantee that one customer brings another.
Sources: Vasion challenge https://github.com/PrinterLogic/iqc-2026-paper-phase-transition ; supplied full-2026–2040 quantum-sweep report; ClassicalModel (1).ipynb saved outputs and reproduced min-cut results; user-supplied Rigetti table, November 7, 2026.

## Slide 11
Quantum Advantage?
Classical Computation:
Quantum Optimization:
Quantum advantage for large n
Quantum gate computing hardware is limited!
NOTES: 

## Slide 12
Quantum Advantage?
NOTES: 

## Slide 13
The Oracles on “When Vasion Should Sell”
Another optimization problem!
Score each industry in each region by
How soon is it predicted to flip
Reward bonuses on landing connected industries
Enforce the budget and costs
Look ahead in the near future to make a prediction for what to do next . . .
Based on our real-world inspired data set
In 2029, Sell into
Technology in California
Media in California
Telecom in California
Classically,
NOTES: 

## Slide 14
The Oracles on “When Vasion Should Sell” - QAOA!
NOTES: 

## Slide 15
Acknowledgements
Big thank you to Vasion for this challenging and fun problem!
Thank you to qBraid and classiq for supporting our research and allowing us to use their software and credits



NOTES: 
