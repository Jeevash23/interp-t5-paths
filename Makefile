# The later study of the FlyVis silencing preprint (Section 5): code release.
# `make help` lists the targets. PYTHON defaults to the environment that `make setup` creates.
PYTHON ?= .venv/bin/python
PY := $(if $(findstring /,$(PYTHON)),$(abspath $(PYTHON)),$(PYTHON))
CPU := CUDA_VISIBLE_DEVICES= $(PY)
FLYVIS_ROOT := reference/flyvis-first-order/03-Data/flyvis-root
export PYTHONDONTWRITEBYTECODE := 1
export OMP_NUM_THREADS ?= 2
export OPENBLAS_NUM_THREADS ?= 2
export MKL_NUM_THREADS ?= 2
.NOTPARALLEL:

.PHONY: help setup python-check unpack check-freezes quick-check flyvis-models rerun

help:
	@echo "make setup          create .venv with the recorded environment (downloads packages, see ENVIRONMENT.md)"
	@echo "make quick-check    CPU, under a minute, no model and no network: both freeze records, the frozen scoring"
	@echo "                    replayed from the saved per-subtype values and compared byte for byte with the saved"
	@echo "                    scores, the per-subtype values against the independent recheck, and every number in"
	@echo "                    REPORT.md and PILOT-NOTES.md"
	@echo "make flyvis-models  download the released FlyVis models (for the simulation; needs network access)"
	@echo "make rerun          simulate some confirmation models again in a copy and compare them with the saved"
	@echo "                    values: COPY=<new folder> MODELS=\"002 003\" (GPU; about 13 minutes per model)"

setup:
	uv venv --python 3.12.14 .venv
	grep -v -E '^(torch|torchvision)==' requirements.txt > .venv/requirements-pypi.txt
	uv pip install --python .venv/bin/python -r .venv/requirements-pypi.txt --no-deps
	uv pip install --python .venv/bin/python --no-deps --index-url https://download.pytorch.org/whl/cu124 \
	  'torch==2.5.1+cu124' 'torchvision==0.20.1+cu124'

python-check:
	@$(PY) -c "import numpy, scipy" 2>/dev/null || { echo "No usable Python at $(PYTHON): run make setup, or set PYTHON=..."; exit 1; }

unpack: python-check
	$(PY) tools/unpack.py

check-freezes: unpack
	$(PY) tools/check_freezes.py

quick-check: unpack
	$(CPU) tools/check_freezes.py
	$(CPU) -B code/freeze.py check
	$(CPU) -B tools/replay_scores.py
	$(PY) -I tools/compare_recheck.py
	$(PY) -I check_report.py
	$(PY) -I code/check_notes.py

# The released checkpoints of the 50 models (the FlyVis authors' archive); flyvis builds its connectome tables and
# stimulus renderings in the same folder on first use. The reference study's code points FLYVIS_ROOT_DIR there.
flyvis-models: python-check
	mkdir -p $(FLYVIS_ROOT)
	FLYVIS_ROOT_DIR=$(CURDIR)/$(FLYVIS_ROOT) $(dir $(PY))flyvis download-pretrained

# The simulator writes into results/confirmation/ of the folder it runs in, so it runs in a fresh copy of the release
# without the saved results; the FlyVis models are linked into the copy. It runs through code/run.sh (GPU lock, write
# audit), then the new records are read by the frozen readout function and compared with the saved values.
rerun: unpack
	@test -n "$(COPY)" -a -n "$(MODELS)" || { echo "usage: make rerun COPY=<new folder> MODELS=\"002 003\""; exit 1; }
	@test ! -e "$(COPY)" || { echo "$(COPY) exists"; exit 1; }
	@test -d $(FLYVIS_ROOT)/results || { echo "the FlyVis models are missing: run make flyvis-models first"; exit 1; }
	mkdir -p "$(COPY)"
	tar --exclude=./data --exclude='./.venv*' --exclude=./$(FLYVIS_ROOT) --exclude=./results/confirmation \
	  --exclude=./results/pilot --exclude=./results/pilot-v1 -cf - . | tar -xf - -C "$(COPY)"
	ln -s $(CURDIR)/$(FLYVIS_ROOT) "$(COPY)/$(FLYVIS_ROOT)"
	cd "$(COPY)/code" && PYTHON=$(PY) ./run.sh $(MODELS)
	$(PY) -B tools/compare_rerun.py "$(COPY)" $(MODELS)
