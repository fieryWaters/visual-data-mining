#!/bin/bash
# Auto-register all UV projects as Jupyter kernels

echo "Registering Jupyter kernels for UV projects..."

find . -name "pyproject.toml" -type f -not -path "*/site-packages/*" | while read -r project_file; do
    project_dir=$(dirname "$project_file")
    kernel_name=$(echo "$project_dir" | sed 's|\./||' | sed 's|/|-|g' | sed 's|^$|root|')
    
    echo "Found: $project_dir -> $kernel_name"
    
    cd "$project_dir"
    uv add ipykernel
    uv run ipython kernel install --user --env VIRTUAL_ENV $(pwd)/.venv --name="$kernel_name"
    cd - > /dev/null
done

echo "Done! Start Jupyter and select kernels from dropdown."