#!/bin/bash

# Function to prompt user for yes/no response
ask_yes_no() {
    local prompt=$1
    local response
    while true; do
        read -p "$prompt (y/n): " response
        case $response in
            [Yy]* ) return 0;;
            [Nn]* ) return 1;;
            * ) echo "Please answer yes (y) or no (n).";;
        esac
    done
}

# Function to check command execution status
check_command() {
    if [ $? -ne 0 ]; then
        echo "Error: $1"
        exit 1
    fi
}

# Display initial information
echo "==== SFSU HPC Cluster Setup ===="
echo "Documentation: https://athelp.sfsu.edu/hc/en-us/articles/31706916588819-Accessing-the-High-Performance-Computing-HPC-cluster"
echo
echo "Prerequisites:"
echo "1. Connect to SFSU VPN"
echo "2. Have HPC cluster authorization"
echo "3. Test cluster access with: ssh YOUR_STUDENT_ID@n1.hpc.at.sfsu.edu"
echo "4. SFSU password required"
echo "5. WSL required for Windows users (no PuTTY)"
echo
echo "IMPORTANT:"
echo "- key file MUST be named 'sfsu' for script compatibility"
echo "- username is YOUR_STUDENT_ID"
echo "- ip address of remote host is n1.hpc.at.sfsu.edu"

# Ask to proceed
if ! ask_yes_no "Would you like to proceed with the setup?"; then
    echo "Setup cancelled."
    exit 0
fi

# Setup SSH keys
echo -e "\n==== Setting up SSH keys ===="
check_command "Failed to setup SSH keys"

# Verify SSH setup
if ! ask_yes_no "Did the SSH key setup complete successfully? open another terminal and type \"ssh sfsu\""; then
    echo "SSH key setup failed. Please check the error messages above and try again."
    exit 1
fi

# Setup Github keys
echo -e "\n==== Setting up Github keys ===="
echo "for some reason the following script will pause sometimes until you press enter once or twice" 
ssh sfsu "mkdir -p ~/.ssh && chmod 700 ~/.ssh"
scp setupGithubKeys.sh sfsu:~/.ssh/
ssh sfsu "chmod +x ~/.ssh/setupGithubKeys.sh && cd ~/.ssh && ./setupGithubKeys.sh"
#check_command "Failed to setup Github keys"

# Verify Github setup
if ! ask_yes_no "Did the Github key setup complete successfully?"; then
    echo "Github key setup failed. Please check the error messages above and try again."
    exit 1
fi

# Create git-repos directory and clone repository
echo -e "\n==== Setting up repository ===="
ssh sfsu "mkdir -p ~/git-repos"
#check_command "Failed to create git-repos directory"

echo "cloning fieryWaters/visual-data-mining, ensure you have access"
ssh sfsu "cd ~/git-repos && git clone git@github.com:fieryWaters/visual-data-mining.git"
#check_command "Failed to clone repository"

# Run virtual environment setup
echo -e "\n==== Setting up virtual environment ===="
echo "Warning: This process may take a while..."
ssh sfsu "cd ~/git-repos/visual-data-mining && ./setup_activate_venv.sh"
#check_command "Failed to setup virtual environment"

# Final instructions
echo -e "\n==== Setup Complete ===="
echo "To use the Jupyter notebook:"
echo "1. Run launch_sfsu_jupyter_client.sh from your local machine"
echo "2. Open the URL provided in your web browser"
echo "You can now access the cluster shell with: ssh sfsu"
echo "Setup completed successfully!"
