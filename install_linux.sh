#!/bin/bash 

# Causes the script to exit if any command exits with a non-zero status
set -e

# Select non-conda python interpeter
PYTHON_INTERPRETER=$(type -a python3 | grep -v 'conda' | head -n 1 | awk '{print $NF}')

# Install venv
PYTHON_VERSION=$($PYTHON_INTERPRETER --version | grep -oP 'Python \K\d+\.\d+')
VENV_PACKAGE_NAME="python${PYTHON_VERSION}-venv"
echo $VENV_PACKAGE_NAME
sudo apt install -y "$VENV_PACKAGE_NAME"

sudo apt install python3-tk python3-venv python3-pip -y

# Copy and install font
mkdir -p ~/.fonts
cp UbuntuCondensed-Regular.ttf ~/.fonts/
fc-cache -f -v

# Create and activate venv
python3 -m venv venv
source venv/bin/activate

pip install -r requirements.txt

# Create desktop shortcut
CURRENT_DIR=$(pwd)
DESKTOP_PATH=$(xdg-user-dir DESKTOP)
DESKTOP_FILE="$DESKTOP_PATH/Labeling.desktop"
cat > "$DESKTOP_FILE" << EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=EG Labeling
Exec=bash -c 'PYTHONPATH=$CURRENT_DIR $(which python3) $CURRENT_DIR/app.py'
Icon=$CURRENT_DIR/icon.png
Terminal=false
StartupNotify=true
EOF
chmod +x "$DESKTOP_FILE"

echo "Go to the Desktop, right click on the Labeling.desktop file and click Allow Launching and press ENTER to continue"
read _

echo "Congratulations, now you can use the annotation tool!"
