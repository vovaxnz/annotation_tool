#!/bin/bash 

# Causes the script to exit if any command exits with a non-zero status
set -e

# Select non-conda python interpreter
PYTHON_INTERPRETER=$(type -p python3)

# Install Homebrew if not installed (macOS package manager)
if ! command -v brew >/dev/null; then
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
fi

# Install dependencies using Homebrew
brew install python3

# Python might be installed via Homebrew but ensure pip & venv are installed
python3 -m ensurepip --upgrade
python3 -m pip install --upgrade pip
python3 -m pip install virtualenv

# Copy and install font
mkdir -p ~/Library/Fonts
cp UbuntuCondensed-Regular.ttf ~/Library/Fonts/

# Create and activate venv
python3 -m venv venv
source venv/bin/activate

pip install -r requirements.txt

echo "To start your application, navigate to the project directory and run:"
echo "source venv/bin/activate"
echo "python3 app.py"