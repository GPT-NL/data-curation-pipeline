#!/usr/bin/bash
# 
# When logging to snellius, the environment will be "empty" and the necessary modules must be 
# loaded still.  This is the function of this script.  It should be executed every time you are starting 
# to work with Snellius.
#
# Furthermore, after an update of the source code, there can be new dependencies being imported. 
# These dependencies must also be installed in the virtual environment of the source code.
# This script install all the requirements in requirements.txt if they are not yet present in the 
# virtual environment.
#
# Execute this file __from the repository root__.  Elsewhere, it will probably fail.
#
module load 2023                         # Will load the parent module for all the other SW modules
module load Python/3.11.3-GCCcore-12.3.0 # Will load Python 3.11
module load CUDA/12.1.1
module load cuDNN/8.9.2.26-CUDA-12.1.1  


# Install dependencies. Poetry handles the virtual environment.
pip install --upgrade pip
pip install poetry

# Check if the virtual environment exists, if not, create it
if [ ! -d "venv" ]; then
    python -m venv venv
fi

# Activate the virtual environment
source venv/bin/activate

poetry install
if [ -f post_install.py ]; then
    poetry run python post_install.py
fi

echo "Setup complete."
