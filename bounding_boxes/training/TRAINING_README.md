# Training Guide

## Setup

1. **ssh onto SFSU cluster**
   ```bash
   ssh sfsu
   ```
   Make sure you are using VPN if you are not on campus. Requires the prerequisite of running the first_time_setup scripts.

2. **create and activate virtual env**
   ```bash
   python3.11 -m venv ~/git-repos/visual-data-mining/training/training_venv
   source ~/git-repos/visual-data-mining/training/training_venv/bin/activate
   ```
   Only need to create the venv the first time.

3. **install requirements**
   ```bash
   pip install wandb
   pip install uv
   uv pip install -r ~/git-repos/visual-data-mining/training/training_requirements.txt
   ```
   Only need to install requirements once, can skip if already done.

4. **login to wandb and huggingface**
   ```bash
   wandb login
   huggingface-cli login --token YOUR_TOKEN
   ```
   Need to have setup a acounts for both weights and biases and huggingface. For weights and biases, need to join the fierywaters13-san-francisco-state-university team. It might keep you logged in so you don't have to login every time.

## Running

### run the training script
```bash
sbatch finetune_lora_slurm.sh
```
Creates a job on the cluster. If the node is being fully used, you might run into memory errors in which case you might need to add ```#SBATCH --exclusive``` to the top of the script to request the whole node.

### view output of the job
```bash
tail -f logs/training_job_[JOBID].log
```
This is for when it is still running, once it is finished running, you can use vim, cat, or other command-line code editors/viewers on the same log file.

### view jobs on the cluster
```bash
squeue
```
This gives a list of all the current jobs on the cluster and you can use it to figure out your JOBID.


## Script Explanation

The `finetune_lora_slurm.sh` script:
- Runs on the SFSU GPU cluster for 4 hours
- Uses LoRA (parameter-efficient fine-tuning)
- Saves checkpoints automatically
- Tracks metrics with Weights & Biases
- Runs training for multiple jobs sequentially (N=2 by default)