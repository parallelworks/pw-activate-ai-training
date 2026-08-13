#!/bin/bash
#SBATCH --job-name=sum_job
#SBATCH --partition=standard
#SBATCH --qos=standard
#SBATCH --account=default
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=4
#SBATCH --gres=gpu:4
#SBATCH --time=00:10:00
#SBATCH --output=sum_%j.out

# Sum the integers 1..N with a job split across 4 parallel tasks.
srun bash sum_job.sh 1000000 "sum_out_${SLURM_JOB_ID}"
