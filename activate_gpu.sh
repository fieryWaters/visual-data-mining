#!/bin/bash
# This script activates a specific node on the SFSU HPC Cluster

# Function to show usage and node status
show_usage_and_status() {
    echo "Usage: $0 [node_name]"
    echo "Available nodes on this cluster:"
    echo "  - gpu01 (gpucluster, 4 GPUs)"
    echo "  - lmn01, lmn02, lmn03 (cpucluster)"
    echo "  - hmn01 (cputest)"
    echo ""
    echo "Current node status:"
    echo "---------------------------------------------"
    echo "HOSTNAMES = Node name"
    echo "PARTITION = Cluster partition"
    echo "CPUS(A/I/O/T) = CPUs (Allocated/Idle/Other/Total)"
    echo "GRES = Generic Resources (e.g., GPUs)"
    echo "---------------------------------------------"
    sinfo -o "%20n %10P %15C %10G" -N
    echo ""
    echo "GPU utilization:"
    timeout 5 srun --partition=gpucluster --nodelist=gpu01 --immediate nvidia-smi --query-gpu=index,utilization.gpu,memory.used,memory.total --format=csv 2>/dev/null || echo "Cannot access GPU information (not currently logged into GPU node)"
    echo ""
    echo "CPU utilization:"
    sinfo -o "%n %C" | grep -v NODELIST
}

# Show help or node options if no args or help flag
if [[ $# -eq 0 || "$1" == "-h" || "$1" == "--help" ]]; then
    show_usage_and_status
    exit 0
fi

NODE_NAME=$1
PARTITION=""

# Select appropriate partition based on node name
if [[ $NODE_NAME == lmn* ]]; then
    PARTITION="cpucluster"
elif [[ $NODE_NAME == hmn* ]]; then
    PARTITION="cputest"
else
    PARTITION="gpucluster"
fi

# Run the srun command with specified node
srun --pty --time=04:00:00 --partition=$PARTITION --nodelist=$NODE_NAME --nodes=1 bash || {
    echo "Failed to allocate node: $NODE_NAME"
    show_usage_and_status
}
