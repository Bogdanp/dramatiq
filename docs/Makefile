# Minimal makefile for Sphinx documentation
#

# You can set these variables from the command line.
SPHINXOPTS    =
SPHINXBUILD   = sphinx-build
SPHINXPROJ    = remoulade
SOURCEDIR     = source
BUILDDIR      = build


.PHONY: all
all:
	sphinx-versioning build -a -b -W 'v[1-9]+.[0-9]+.[0-9]+' "./docs/$(SOURCEDIR)" "$(BUILDDIR)/html/"


.PHONY: deploy
deploy: all
	gcloud app deploy --project remoulade-docs app.yaml


.PHONY: help
help:
	@$(SPHINXBUILD) -M help "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)


.PHONY: Makefile
# Catch-all target: route all unknown targets to Sphinx using the new
# "make mode" option.  $(O) is meant as a shortcut for $(SPHINXOPTS).
%: Makefile
	@$(SPHINXBUILD) -M $@ "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)
