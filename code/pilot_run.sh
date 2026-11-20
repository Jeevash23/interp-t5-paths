#!/usr/bin/env bash
# Run the BM2 development pilot on the local GPU under the portfolio GPU lock, with a write audit of AI-06.
#   systemd-run --user --collect -p Nice=10 -p MemoryMax=6G -p MemorySwapMax=1G -p TasksMax=256 \
#     -p WorkingDirectory=<BM2>/code --unit=bm2-pilot <BM2>/code/pilot_run.sh [models...]
set -euo pipefail
cd "$(dirname "$0")"
study="$(cd .. && pwd)"
ai06="$(cd ../reference/flyvis-first-order && pwd -P)"  # release: the reference study's files
python="${PYTHON:-$study/.venv/bin/python}"  # release: the release environment
lock="$study/code/gpu_lock.py"  # release: a copy of the GPU lock helper
touch "$study/${GPU_LOCK:-gpu.lock}"
logs="$study/results/pilot/logs"
mkdir -p "$logs"
free_gib=$(df --output=avail -BG / | tail -1 | tr -dc '0-9')
if [ "$free_gib" -lt 5 ]; then echo "less than 5 GiB free; not starting"; exit 1; fi
marker="$logs/audit.marker"
touch "$marker"
sleep 1
export OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 MKL_NUM_THREADS=2
"$python" -B "$lock" "$python" -B pilot_simulate.py "$@" 2>&1 | tee "$logs/pilot.log"
changed=$(find "$ai06" -path "$ai06/03-Data/flyvis-root" -prune -o -newer "$marker" -print 2>/dev/null | wc -l)  # release: flyvis-root skipped
printf '{"finished": "%s", "files_changed_under_AI06": %s}\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$changed" > "$logs/audit.json"
echo "write audit: $changed files changed under AI-06"
[ "$changed" -eq 0 ]
