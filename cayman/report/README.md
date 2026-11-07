# IQC Paper Phase Transition — pedagogical report

Prepared for Cayman Quinn, November 7, 2026 (MST / America/Denver).

## Files
- `IQC_Paper_Phase_Transition_Report.pdf`: final compiled report.
- `main.tex`, `references.bib`: editable source and bibliography.
- `figures/`: original supplied figures, plus two attributed presentation reference screenshots and two clearly labeled enlargement crops. All report figures are local; no external image dependencies.
- `metrics/`: unchanged actual evidence CSV/JSON inputs.
- `reproducibility/`: actual C++ measurement source, Python plotting source, original runner/reference-check/guarded-extension scripts, dependencies, immutable provenance and saved raw/summary/machine data. No benchmark was run for this report.
- `tables/`: saved formatted tables generated from metrics.
- `PRESENTATION_MAPPING.md`: complete 15-slide outline, structural alignment and substantive discrepancies.
- `presentation-extract.md`: slide text and speaker notes from the user-supplied deck (not independently verified results).
- `checks/`: tiny illustrative algebra, CSV-to-table generator and QA record.

## Build
Use a standard TeX distribution with latexmk or pdflatex/bibtex and the usual recommended/extra packages, or install Tectonic 0.17.0. Then:

```bash
./build.sh
# or: make
```

Tectonic may fetch public support packages on its initial run. No provider authentication or jobs are involved. `build.sh` writes `main.pdf` and the stable deliverable filename above. The ZIP includes the already compiled PDF; no compiler binary is bundled. Figures and bibliography are self-contained.

Optional document-only checks:
```bash
python3 checks/generate_tables.py
python3 checks/verify_examples.py
```
The latter performs tiny illustrative calculations, not project circuits or performance measurements. Full project reproduction commands are documented in the PDF and explicitly optional/potentially expensive; none were executed for this report.

## Evidence scope
Repository snapshot: e02f5fba57be8279aadc7f0ed7c597a61271f102, https://github.com/caymanq/iqc-competition . No clone or repository modification was performed during report authoring. Immutable source citations are embedded. Raw target statevectors, every QASM/manifest, and raw qBraid counts are not bundled; the report points to their original repository locations without pretending they are in this package.

Adoption bit 0 means digital; target bit 1 means selected. Most quantum results are local CPU simulations. The external qBraid 3q run is a simulator result; 20q status is historical pending/running without returned counts. Classiq demonstration is presentation-reported with circuit/heatmap visuals but lacks repository source/synthesis/job corroboration. No quantum advantage, hardware validation, calibrated forecast or current platform-state check is asserted.

## Presentation alignment
The report follows problem/data → QAOA → Classiq/qBraid → quantum/classical comparison → target oracle → acknowledgement, adding exact foundations and detailed derivations. It does not copy unsupported hardware, bonus-model or large-n advantage claims. Presentation and repository numerical scenarios are explicitly distinguished.
