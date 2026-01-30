#!/bin/bash

# Directory for installation
INSTALL_DIR="$HOME/.local/share/goal-up"
BIN_DIR="$HOME/.local/bin"
APP_DIR="$HOME/.local/share/applications"
ICON_DIR="$HOME/.local/share/icons/hicolor/128x128/apps"

echo "Installing Goal UP..."

# Create directories
mkdir -p "$INSTALL_DIR"
mkdir -p "$BIN_DIR"
mkdir -p "$APP_DIR"
mkdir -p "$ICON_DIR"

# Copy source files
echo "Copying application files..."
cp main.py window.py goal_row.py storage.py edit_dialog.py summary_widget.py notification_manager.py "$INSTALL_DIR/"

# Copy icon
echo "Installing icon..."
cp icon.png "$ICON_DIR/goal-up.png"
cp icon.png "$INSTALL_DIR/icon.png" # Fallback for local search path

# Copy desktop file
echo "Installing desktop entry..."
cp goal-up.desktop "$APP_DIR/"

# Update desktop database
echo "Updating desktop database..."
update-desktop-database "$APP_DIR"

# Create executable wrapper
echo "Creating executable..."
cat > "$BIN_DIR/goal-up" <<EOL
#!/bin/bash
cd "$INSTALL_DIR"
python3 main.py "\$@"
EOL

chmod +x "$BIN_DIR/goal-up"

echo "Installation complete!"
echo "Run 'goal-up' or find it in your application menu."
