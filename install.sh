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
cp main.py window.py goal_row.py storage.py edit_dialog.py summary_widget.py timeline_widget.py trend_widget.py notification_manager.py gtk_dark.css gtk_light.css "$INSTALL_DIR/"

# Copy icon
echo "Installing icon..."
cp icon.png "$ICON_DIR/goal-up.png"
cp icon.png "$INSTALL_DIR/icon.png" # Fallback for local search path

# Copy theme asset icons referenced in gtk_* CSS files (required by libadwaita style rules)
ASSETS_DIR="$INSTALL_DIR/assets"
mkdir -p "$ASSETS_DIR"
for name in checkbox-checked-symbolic.svg checkbox-mixed-symbolic.svg radio-checked-symbolic.svg radio-mixed-symbolic.svg; do
  src=$(find /usr/share/icons -name "$name" 2>/dev/null | head -n 1)
  if [[ -n "$src" ]]; then
    cp "$src" "$ASSETS_DIR/"
  else
    # fallback to blank icon to avoid missing-resource errors
    cat > "$ASSETS_DIR/$name" <<EOL
<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16"></svg>
EOL
  fi
done
for name in small-checkbox-checked-symbolic.svg small-checkbox-mixed-symbolic.svg small-radio-checked-symbolic.svg small-radio-mixed-symbolic.svg; do
  if [[ -f "$ASSETS_DIR/${name#small-}" ]]; then
    ln -sf "${name#small-}" "$ASSETS_DIR/$name"
  else
    cat > "$ASSETS_DIR/$name" <<EOL
<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16"></svg>
EOL
  fi
done
if [[ ! -f "$ASSETS_DIR/cursor-handle-symbolic.svg" ]]; then
  cat > "$ASSETS_DIR/cursor-handle-symbolic.svg" <<EOL
<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16"></svg>
EOL
fi

# Update icon cache so desktop environments pick up the new icon immediately
if command -v gtk-update-icon-cache >/dev/null 2>&1; then
  echo "Updating icon cache..."
  # ICON_DIR is .../hicolor/128x128/apps, so go up two levels to .../hicolor
  gtk-update-icon-cache -f -t "$(dirname "$(dirname "$ICON_DIR")")" || true
fi

# Copy desktop file
echo "Installing desktop entry..."
cp goal-up.desktop "$APP_DIR/"

# Ensure desktop entry points to local icon and has wm class for GNOME
DESKTOP_FILE="$APP_DIR/goal-up.desktop"
sed -i "s|^Icon=.*|Icon=$INSTALL_DIR/icon.png|" "$DESKTOP_FILE"
if ! grep -q '^StartupWMClass=' "$DESKTOP_FILE"; then
  echo 'StartupWMClass=GoalUp' >> "$DESKTOP_FILE"
fi
if ! grep -q '^X-GNOME-UsesNotifications=' "$DESKTOP_FILE"; then
  echo 'X-GNOME-UsesNotifications=true' >> "$DESKTOP_FILE"
fi

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
