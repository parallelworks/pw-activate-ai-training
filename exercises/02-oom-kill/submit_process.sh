#!/bin/bash
#SBATCH --job-name=sensor_rollup
#SBATCH --partition=standard
#SBATCH --qos=standard
#SBATCH --nodes=1
#SBATCH --ntasks=4
#SBATCH --mem=1G
#SBATCH --time=00:30:00
#SBATCH --output=sensor_rollup_%j.out

# Roll up sensor readings across parallel tasks.
srun bash process_data.sh data/input_full.csv
