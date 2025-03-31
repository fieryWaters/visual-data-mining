# CLAUDE.md - Agent Reference Guide

## Build/Run Commands
- Single GPU training: `CUDA_VISIBLE_DEVICES=0 torchrun --nproc_per_node 1 finetuning.py --model_name meta-llama/Llama-3.2-11B-Vision-Instruct [args]`
- LoRA training: Add `--use_peft --peft_method lora` to training command
- Full model training: Use without PEFT args
- Benchmark: `python3 accuracy_benchmark.py` or `python3 accuracy_benchmark_synthetic.py`
- Dataset tokenization: `python3 tokenize_dataset.py --dataset "custom_dataset"`

## Style Guidelines
- **Imports**: stdlib → third-party → local modules
- **Naming**: snake_case for functions/variables, PascalCase for classes
- **Documentation**: Add comments for complex logic
- **Error handling**: Use try/except blocks for data processing and predictions
- **Parameters**: Define training hyperparameters via command-line arguments
- **Training**: Prefer LoRA for parameter-efficient fine-tuning when possible
- **Distribution**: Use FSDP with `--enable_fsdp` for multi-GPU training

Always check configs before running distributed training or benchmarks.