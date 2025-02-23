#this script activates the gpu node on the SFSU HPC Cluster when using an SSH sesstion 
srun --pty --qos=interactive --time=04:00:00 --partition=gpucluster --nodes=1 bash
