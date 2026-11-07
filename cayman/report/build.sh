#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
if command -v latexmk >/dev/null 2>&1; then
 latexmk -pdf -interaction=nonstopmode -halt-on-error main.tex
elif command -v pdflatex >/dev/null 2>&1; then
 pdflatex -interaction=nonstopmode -halt-on-error main.tex
 bibtex main
 pdflatex -interaction=nonstopmode -halt-on-error main.tex
 pdflatex -interaction=nonstopmode -halt-on-error main.tex
elif command -v tectonic >/dev/null 2>&1; then
 tectonic --keep-logs --keep-intermediates main.tex
elif [ -x ../toolchain/tectonic ]; then
 ../toolchain/tectonic --keep-logs --keep-intermediates main.tex
else
 echo 'Install TeX Live (latexmk + recommended/extra packages), or Tectonic, then rerun.' >&2
 exit 1
fi
cp main.pdf IQC_Paper_Phase_Transition_Report.pdf
