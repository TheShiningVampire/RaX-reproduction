#!/bin/bash
# Wait for a GPU job, copy the session-2 source for its GPU, then run one perturbation batch on layouts 0..74.
# Usage: launch_when_running.sh <jobid> <perturb>
set -euo pipefail
JOB=$1 P=$2
R=${RAX_REPRO_ROOT}; A=$R/runtime/auto-research; S2=$A/20261020T180046Z_b52a07ed8c
until [ "$(squeue -h -j $JOB -o %T)" = RUNNING ]; do sleep 20; done
G=$(srun --jobid=$JOB --overlap -n1 nvidia-smi --query-gpu=uuid --format=csv,noheader)
python3 -I $R/tools/make_source_copy.py $S2 $A/srccopy_${P}_v2 $G
exec $R/jobs/run_perturb_v2.sh $JOB $P 0 75 6 $A/srccopy_${P}_v2 pert_${P}_v2
