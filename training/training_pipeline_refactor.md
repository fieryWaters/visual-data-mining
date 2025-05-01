# Training Pipeline Refactoring Plan

## Current State Analysis

The current training pipeline has several issues:
- Dataset selection is hardcoded in tokenize_dataset.py (line 53: `dataset = dataset.select(range(100))`)
- Data sources are hardcoded, requiring code modification to change datasets
- Accuracy benchmark files have hardcoded paths and parameters
- Training scripts contain redundant code with different parameter sets
- Configuration is spread across multiple files making it hard for new team members to understand

## Proposed Solution

Create a centralized configuration system that separates configuration from implementation while minimizing code changes. This approach will leverage existing modular design where possible.

### Core Components

1. **Configuration Files**
   - Single YAML file containing all parameters
   - Different config files for different scenarios (test vs. production)
   - Example: `configs/test.yaml`, `configs/production.yaml`

2. **Dataset Implementation Files**
   - Separate implementation files for different datasets
   - Each file maintains the `get_custom_dataset` function signature
   - Example: `datasets/synthetic_dataset.py`, `datasets/test_dataset.py`

3. **Entry Point Script**
   - Unified `train.sh` script that takes a config file path
   - Extracts parameters from config
   - Runs appropriate commands based on config values

### Implementation Details

#### Configuration Structure
```yaml
# Example config.yaml structure
dataset:
  name: "custom_dataset"
  file: "synthetic_dataset.py"  # or test_dataset.py for small dataset
  test_split: "test"
  split_ratio: 0.8

model:
  name: "meta-llama/Llama-3.2-11B-Vision-Instruct"
  peft: true
  peft_method: "lora"
  checkpoint_dir: "finetuned_model/fine-tuned"
  
training:
  batch_size: 8
  lr: 1e-5
  epochs_per_job: 1
  total_jobs: 10
  gradient_accumulation: 1
  
slurm:
  partition: "gpucluster"
  time: "04:00:00"
  nodes: 1
  gpu_id: 3  # CUDA_VISIBLE_DEVICES
```

#### File Modifications

1. **Dataset Implementation Files**
   - Create files like `datasets/synthetic_dataset.py` containing:
     ```python
     def get_custom_dataset(dataset_config, processor, split, split_ratio=0.8):
         # Full implementation with specific dataset loading logic
         # For test dataset, include dataset.select(range(100))
     ```

2. **Entry Point Script (`train.sh`)**
   - Loads config file
   - Extracts parameters
   - Builds command line arguments
   - Handles job chaining based on config

3. **Minimal changes to existing files**
   - Most core files remain unchanged
   - `tokenize_dataset.py` might require slight modification if needed

### Data Flow

1. User runs: `./train.sh configs/test.yaml`
2. Script extracts parameters from YAML
3. Builds appropriate command with all parameters
4. Executes training with the specified dataset file
5. Handles job chaining for multi-job training

## Strengths

1. **Minimal Code Changes**
   - Leverages existing modular design where possible
   - Focuses on configuration extraction, not code restructuring

2. **Enhanced Flexibility**
   - Easy to add new parameters in the future
   - Simple to create new dataset implementations
   - Configuration changes don't require code changes

3. **Improved Discoverability**
   - One central place for all configuration
   - Clear separation between configuration and implementation
   - Easier for new team members to understand

4. **Backwards Compatibility**
   - Old scripts could still work alongside new system
   - Gradual migration path available

## Uncertainties and Risks

1. **Dataset File Loading Mechanism**
   - How exactly does `finetuning.py` use the `--custom_dataset.file` parameter?
   - Does it dynamically import? Or use another mechanism?
   - FIRST STEP: Test with a duplicate file to see if it works as expected

2. **Parameter Processing**
   - How does `finetuning.py` process nested parameters?
   - Are there conventions we need to follow?

3. **Job Chaining Logic**
   - How will job chaining work with the unified approach?
   - Will we need to preserve special logic from the SLURM scripts?

4. **Integration with Other Tools**
   - How will this interact with existing tools in the pipeline?
   - Are there dependencies we're not aware of?

## Implementation Plan

### Phase 1: Investigation and Testing
1. Create duplicate of `tokenize_dataset.py` with minor modifications
2. Test running with new file to see how system behaves
3. Document actual behavior of `--custom_dataset.file` parameter

### Phase 2: Create Basic Configuration System
1. Create sample YAML configuration files
2. Implement basic config loading in `train.sh`
3. Test with minimal parameter changes

### Phase 3: Create Dataset Implementations
1. Create dataset implementation files with different configurations
2. Test compatibility with training system
3. Verify results match expectations

### Phase 4: Complete Integration
1. Finalize entry point script
2. Add support for all parameters
3. Document usage for team

### Phase 5: Testing and Validation
1. Test full workflow with different configurations
2. Verify job chaining works correctly
3. Document any issues or workarounds

## Success Criteria

1. **Functionality**
   - System works with both full and subset datasets
   - No change in training outcomes, just in configuration
   - Job chaining works correctly

2. **Usability**
   - New team members can understand the system
   - Changing datasets or parameters is straightforward
   - Configuration is centralized and easy to modify

3. **Extensibility**
   - New parameters can be added easily
   - New dataset implementations can be created without code changes
   - System can adapt to future needs

## Next Steps

1. Begin with experimental testing of the dataset file loading mechanism
2. Create prototype configuration and entry point
3. Validate approach with small changes before full implementation
4. Document findings and decisions along the way