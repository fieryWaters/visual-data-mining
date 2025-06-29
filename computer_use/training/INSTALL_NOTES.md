# LLaMA Factory Installation on SFSU HPC Cluster

## Prerequisites
- Access to SFSU HPC cluster
- GPU node access

## Installation Steps

### 1. Install UV Package Manager
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
uv python pin --global 3.11
```

### 2. Activate GPU Node
```bash
./activate_gpu.sh
```

### 3. Launch Web UI with Public Share
```bash
GRADIO_SHARE=1 uvx --python 3.11 --from "git+https://github.com/hiyouga/LLaMA-Factory.git[torch,metrics]" llamafactory-cli webui
```

This will output a public URL like `https://xxxxx.gradio.live` that you can access from any browser without port forwarding.

## Notes
- The Gradio share link is active for 72 hours
- UVX automatically manages the environment - no setup or project files needed
- Each run downloads and installs LLaMA Factory fresh (cached after first run)
- The activate_gpu.sh script handles the SLURM GPU allocation