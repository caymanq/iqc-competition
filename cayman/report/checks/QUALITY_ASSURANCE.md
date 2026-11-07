# Final report quality assurance

Prepared November 7, 2026 (America/Denver / MST).

## Build
- Compiled with Tectonic 0.17.0 on the box, with BibTeX and repeated TeX passes for resolved cross-references.
- Final PDF: 31 letter-size pages, including title, one-page contents and references (28 remaining pages of narrative/appendices).
- Final build logs: zero errors, zero warnings, no overfull/underfull boxes, no undefined citations/references, no missing figures. Title-page hyperlink anchor duplication was resolved.
- Extracted the ZIP into a separate scratch directory and rebuilt from packaged source: passed, same 31-page count, clean references/figure/layout log. All PDF fonts are embedded.
- Editable main.tex, local figures, references.bib, build.sh and Makefile supplied. Standard TeX Live/latexmk or pdflatex/bibtex and Tectonic supported. No compiler binary bundled.

## Visual checks and corrections
- Rendered and inspected representative math pages: two-qubit Hamiltonian/phase table/gate factors, coherent one-qubit mixer and complete cost+mixer toy.
- Inspected original adoption walkthrough, yearly adoption heatmap, pinned DQA histogram, Classiq presentation screenshot, CPU runtime plots, complete annual target tables/MAP, enlarged target maps, title, artifact index, reproduction appendix, slide mapping and bibliography.
- Fixed an initially overflowing MAP-table/figure combination by preventing table floats and consolidating identical no-eligible display rows; full 15-year CSVs remain unchanged.
- Target maps use explicitly labeled enlargement crops of original plot/axes/colorbar; right-side annotation and tiny footer are supplied in full originals and explained by captions. No plotted values or reference marks changed.
- Main prose and tables are readable; original circuit screenshots and dense original plot legends remain fine-grained evidence, not newly extracted resource claims. Full-resolution originals included for zooming.
- Layout check images are outside the deliverable directory under /workspace/iqc-report/render-checks/; not source-package dependencies.

## Arithmetic and saved-data checks
- checks/verify_examples.py independently verifies the illustrative two-qubit energies (-5,-1,9,-3), cuts (4,8,18,6), offset -9 and one-qubit P0/P1 formula and chosen ground-state angles. Maximum numerical probability error 2.22e-16. These are tiny document checks, not research simulations/benchmarks.
- checks/verify_saved_metrics.py verifies 15 target years (9 eligible, 6 no eligible), binomial dimensions, feasibility mass, marginal sums, p2 incumbent dominance, expectation gaps, exact/MAP recommendation scores/counts, maximum measured sizes and 805/1000 qBraid ground fraction. Passed.
- Original metrics and nine original figures were copied byte-for-byte from the supplied evidence directory. New crops and presentation screenshots have separate names.
- Benchmark aggregation was checked against actual immutable plot_results.py: end-to-end curves sum component medians; reported energy gap is median expected energy minus median exact energy (not necessarily median paired gap).
- Repeat caveat preserved: common 4–20q three repeats, 22q two, 24q/26q one; guarded 4000/6000/8000 classical extension one each. Older screenshot's blanket “3 repeats” is not copied.

## Provenance and scope
- Repository commit e02f5fba57be8279aadc7f0ed7c597a61271f102 only. No clone or repository modification during authoring.
- Original QAOA arXiv:1411.4028v1 source opened and verified; other references use immutable source links identified by evidence, plus the supplied presentation as a clearly attributed user source.
- Actual C++/Python benchmark sources and original runner/helpers read narrowly at the immutable commit and included under reproducibility/, with immutable raw URLs and local hashes. Source code was NOT compiled or executed for report preparation. Plot script was NOT run; original empirical figures preserved.
- No new project simulations, benchmarks, provider jobs, authenticated Lab check, qBraid polling or credit spending.
- Dossier arithmetic/schedule errors corrected. Classiq upgraded from a repo-only absence statement to presentation-reported simulator demonstration, while retaining missing source/synthesis/run metadata caveat. Hardware labels and new blended-data classical scenarios are not promoted to verified circuit results.
- Original presentation was not edited. Complete outline/discrepancies are in PRESENTATION_MAPPING.md.
