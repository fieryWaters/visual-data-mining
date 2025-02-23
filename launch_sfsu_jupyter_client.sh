#!/bin/bash
# Run this from your local machine to initiate starting the jupyter notebook
# on the remote machine and then forwarding the port so you can access the URL
# on localhost
# IMPORTANT
# this script assumes you already have ssh keys setup 
#    (IE the "ssh sfsu" command will log you into the cluster)
# Also assumes you are connected to the SFSU VPN

# Function to check if job is running
check_job_status() {
    local job_id=$1
    local status=$(ssh sfsu "squeue -j $job_id -h -o %t" 2>/dev/null)
    echo $status
}

# Function to get connection details from existing job
get_connection_details() {
    local job_id=$1
    # Read from our consolidated info file
    local info=$(ssh sfsu "cat ~/.jupyter_info")
    local node=$(echo "$info" | grep "^NODE=" | cut -d'=' -f2)
    local port=$(echo "$info" | grep "^PORT=" | cut -d'=' -f2)
    local token=$(echo "$info" | grep -m1 "token=" | sed -n 's/.*token=\([^&]*\).*/\1/p')
    echo "$node:$port:$token"
}

# Check for existing job
echo "Checking for existing Jupyter session..."
EXISTING_JOB_ID=$(ssh sfsu "grep '^JOB_ID=' ~/.jupyter_info 2>/dev/null | cut -d'=' -f2")
EXISTING_STATUS=""
if [ ! -z "$EXISTING_JOB_ID" ]; then
    EXISTING_STATUS=$(check_job_status $EXISTING_JOB_ID)
fi

if [ "$EXISTING_STATUS" == "R" ]; then
    echo "Found running Jupyter session, reconnecting..."
    # Get connection details from existing session
    CONNECTION_INFO=$(get_connection_details $EXISTING_JOB_ID)
    NODE=$(echo $CONNECTION_INFO | cut -d':' -f1)
    PORT=$(echo $CONNECTION_INFO | cut -d':' -f2)
    TOKEN=$(echo $CONNECTION_INFO | cut -d':' -f3)
else
    echo "No active session found. Starting new Jupyter job..."
    # Submit new job
    JOB_ID=$(ssh sfsu "sbatch ~/git-repos/visual-data-mining/slurm_jupyter_job.sh" | awk '{print $4}') || exit 1
    echo "Submitted job ID: $JOB_ID"
    
    # Wait for job to start
    while true; do
        status=$(check_job_status $JOB_ID)
        if [ "$status" == "R" ]; then
            echo "Job is running!"
            break
        elif [ -z "$status" ]; then
            echo "Job failed to start. Check jupyter_${JOB_ID}.log on SFSU"
            exit 1
        fi
        echo "Job status: $status (waiting for R)"
        sleep 3
    done
    
    # Give Jupyter a moment to write its files
    sleep 5
    
    # Get connection details
    CONNECTION_INFO=$(get_connection_details $JOB_ID)
    NODE=$(echo $CONNECTION_INFO | cut -d':' -f1)
    PORT=$(echo $CONNECTION_INFO | cut -d':' -f2)
    TOKEN=$(echo $CONNECTION_INFO | cut -d':' -f3)
fi

# Display connection information
echo -e "\nJupyter is running!"
echo "Node: $NODE"
echo "Port: $PORT"
echo -e "\nConnection URLs:"
echo "Local machine URL: http://localhost:$PORT/?token=$TOKEN"
echo "http://localhost:$PORT/?token=$TOKEN"
echo -e "\nVSCode remote development URL:"
echo "http://$NODE:$PORT/?token=$TOKEN"

# Display job management commands
echo -e "\nJob Management:"
echo "Check status: ssh sfsu \"squeue -j $EXISTING_JOB_ID\""
echo "View logs:    ssh sfsu \"cat jupyter_${EXISTING_JOB_ID}.log\""
echo "Kill job:     ssh sfsu \"scancel $EXISTING_JOB_ID\""

# Establish SSH tunnel
echo -e "\nEstablishing SSH tunnel (keep this terminal open)..."
max_retries=5
retry_count=0
while [ $retry_count -lt $max_retries ]; do
    if ssh -N -L "$PORT:$NODE:$PORT" sfsu; then
        break
    fi
    if [ $? -eq 130 ]; then  # Ctrl+C was pressed
        break
    fi
    echo "Connection failed, retrying in 3 seconds..."
    sleep 3
    retry_count=$((retry_count + 1))
done