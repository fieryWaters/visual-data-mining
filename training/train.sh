#!/bin/bash
# Unified training script for the visual data mining project

# Parse command line arguments
CONFIG_FILE=${1:-"configs/example_config.yaml"}
JOB_NUM=${2:-1}

# Check if the config file exists
if [ ! -f "$CONFIG_FILE" ]; then
    echo "Error: Configuration file not found: $CONFIG_FILE"
    exit 1
fi

# Set up environment
source ~/git-repos/visual-data-mining/venv/bin/activate
cd ~/git-repos/visual-data-mining/training

# Make sure torchrun is available
which torchrun || echo "torchrun not found in PATH"

# Load configuration values using Python
echo "Loading configuration from $CONFIG_FILE..."
CONFIG_VALUES=$(python3 -c "
import json
import sys
sys.path.append('.')
from config_loader import load_config, get_slurm_config, get_training_config, get_dataset_file

# Load the configuration
config = load_config('$CONFIG_FILE')

# Get SLURM configuration
slurm_config = get_slurm_config(config)

# Get training configuration
training_config = get_training_config(config)

# Get checkpoint paths
checkpoint_root = config.get('checkpoint', {}).get('root_dir', 'finetuned_model')
checkpoint_dir = config.get('checkpoint', {}).get('dir_name', 'fine-tuned')

# Get dataset file
dataset_file = get_dataset_file(config)

# Get GPU ID for CUDA_VISIBLE_DEVICES
gpu_id = slurm_config.get('gpu_id', 0)

# Print values as shell variables
print(f'PARTITION={slurm_config[\"partition\"]}')
print(f'TIME={slurm_config[\"time\"]}')
print(f'NODES={slurm_config[\"nodes\"]}')
print(f'JOB_NAME={slurm_config[\"job_name\"]}')
print(f'OUTPUT_PATH={slurm_config[\"output_path\"]}')
print(f'GPU_ID={gpu_id}')
print(f'TOTAL_JOBS={training_config[\"total_jobs\"]}')
print(f'EPOCHS_PER_JOB={training_config[\"epochs_per_job\"]}')
print(f'CREATE_BACKUPS={training_config[\"create_backups\"]}')
print(f'BACKUP_FORMAT={training_config.get(\"backup_format\", \"fine-tuned_backup_job_$JOB_NUM\")}')
print(f'CHECKPOINT_ROOT={checkpoint_root}')
print(f'CHECKPOINT_DIR={checkpoint_dir}')
print(f'DATASET_FILE={dataset_file}')
")

# Source the configuration values
eval "$CONFIG_VALUES"

# Set derived paths
FULL_CHECKPOINT_PATH="${CHECKPOINT_ROOT}/${CHECKPOINT_DIR}"
PEFT_WEIGHTS_DIR="${FULL_CHECKPOINT_PATH}/peft_weights"

echo "Starting training job number $JOB_NUM at $(date)"
echo "Running on node: $(hostname)"
echo "Using dataset implementation: $DATASET_FILE"
echo "Checkpoint directory: $FULL_CHECKPOINT_PATH"

# Function to check if previous run was successful
check_previous_run() {
    if [ $JOB_NUM -gt 1 ]; then
        # Check for PEFT weights directory
        if [ ! -d "$PEFT_WEIGHTS_DIR" ]; then
            echo "Previous PEFT checkpoint not found at $PEFT_WEIGHTS_DIR"
            echo "Contents of checkpoint directory (if it exists):"
            ls -la $FULL_CHECKPOINT_PATH || echo "Directory does not exist"
            exit 1
        else
            echo "Found valid PEFT checkpoint at $PEFT_WEIGHTS_DIR"
        fi
    fi
}

# Function to run training
run_training() {
    local peft_flag=""
    if [ $JOB_NUM -gt 1 ]; then
        peft_flag="--train_config.from_peft_checkpoint $PEFT_WEIGHTS_DIR"
        echo "Loading from PEFT checkpoint: $PEFT_WEIGHTS_DIR"
    else
        echo "Starting fresh training without PEFT checkpoint"
        # Ensure checkpoint directory is clean for first run
        rm -rf $FULL_CHECKPOINT_PATH
        mkdir -p $FULL_CHECKPOINT_PATH
    fi

    # Build command arguments using Python
    CMD_ARGS=$(python3 -c "
from config_loader import load_config, build_command_args
config = load_config('$CONFIG_FILE')
args = build_command_args(config, $JOB_NUM)
print(' '.join(args))
")

    # Run the training command
    CUDA_VISIBLE_DEVICES=$GPU_ID torchrun --nnodes 1 --nproc_per_node 1 finetuning.py \
        $CMD_ARGS \
        $peft_flag

    # Check if training was successful
    return $?
}

# Create checkpoint root directory if it doesn't exist
mkdir -p $CHECKPOINT_ROOT

# Check if we have previous checkpoints when needed
check_previous_run

# Run the training
run_training

# Check if training was successful
if [ $? -eq 0 ]; then
    echo "Training job $JOB_NUM completed successfully at $(date)"
    
    # Chain to next job if we haven't reached TOTAL_JOBS
    if [ $JOB_NUM -lt $TOTAL_JOBS ]; then
        NEXT_NUM=$((JOB_NUM + 1))
        echo "Submitting job number $NEXT_NUM"
        
        # Create a backup of the checkpoint before starting next job
        if [ "$CREATE_BACKUPS" = "true" ]; then
            # Replace job_num in the backup format if needed
            BACKUP_DIR_TEMPLATE=$(echo $BACKUP_FORMAT | sed "s/{job_num}/$JOB_NUM/g")
            BACKUP_DIR="${CHECKPOINT_ROOT}/${BACKUP_DIR_TEMPLATE}"
            echo "Creating backup at: $BACKUP_DIR"
            rm -rf "$BACKUP_DIR"  # Remove old backup if it exists
            cp -r $FULL_CHECKPOINT_PATH "$BACKUP_DIR"
            
            # Backup wandb ID file specifically
            if [ -f "${PEFT_WEIGHTS_DIR}/wandb_id.txt" ]; then
                cp "${PEFT_WEIGHTS_DIR}/wandb_id.txt" "${BACKUP_DIR}/wandb_id.txt"
            fi
        fi
        
        # Submit the next job with SLURM
        sbatch --job-name=$JOB_NAME \
               --partition=$PARTITION \
               --time=$TIME \
               --nodes=$NODES \
               --output=$OUTPUT_PATH \
               --dependency=afterok:$SLURM_JOB_ID \
               $0 $CONFIG_FILE $NEXT_NUM
    else
        echo "All training jobs completed successfully!"
    fi
else
    echo "Training job $JOB_NUM failed at $(date)"
    exit 1
fi