sudo apt install rsync python3-tk -y

pip install -r requirements.txt

# Specify .env values
cp .env.example .env
chmod 600 .env
echo "\nOpen $(realpath .env) file, enter your data into it, save and press ENTER to continue"
read _

# Create desktop shortcut
CURRENT_DIR=$(pwd)
DESKTOP_FILE="$HOME/Desktop/Labeling.desktop"
cat > "$DESKTOP_FILE" << EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=Labeling
Exec=bash -c 'PYTHONPATH=$CURRENT_DIR $(which python3) $CURRENT_DIR/app.py'
Icon=$CURRENT_DIR/icon.png
Terminal=false
StartupNotify=true
EOF
chmod +x "$DESKTOP_FILE"

echo "Go to the Desktop, right click on the Labeling.desktop file and click Allow Launching and press ENTER to continue"
read _

echo "Congratulations, now if the steps have been completed successfully, you can use the annotation tool!"