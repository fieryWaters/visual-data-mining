#!/bin/bash
# Run this from your local machine to initiate starting the jupyter notebook
# on the remote machine and then forwarding the port so you can access the URL
# on localhost
# IMPORTANT
# this script assumes you already have ssh keys setup 
#    (IE the "ssh sfsu" command will log you into the cluster)
# Also assumes you are connected to the SFSU VPN

# Get the status of a SLURM job (R=running, PD=pending, etc)
check_job_status() {
    local job_id=$1
    local status=$(ssh sfsu "squeue -j $job_id -h -o %t" 2>/dev/null)
    echo $status
}

# Parse the jupyter_info file to get connection details
# Returns them in format: node:port:token
get_connection_details() {
    local job_id=$1
    
    # Get all info from the consolidated file
    local info=$(ssh sfsu "cat ~/.jupyter_info")
    
    # Extract each piece using 'cut':
    # -d'=' means split at equals sign
    # -f2 means take the second piece
    local node=$(echo "$info" | grep "^NODE=" | cut -d'=' -f2)
    local port=$(echo "$info" | grep "^PORT=" | cut -d'=' -f2)
    
    # Extract token using sed because it's a more complex pattern
    local token=$(echo "$info" | grep -m1 "token=" | sed -n 's/.*token=\([^&]*\).*/\1/p')
    
    echo "$node:$port:$token"
}

# Check for existing job
echo "Checking for existing Jupyter session..."

# Get job ID from the info file, suppressing any errors with 2>/dev/null
EXISTING_JOB_ID=$(ssh sfsu "grep '^JOB_ID=' ~/.jupyter_info 2>/dev/null | cut -d'=' -f2")
EXISTING_STATUS=""

if [ ! -z "$EXISTING_JOB_ID" ]; then
    EXISTING_STATUS=$(check_job_status $EXISTING_JOB_ID)
fi

if [ "$EXISTING_STATUS" == "R" ]; then
    echo "Found running Jupyter session, reconnecting..."
    
    # Get connection details from existing session
    CONNECTION_INFO=$(get_connection_details $EXISTING_JOB_ID)
    
    # Split CONNECTION_INFO at colons into node, port, token
    NODE=$(echo $CONNECTION_INFO | cut -d':' -f1)
    PORT=$(echo $CONNECTION_INFO | cut -d':' -f2)
    TOKEN=$(echo $CONNECTION_INFO | cut -d':' -f3)
else
    echo "No active session found. Starting new Jupyter job..."
    
    # Submit new job - awk '{print $4}' extracts just the job ID from SLURM output
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
    
    # Wait for token to appear in jupyter_info file
    echo "Waiting for Jupyter token..."
    while ! ssh sfsu "grep -q token ~/.jupyter_info"; do sleep 5; echo "Still waiting..."; done
    
    # Get connection details
    CONNECTION_INFO=$(get_connection_details $JOB_ID)
    NODE=$(echo $CONNECTION_INFO | cut -d':' -f1)
    PORT=$(echo $CONNECTION_INFO | cut -d':' -f2)
    TOKEN=$(echo $CONNECTION_INFO | cut -d':' -f3)
fi

# Display connection information
echo -e "\nJupyter is running!"
echo -e "\nConnection URLs:"
echo "Local machine URL: "
echo "http://localhost:$PORT/?token=$TOKEN"
echo -e "\nVSCode remote development URL:"
echo "http://$NODE:$PORT/?token=$TOKEN"

# Display job management commands
echo -e "\nJob Management:"
echo "Check status: ssh sfsu \"squeue -j $EXISTING_JOB_ID\""
echo "View logs:    ssh sfsu \"cat jupyter_${EXISTING_JOB_ID}.log\""
echo "Kill job:     ssh sfsu \"scancel $EXISTING_JOB_ID\""

# Set up SSH tunnel - will exit immediately on Ctrl+C
echo -e "\nEstablishing SSH tunnel (keep this terminal open)..."
ssh -N -L "$PORT:$NODE:$PORT" sfsu