# Configuration loader for training pipeline
import os
import yaml
from typing import Dict, Any, Optional

def load_config(config_path: str) -> Dict[str, Any]:
    """
    Load a YAML configuration file.
    
    Args:
        config_path: Path to the YAML configuration file
        
    Returns:
        Dictionary containing the configuration
    """
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Configuration file not found: {config_path}")
    
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    return config

def get_dataset_file(config: Dict[str, Any]) -> str:
    """
    Get the dataset implementation file path from the configuration.
    
    Args:
        config: Configuration dictionary
        
    Returns:
        Path to the dataset implementation file
    """
    if 'dataset' not in config or 'file' not in config['dataset']:
        raise ValueError("Configuration missing required field: dataset.file")
    
    # Get the dataset file path
    dataset_file = config['dataset']['file']
    
    # Check if the file exists in the datasets directory
    dataset_path = os.path.join("datasets", dataset_file)
    if not os.path.exists(dataset_path):
        raise FileNotFoundError(f"Dataset implementation file not found: {dataset_path}")
    
    return dataset_file

def build_command_args(config: Dict[str, Any], job_num: int = 1) -> list:
    """
    Build command line arguments from the configuration.
    
    Args:
        config: Configuration dictionary
        job_num: Current job number
        
    Returns:
        List of command line arguments
    """
    args = []
    
    # Add dataset arguments
    if 'dataset' in config:
        args.extend([
            "--dataset", "custom_dataset",
            "--custom_dataset.file", config['dataset']['file']
        ])
        
        if 'test_split' in config['dataset']:
            args.extend(["--custom_dataset.test_split", config['dataset']['test_split']])
    
    # Add model arguments
    if 'model' in config:
        if 'name' in config['model']:
            args.extend(["--model_name", config['model']['name']])
        
        if config['model'].get('peft', False):
            args.append("--use_peft")
            
            if 'peft_method' in config['model']:
                args.extend(["--peft_method", config['model']['peft_method']])
            
        if config['model'].get('use_fast_kernels', False):
            args.append("--use_fast_kernels")
    
    # Add checkpoint arguments
    if 'checkpoint' in config:
        if 'root_dir' in config['checkpoint']:
            args.extend(["--dist_checkpoint_root_folder", config['checkpoint']['root_dir']])
            
        if 'dir_name' in config['checkpoint']:
            args.extend(["--dist_checkpoint_folder", config['checkpoint']['dir_name']])
    
    # Add training arguments
    if 'training' in config:
        if 'batch_size' in config['training']:
            args.extend(["--batch_size_training", str(config['training']['batch_size'])])
            
        if 'lr' in config['training']:
            args.extend(["--lr", str(config['training']['lr'])])
            
        if 'epochs_per_job' in config['training']:
            args.extend(["--num_epochs", str(config['training']['epochs_per_job'])])
            
        if 'gradient_accumulation_steps' in config['training']:
            args.extend(["--gradient_accumulation_steps", 
                         str(config['training']['gradient_accumulation_steps'])])
            
        if config['training'].get('enable_fsdp', False):
            args.append("--enable_fsdp")
            
        if 'batching_strategy' in config['training']:
            args.extend(["--batching_strategy", config['training']['batching_strategy']])
            
        if config['training'].get('run_validation', False):
            args.extend(["--run_validation", "True"])
            
        # WandB configuration
        if config['training'].get('use_wandb', False):
            args.extend(["--use_wandb", "True"])
            
            if 'wandb' in config:
                if 'project' in config['wandb']:
                    args.extend(["--wandb_config.project", config['wandb']['project']])
                
                # Generate group name with job number
                group_format = config['wandb'].get('group_format', "training_run_{date}")
                import datetime
                date_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                group_name = group_format.replace("{date}", date_str)
                args.extend(["--wandb_config.group", f"{group_name}_job{job_num}"])
    
    # Add output directory for PEFT weights
    if 'checkpoint' in config and 'root_dir' in config['checkpoint'] and 'dir_name' in config['checkpoint']:
        peft_weights_dir = os.path.join(
            config['checkpoint']['root_dir'],
            config['checkpoint']['dir_name'],
            "peft_weights"
        )
        args.extend(["--output_dir", peft_weights_dir])
    
    return args

def get_slurm_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Get SLURM configuration from the main config.
    
    Args:
        config: Configuration dictionary
        
    Returns:
        Dictionary with SLURM configuration
    """
    slurm_config = {
        "partition": "gpucluster",
        "time": "04:00:00",
        "nodes": 1,
        "job_name": "llama_training",
        "output_path": "logs/training_job_%j.log",
        "gpu_id": 0
    }
    
    if 'slurm' in config:
        for key in slurm_config.keys():
            if key in config['slurm']:
                slurm_config[key] = config['slurm'][key]
    
    return slurm_config

def get_training_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Get training configuration from the main config.
    
    Args:
        config: Configuration dictionary
        
    Returns:
        Dictionary with training configuration
    """
    training_config = {
        "total_jobs": 1,
        "epochs_per_job": 1,
        "create_backups": True
    }
    
    if 'training' in config:
        if 'total_jobs' in config['training']:
            training_config['total_jobs'] = config['training']['total_jobs']
            
        if 'epochs_per_job' in config['training']:
            training_config['epochs_per_job'] = config['training']['epochs_per_job']
    
    if 'checkpoint' in config and 'create_backups' in config['checkpoint']:
        training_config['create_backups'] = config['checkpoint']['create_backups']
        
    if 'checkpoint' in config and 'backup_format' in config['checkpoint']:
        training_config['backup_format'] = config['checkpoint']['backup_format']
    
    return training_config