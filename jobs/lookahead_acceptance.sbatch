#!/bin/bash
#SBATCH -p katef
#SBATCH --qos=katef_qos
#SBATCH --job-name=rax_lookahead_accept
#SBATCH --gres=gpu:RTX_PRO_6000:1
#SBATCH --exclude=babel-z9-16
#SBATCH --cpus-per-task=8
#SBATCH --mem=60G
#SBATCH --time=2:00:00
#SBATCH --output=/data/user_data/vawale/rax_state/logs/%j.out
# GPU acceptance of dexjoco_lookahead (branch exp/add-state-info/lookahead) on the 5 trial tasks.
set -euo pipefail
CODE=${CODE:?set CODE to a clean worktree}
export RAX_RUNTIME_ROOT=/data/user_data/vawale/rax_state/runtime RAX_PRIVILEGED_STATE=full RAX_LOOKAHEAD=on
cd "$CODE"
unset XDG_CACHE_HOME XDG_RUNTIME_DIR
source scripts/host_env.sh
echo "commit $(git rev-parse HEAD) dirty=$(git status --porcelain | wc -l) host $(hostname)"
nvidia-smi --query-gpu=name,driver_version,uuid --format=csv,noheader
GPU=$(nvidia-smi --query-gpu=uuid --format=csv,noheader | head -1)
PYTHONPATH=. "$RAX_PYTHON" scripts/lookahead_acceptance.py --gpu "$GPU" --out /data/user_data/vawale/rax_state/accept/$SLURM_JOB_ID
