# Makefile for the monograph.
#
# Drives latexmk against main.tex; auxiliary files land under build/ to
# keep the source tree clean. The class file relies on bibtex (not biber)
# and uses makeindex, both of which latexmk runs automatically.

DOC      := main
OUT      := monograph
BUILDDIR := build
PDF      := $(BUILDDIR)/$(OUT).pdf

# pdflatex with -outdir mirrors the source tree under build/ for .aux
# files. The mirror directories must exist before the run.
BUILD_SUBDIRS := $(BUILDDIR) \
                 $(BUILDDIR)/classe \
                 $(BUILDDIR)/pre \
                 $(BUILDDIR)/chapters \
                 $(BUILDDIR)/pos

# Every file that, if changed, must trigger a rebuild. Globbed so that
# adding a chapter or a bib entry is automatically picked up.
SRCS := $(DOC).tex pre-textual.tex units.tex \
        $(wildcard chapters/*.tex) \
        $(wildcard pre/*.tex) $(wildcard pre/*.pdf) \
        $(wildcard pos/*.tex) \
        $(wildcard bib/*.bib) \
        $(wildcard classe/*.cls) $(wildcard classe/*.sty) \
        $(wildcard classe/*.bst) \
        $(wildcard img/*.jpg) $(wildcard img/*.png) \
        $(wildcard img/*.pdf)

LATEXMK_FLAGS := -pdf -interaction=nonstopmode -file-line-error \
                 -outdir=$(BUILDDIR) -jobname=$(OUT)

# Beamer decks (Workshop de Ideias / defence). Two independent, standalone
# sources sharing the TikZ figures under img/ via \input. Each builds its own
# PDF into build/. PRES_EN is the English deck (matches the thesis language);
# PRES_PT is the pt-BR deck.
PRES_EN  := presentation
PRES_PT  := presentation-pt_BR
PRES_FLAGS := -pdf -interaction=nonstopmode -file-line-error -outdir=$(BUILDDIR)
PRES_SRCS := $(wildcard img/*-tikz.tex)

.PHONY: all help pdf rebuild watch view clean distclean info text verify pt-scan toc \
        presentation presentation-en presentation-pt presentations pres-view

# `make` and `make pdf` always invoke latexmk; latexmk itself skips the
# rebuild when no source has changed (fingerprint tracking), so this is
# both responsive and fast.
all: pdf presentations

pdf:
	@mkdir -p $(BUILD_SUBDIRS)
	latexmk $(LATEXMK_FLAGS) $(DOC).tex

# --- Beamer presentations -------------------------------------------------

# Build both decks.
presentations: presentation-en presentation-pt

# English deck (default `presentation`) -> build/presentation.pdf
presentation: presentation-en
presentation-en: $(PRES_EN).tex $(PRES_SRCS)
	@mkdir -p $(BUILDDIR)
	latexmk $(PRES_FLAGS) $(PRES_EN).tex
	@echo "Built $(BUILDDIR)/$(PRES_EN).pdf"

# pt-BR deck -> build/presentation-pt_BR.pdf
presentation-pt: $(PRES_PT).tex $(PRES_SRCS)
	@mkdir -p $(BUILDDIR)
	latexmk $(PRES_FLAGS) $(PRES_PT).tex
	@echo "Built $(BUILDDIR)/$(PRES_PT).pdf"

# Open the English deck (override with PRES=presentation-pt_BR).
PRES ?= $(PRES_EN)
pres-view:
	xdg-open $(BUILDDIR)/$(PRES).pdf >/dev/null 2>&1 &

help:
	@echo "Monograph - available make targets"
	@echo ""
	@echo "  make            Build $(PDF) (incremental)"
	@echo "  make pdf        Same as 'make'"
	@echo "  make rebuild    Clean everything and rebuild from scratch"
	@echo "  make watch      latexmk -pvc - rebuild on every file change"
	@echo "  make view       Open the produced PDF in the default viewer"
	@echo ""
	@echo "  make presentations     Build both Beamer decks (EN + pt-BR)"
	@echo "  make presentation      Build the English deck -> build/presentation.pdf"
	@echo "  make presentation-pt   Build the pt-BR deck -> build/presentation-pt_BR.pdf"
	@echo "  make pres-view PRES=presentation-pt_BR   Open a built deck"
	@echo ""
	@echo "  make verify     Build status + page count + undefined-citation scan"
	@echo "  make info       Page count and file size of the PDF"
	@echo "  make toc        Show the page where each chapter starts"
	@echo "  make text       Dump the PDF as plain text (pipe to grep/less)"
	@echo "  make pt-scan    List remaining Portuguese-accented words"
	@echo ""
	@echo "  make clean      Remove latex auxiliary files, keep the PDF"
	@echo "  make distclean  Remove the entire build/ directory"
	@echo "  make help       Show this message"

# File rule for targets that consume the PDF (info, verify, view, ...).
# Sources are listed so this rule fires when any source changes; latexmk
# itself skips work via fingerprint tracking when nothing has changed.
$(PDF): $(SRCS)
	@mkdir -p $(BUILD_SUBDIRS)
	latexmk $(LATEXMK_FLAGS) $(DOC).tex

# Force a full rebuild from a clean state (useful after structural edits).
rebuild: distclean pdf presentations

# Continuously rebuild and (if a viewer is configured) refresh the PDF.
watch:
	@mkdir -p $(BUILD_SUBDIRS)
	latexmk $(LATEXMK_FLAGS) -pvc $(DOC).tex

# Open the produced PDF with the system default viewer.
view: $(PDF)
	xdg-open $(PDF) >/dev/null 2>&1 &

# Print page count and file size of the built PDF.
info: $(PDF)
	@pdfinfo $(PDF) | grep -E "Pages|File size"

# Dump the rendered text of the PDF (handy for reviewing without a reader).
text: $(PDF)
	@pdftotext -layout $(PDF) -

# Print the page where each chapter starts (TOC + first occurrence).
toc: $(PDF)
	@pdftotext -layout $(PDF) - | grep -nE "(INTRODUCTION|THEORETICAL FOUNDATION|METHODOLOGY|EXPERIMENTAL EVALUATION|CONCLUSION|REFERENCES)" | head

# List remaining Portuguese-accented words in the rendered PDF (proper nouns
# such as "São", "Géron", "Português" are expected).
pt-scan: $(PDF)
	@pdftotext $(PDF) - | grep -oE "\b\w*[áàâãéêíóôõúçÁÀÂÃÉÊÍÓÔÕÚÇ]\w*\b" | sort -u

# One-shot health check: build status, page count, missing/undefined cites.
verify: $(PDF)
	@echo "=== $(PDF) ==="
	@pdfinfo $(PDF) | grep -E "Pages|File size"
	@echo "=== Undefined citations / references ==="
	@grep -E "Warning.*[Cc]itation|undefined" $(BUILDDIR)/$(OUT).log | head || echo "  (none)"
	@echo "=== Chapter pages ==="
	@pdftotext -layout $(PDF) - | grep -nE "(INTRODUCTION|THEORETICAL FOUNDATION|METHODOLOGY|EXPERIMENTAL EVALUATION|CONCLUSION|REFERENCES)" | head

# Remove latex auxiliary files, keep the PDF.
clean:
	latexmk -c -outdir=$(BUILDDIR) -jobname=$(OUT) $(DOC).tex || true
	latexmk -c -outdir=$(BUILDDIR) $(PRES_EN).tex $(PRES_PT).tex || true

# Remove the entire build directory.
distclean:
	rm -rf $(BUILDDIR)
