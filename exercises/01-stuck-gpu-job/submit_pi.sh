#!/bin/bash
#SBATCH --job-name=mpi_pi
#SBATCH --partition=gpu
#SBATCH --nodes=2
#SBATCH --ntasks-per-node=4
#SBATCH --gres=gpu:4
#SBATCH --time=00:10:00
#SBATCH --output=mpi_pi_%j.out

# Estimate pi with a bash+awk Monte Carlo across MPI ranks.
srun bash mpi_pi.sh 1000000 "pi_out_${SLURM_JOB_ID}"
