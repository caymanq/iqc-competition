# Presentation alignment and evidence review

Reference: user-supplied 15-slide PowerPoint, title “Quantum Approaches to the Paper Phase Transition.” Authors on slide 1: Cayman Quinn, Jaxon Kindred, Luke Papenfuss, Michael Hannesson. Read-only review; no slides edited. Full extracted text and notes: presentation-extract.md. Contact sheet and relevant rendered slide visuals were inspected, including slides 5 and 8 at full rendered size. Slide 5 is reproduced with a qualified caption in the report; slide 12's illustrative/empirical composite is preserved as a separate reference JPEG, not an invented dataset.

## Actual outline and report mapping
1. Quantum Approaches to the Paper Phase Transition → report title/scope.
2. Introduction to the Problem → introduction and business framing.
3. Data / Model → data/assumptions, notation, Ising/exact foundations.
4. Quantum Approximate Optimization Algorithm (QAOA) → full QAOA walkthrough, two-qubit cost and one-qubit mixer/toy.
5. Getting Some Results with classiq! → Classiq presentation-reported demonstration and repository corroboration gap.
6. Quantum Results with qBraid → qBraid export/simulator/historical pending distinctions.
7. Quantum vs Classical: 20 nodes → dashboard and provenance cautions.
8. Quantum vs Classical: 20 nodes → platform comparison cautions.
9. 100-node classical: improved data → distinct presentation-reported coupled classical scenario, not dashboard statevector.
10. Story: the new 20-industry model → presentation-reported revised-vector results, not imported into earlier metrics.
11. Quantum Advantage? → operation-count vs empirical comparison caveats.
12. Quantum Advantage? → measured CPU runtime/quality and distinction from assumed N-curves.
13. The Oracles on “When Vasion Should Sell” → four-year target model/constraints/reduction.
14. The Oracles on “When Vasion Should Sell” - QAOA! → constrained XY ansatz, yearly metrics, heatmaps/MAP/recommendations.
15. Acknowledgements → acknowledgements plus limitations/conclusions.

## Structural alignment made
- Adopted deck title and problem → data → QAOA → Classiq → qBraid → classical comparisons → target oracle → acknowledgements narrative.
- Placed exact classical foundations before QAOA so gate/sign derivations have a ground-truth reference.
- Retained long derivations in natural QAOA subsections; expanded target methods/results rather than treating final oracle as the adoption model.
- Put reproduction, artifact index and presentation mapping in appendices.
- Preserved two separate use cases and clearly labeled bit meanings.

## Classiq inspection (new user evidence)
Slide 5 explicitly claims hybrid quantum/classical circuit work in Classiq Studio on simulated bits. It embeds a dark multiqubit circuit visualization and a heatmap titled “QAOA estimated adoption probability by year,” spanning 20 industries and 2026–2040. The heatmap appears again in slide 8 labeled “classiq Simulated Data.” This supports “presentation-reported simulator demonstration with visual circuit evidence,” NOT “Classiq was only proposed” or “no Classiq work exists.”
Neither slide gives a readable source program, synthesis resource report, job ID, shots, selected angles or backend execution metadata; the screenshot does not demonstrate a verified linkage between displayed circuit and all yearly heatmap entries. No gate/depth/resource statistics are extracted. No Classiq source/synthesis/execution artifacts were found in the reviewed repository dossier. There remains a repository corroboration/reproducibility gap, not proof that external work did not happen.

## Substantive discrepancies not copied into the report
- Slides 6–7 use “Quantum Hardware · QAOA”; reviewed artifact evidence is local DQA/standard QAOA simulations, one external three-qubit qBraid simulator, and a historical 20q pending/running job without counts. Deck notes mention user-provided Rigetti classifications lacking IDs/shots/rules/runtimes. No new hardware result is inferred.
- Slide 8's qBraid figure actually says DQA digital probability. DQA is not free-angle QAOA.
- Several slide notes explicitly describe exact classical maps despite prominent quantum comparison labels. Notes also distinguish original inputs from newly blended inputs; original circuit evidence does not validate revised-vector outputs.
- Slide 3 names Census/BEA/Eurostat and an AI-adoption proxy. Notes qualify blended resistance as illustrative, using notebook four-decimal saved values because raw CSV is unavailable. The report does not claim independently verified datasets or calibrated forecasts.
- Slide 9 is a separate coupled 100-node classical regional model. The saved teaching dashboard's independent 1/2/5 regional selectors remain separate 20q circuits, not a 100q quantum run.
- Slide 10 reports revised-vector transition counts and counterfactuals; source result JSONs named in notes were not included in this evidence archive. These are attributed to presentation notes, not reproduced/validated.
- Slide 11 suggests large-n quantum advantage from simplified operation counts. CPU statevector timing is not hardware runtime, and counts omit shots/optimizer/routing/noise. No measured advantage or crossover is asserted.
- Slide 13 includes connected-industry bonuses and a 2029 Technology/Media/Telecom California example. The saved target study has no bonuses, unit costs, independent years and a four-year eligibility window. Its exact 2029 set is Energy/Hospitality/Logistics/Manufacturing/Retail; these are different scenarios.
- Slide 15's thanks for credits do not establish per-job spending. Only saved 3q qBraid record reports charged credits (0).

## Evidence corrections applied beyond deck alignment
- Illustrative HC=-4 Z1Z2-3 Z1+2 Z2 energies are (-5,-1,9,-3), cuts (4,8,18,6), offset -9. The dossier's erroneous arithmetic is not reproduced or called a passed regression.
- DQA schedule uses s=t/T in BOTH weights.
- Lab notebook prepared/runnable; automated deployment verification and Lab-only edits not recovered, no fresh authenticated Lab check.
