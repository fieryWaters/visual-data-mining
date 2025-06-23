# LLaMA Factory Installation on SFSU HPC Cluster

## Prerequisites
- Access to SFSU HPC cluster
- Python 3.11
- GPU node access

## Installation Steps

### 1. Clone LLaMA Factory Repository
```bash
git clone https://github.com/hiyouga/LLaMA-Factory.git
cd LLaMA-Factory
```

### 2. Create Virtual Environment with Python 3.11
```bash
python3.11 -m venv ../env
```

### 3. Activate Virtual Environment
```bash
source ../env/bin/activate
```

### 4. Install UV Package Manager
```bash
pip install uv
```

### 5. Install LLaMA Factory with UV
```bash
uv pip install -e ".[torch,metrics]"
```

### 6. Activate GPU Node
```bash
./activate_gpu.sh
```

### 7. Launch Web UI with Public Share
```bash
GRADIO_SHARE=true llamafactory-cli webui
```

This will output a public URL like `https://xxxxx.gradio.live` that you can access from any browser without port forwarding.

## Notes
- The Gradio share link is active for 72 hours
- Make sure to activate the virtual environment before running any LLaMA Factory commands
- The activate_gpu.sh script handles the SLURM GPU allocation