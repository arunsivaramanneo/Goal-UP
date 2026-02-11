#!/bin/bash

# Directory for installation
INSTALL_DIR="$HOME/.local/share/goal-up"
BIN_DIR="$HOME/.local/bin"
APP_DIR="$HOME/.local/share/applications"
ICON_DIR="$HOME/.local/share/icons/hicolor/128x128/apps"
EXTENSION_DIR="$HOME/.local/share/gnome-shell/extensions/goal-up@neothenoone"

echo "Installing Goal UP..."

# Create directories
mkdir -p "$INSTALL_DIR"
mkdir -p "$BIN_DIR"
mkdir -p "$APP_DIR"
mkdir -p "$ICON_DIR"
mkdir -p "$EXTENSION_DIR"

# Copy source files
echo "Copying application files..."
cp main.py window.py goal_row.py storage.py edit_dialog.py summary_widget.py timeline_widget.py trend_widget.py notification_manager.py "$INSTALL_DIR/"

# Copy icon
echo "Installing icon..."
cp icon.png "$ICON_DIR/goal-up.png"
cp icon.png "$INSTALL_DIR/icon.png" # Fallback for local search path

# Update icon cache so desktop environments pick up the new icon immediately
if command -v gtk-update-icon-cache >/dev/null 2>&1; then
  echo "Updating icon cache..."
  # ICON_DIR is .../hicolor/128x128/apps, so go up two levels to .../hicolor
  gtk-update-icon-cache -f -t "$(dirname "$(dirname "$ICON_DIR")")" || true
fi

# Copy desktop file
echo "Installing desktop entry..."
cp goal-up.desktop "$APP_DIR/"

# Copy extension files
echo "Installing GNOME extension..."
cp extension/extension.js extension/metadata.json extension/stylesheet.css "$EXTENSION_DIR/"

# Update desktop database if available
if command -v update-desktop-database >/dev/null 2>&1; then
  echo "Updating desktop database..."
  update-desktop-database "$APP_DIR" || true
fi

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
echo "Note: To enable the GNOME extension, search for 'Extensions' in your menu or run:"
echo "gnome-extensions enable goal-up@neothenoone"
echo "You may need to restart GNOME Shell (Alt+F2, then type 'r' and Enter) if it doesn't appear."
