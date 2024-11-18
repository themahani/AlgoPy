#!/usr/bin/env bash

# Save the project directory
WORKING_DIR=$(pwd)

# Name of the virtual env to be created
VENV_NAME="venv"

# The python executable to run. You can set it to the path of your python exec as well
# Example: "/usr/bin/python"
PYTHON="python"

if [[ ! -x "$(command -v "${PYTHON}")" ]]
then
    PYTHON="python3";
elif [[ ! -x "$(command -v "${PYTHON}")" ]]
then
    echo "[!ERROR] Python executable not found...";
fi

if [[ -z "$WORKING_DIR/requirements.txt" ]]
then
    echo "Requirements file not found!";
    return -1;
fi

cd $WORKING_DIR;

# Create the virtual environment
if [[ ! -d "$WORKING_DIR/$VENV_NAME" ]]
then
    $PYTHON -m venv $VENV_NAME;
    # Switch to the newly created Python env
    source "$VENV_NAME/bin/activate";
    echo "$(which python)";
    # Install required packages using pip
    pip install -r "$WORKING_DIR/requirements.txt";
fi


