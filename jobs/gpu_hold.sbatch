#!/bin/bash
#SBATCH -p katef
#SBATCH --qos=katef_qos
#SBATCH --job-name=rax_gpu
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=60G
#SBATCH --time=12:00:00
#SBATCH --output=logs/%j.out   # submit from $RAX_REPRO_ROOT (SBATCH lines do not expand variables)
# Holds one GPU for the RaX Hanoi reproduction; work attaches with srun --jobid=<id> --overlap.
nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv,noheader
echo "holding on $(hostname)"; sleep infinity
