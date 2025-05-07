# Training Guide

## Quick Start

1. **Log in to Weights & Biases**
   ```bash
   wandb login
   ```

2. **Run the training script**
   ```bash
   sbatch finetune_lora_slurm.sh
   ```

3. **Monitor progress**
   ```bash
   tail -f logs/training_job_[JOBID].log
   ```

## Script Explanation

The `finetune_lora_slurm.sh` script:
- Runs on the SFSU GPU cluster for 4 hours
- Uses LoRA (parameter-efficient fine-tuning)
- Saves checkpoints automatically
- Tracks metrics with Weights & Biases
- Runs training for multiple jobs sequentially (N=2 by default)