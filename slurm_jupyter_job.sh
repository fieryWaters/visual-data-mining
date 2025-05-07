#!/bin/bash
# This slurm job allows the user to start a jupyter notebook on the remote SFSU Cluster and get access to the GPUs
#SBATCH --partition=gpucluster
#    SBATCH --qos=interactive #this broke jupyter notebook
#SBATCH --time=04:00:00
#SBATCH --nodes=1
#SBATCH --job-name=slurm_jupyter
#SBATCH --output=jupyter_%j.log  # %j is the job ID

# Ensure jupyter_venv exists before activating
REPO_PATH=~/git-repos/visual-data-mining
if [ ! -d "$REPO_PATH/jupyter_venv" ]; then
    echo "Jupyter virtual environment not found, creating it now..."
    cd $REPO_PATH
    python3.11 -m venv jupyter_venv || python3 -m venv jupyter_venv
    ./jupyter_venv/bin/pip install -r requirements.txt
    ./jupyter_venv/bin/pip install jupyter notebook
fi

echo Activate environment
source $REPO_PATH/jupyter_venv/bin/activate

# Try to read previous port from jupyter_info file
PREV_PORT=8888
if [ -f ~/.jupyter_info ]; then
    PREV_PORT=$(grep "^PORT=" ~/.jupyter_info | cut -d'=' -f2)
fi

# Try the previous port first, then find a free one if needed
PORT=$(python3 -c "
import socket
def try_port(port):
    try:
        s = socket.socket()
        s.bind(('', port))
        return port
    except OSError:
        s = socket.socket()
        s.bind(('', 0))
        return s.getsockname()[1]
    finally:
        s.close()
print(try_port($PREV_PORT))
")

# Save all connection info in one file
echo "JOB_ID=$SLURM_JOB_ID" > ~/.jupyter_info
echo "PORT=$PORT" >> ~/.jupyter_info
echo "NODE=$(hostname)" >> ~/.jupyter_info

# Start Jupyter and save the token
jupyter notebook --no-browser --port=$PORT --ip=0.0.0.0 2>&1 | tee -a ~/.jupyter_info
