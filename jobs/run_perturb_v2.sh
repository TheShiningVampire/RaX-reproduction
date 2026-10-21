#!/bin/bash
# One perturbation batch of the session-2 submitted bundle via the harness's parallel_batch.
# Usage: run_perturb.sh <jobid> <perturb: rand_full|mass> <first_layout> <episodes> <workers> <source_copy_dir> <out_name>
# Layouts first_layout..first_layout+episodes-1 of the 150 official ones (eval seed 1), same as the formal test.
set -euo pipefail
JOB=$1 P=$2 START=$3 N=$4 W=$5 SRC=$6 NAME=$7
R=${RAX_REPRO_ROOT}
B=c8712bc7f03f4abf8d6a6fab4c00aae5
OUT=$R/runtime/auto-research/$NAME
cd ${RAX_CODE}/.worktrees/dexjoco-pert
exec srun --jobid=$JOB --overlap -n1 bash -c "export RAX_RUNTIME_ROOT=$R/runtime RAX_PERTURB=$P RAX_FORMAL_START=$START; source scripts/host_env.sh; \
  exec python -m services.controller.parallel_batch --source-session $SRC --bundle $B --output $OUT --episodes $N --workers $W"
