#!/bin/bash
#SBATCH --job-name=analyze_readings
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --time=00:05:00
#SBATCH --output=analyze_%j.out

source ./config.sh

srun bash analyze_readings.sh "$DATA_DIR/readings.csv"
