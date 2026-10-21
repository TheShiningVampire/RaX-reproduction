#!/bin/bash
#SBATCH -p katef
#SBATCH --qos=katef_qos
#SBATCH --job-name=rax_state_smoke
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=60G
#SBATCH --time=1:30:00
#SBATCH --output=/data/user_data/vawale/rax_state/logs/%j.out
# GPU smoke check of the privileged tool (branch exp/add-state-info/object) on the 5 trial tasks.
set -euo pipefail
CODE=${CODE:-$HOME/my_things/codes/rax/.worktrees/add-state-info}
export RAX_RUNTIME_ROOT=/data/user_data/vawale/rax_state/runtime
cd "$CODE"
source scripts/host_env.sh
echo "commit $(git rev-parse HEAD) dirty=$(git status --porcelain | wc -l) host $(hostname)"
nvidia-smi --query-gpu=name,driver_version,uuid --format=csv,noheader
GPU=$(nvidia-smi --query-gpu=uuid --format=csv,noheader | head -1)
PYTHONPATH=. "$RAX_PYTHON" scripts/object_states_smoke.py --gpu "$GPU" --out /data/user_data/vawale/rax_state/smoke/$SLURM_JOB_ID
