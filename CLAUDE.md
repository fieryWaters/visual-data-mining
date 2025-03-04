# Visual Data Mining Project Guide

## Build & Test Commands
- Setup environment: `source setup_activate_venv.sh` (SFSU cluster)
- Run training (LoRA): `sbatch training/finetune_lora_slurm.sh`
- Run training (full): `sbatch training/finetune_full_slurm.sh`
- Run inference: `python inferences.py`
- Run accuracy test: `python training/accuracy_benchmark.py`
- Run synthetic accuracy test: `python training/accuracy_benchmark_synthetic.py`
- Launch jupyter: `bash launch_sfsu_jupyter_client.sh`

## Code Style Guidelines
- Use Python 3.9+ features
- Follow PEP 8 conventions (black formatter)
- Imports: standard lib first, then third-party, then local modules
- Use bfloat16 precision for model training
- Use torch.cuda.empty_cache() and gc.collect() when freeing model memory
- Use contextmanagers for resource management
- Errors: Prefer explicit error handling with informative messages
- Naming: snake_case for variables/functions, PascalCase for classes
- Comments: Only add comments that explain the code's purpose or logic - do not add comments that respond to change requests
- Keep code modifications clean without explanatory or conversational comments
- Write code as simple as possible. Only add error checking and test cases when those cases are needed. Don't be afraid to add error checking but realize there is a code complexity and code readability cost. 

## Mining Module Status
- Location: `/mining` subdirectory
- Purpose: Data collection system that respects privacy

### Components
- `keystroke_recorder.py`: Real-time keystroke capture with in-memory buffer
- `screen_recorder.py`: Optimized in-memory screenshot capturing (2-3 FPS)
- `keystroke_sanitizer.py`: Password detection and sanitization
- `data_collector.py`: Main controller integrating all modules
- `keystroke_logger.py`: Legacy implementation (being replaced)

### Current Status
- Refactoring completed for screen and keystroke recorders
- Optimized for memory storage with detailed timestamps
- Sanitization system implemented for privacy protection
- Working on final integration and testing

### Project Structure
- Generated directories (excluded from git):
  - `memory_captures/`
  - `screenshots/`
  - `logs/`
  - `__pycache__/`