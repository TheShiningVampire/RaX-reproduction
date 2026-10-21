#!/bin/bash
#SBATCH -p katef-cpu
#SBATCH --qos=katef_cpu_qos
#SBATCH --job-name=rax_setup
#SBATCH --time=02:00:00
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --output=logs/%j.out   # submit from $RAX_REPRO_ROOT (SBATCH lines do not expand variables)
# Phase 0 CPU setup for RaX dexjoco/native: pinned sources, host env (+socat), DexJoCo sim env.
set -euo pipefail
export RAX_RUNTIME_ROOT=${RAX_REPRO_ROOT}/runtime
cd ${RAX_CODE}/.worktrees/dexjoco
echo "== bootstrap"; bash scripts/bootstrap_sources.sh
echo "== host env"; bash scripts/setup_host_env.sh
echo "== socat into host env"
"$RAX_RUNTIME_ROOT/miniforge3/bin/conda" install -y -p "$RAX_RUNTIME_ROOT/envs/host" -c conda-forge socat
echo "== dexjoco env"; bash scripts/setup_dexjoco_env.sh
echo "== doctor (no GPU here, nvidia-smi check expected to fail)"; bash scripts/doctor.sh || true
echo "== unit tests (no GPU, no paid calls)"
PYTHONPATH=. runtime/envs/host/bin/python -m pytest -m "not gpu" -q local_tests/unit 2>&1 | tail -15 || true
echo SETUP_DONE
