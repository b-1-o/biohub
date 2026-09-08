#!/usr/bin/env bash

set -e

REPO_URL="https://github.com/b-1-o/biohub"
INSTALL_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/biohub"
BIN_DIR="${HOME}/.local/bin"
DESKTOP_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/applications"

echo
echo "======================================"
echo "          BioHub Installer"
echo "======================================"
echo

# ------------------------------------------------------------
# Check Python
# ------------------------------------------------------------

if ! command -v python3 >/dev/null 2>&1; then
    echo "Error: Python 3 is required."
    echo "Please install Python 3.10 or newer and try again."
    exit 1
fi

python3 - <<'PY'
import sys

if sys.version_info < (3, 10):
    print("Error: BioHub requires Python 3.10 or newer.")
    sys.exit(1)

print(
    f"==> Python {sys.version_info.major}."
    f"{sys.version_info.minor} detected."
)
PY

# ------------------------------------------------------------
# Check curl
# ------------------------------------------------------------

if ! command -v curl >/dev/null 2>&1; then
    echo "Error: curl is required."
    echo "Please install curl and try again."
    exit 1
fi

# ------------------------------------------------------------
# Prepare directories
# ------------------------------------------------------------

echo "==> Preparing installation..."

mkdir -p "$INSTALL_DIR"
mkdir -p "$BIN_DIR"
mkdir -p "$DESKTOP_DIR"

# ------------------------------------------------------------
# Download source
# ------------------------------------------------------------

ARCHIVE_URL="${REPO_URL}/archive/refs/heads/main.tar.gz"

TMP_DIR="$(mktemp -d)"

cleanup() {
    rm -rf "$TMP_DIR"
}

trap cleanup EXIT

echo "==> Downloading BioHub..."

curl -fL --progress-bar "$ARCHIVE_URL" \
    -o "$TMP_DIR/biohub.tar.gz"

echo "==> Extracting..."

tar -xzf "$TMP_DIR/biohub.tar.gz" -C "$TMP_DIR"

SOURCE_DIR="$TMP_DIR/biohub-main"

if [ ! -d "$SOURCE_DIR" ]; then
    echo "Error: Failed to extract BioHub."
    exit 1
fi

# ------------------------------------------------------------
# Update installation
# ------------------------------------------------------------

echo "==> Updating installation..."

rm -rf "$INSTALL_DIR"
mkdir -p "$INSTALL_DIR"

cp -a "$SOURCE_DIR/." "$INSTALL_DIR/"

# ------------------------------------------------------------
# Create virtual environment
# ------------------------------------------------------------

echo "==> Creating virtual environment..."

python3 -m venv "$INSTALL_DIR/.venv"

# ------------------------------------------------------------
# Install BioHub
# ------------------------------------------------------------

echo "==> Installing BioHub and dependencies..."

"$INSTALL_DIR/.venv/bin/python" -m pip install --upgrade pip

"$INSTALL_DIR/.venv/bin/pip" install \
    --upgrade \
    "$INSTALL_DIR"

# ------------------------------------------------------------
# Create launchers
# ------------------------------------------------------------

echo "==> Creating launchers..."

cat > "$BIN_DIR/biohub" <<EOF
#!/usr/bin/env bash
exec "$INSTALL_DIR/.venv/bin/biohub" "\$@"
EOF

cat > "$BIN_DIR/hub" <<EOF
#!/usr/bin/env bash
exec "$INSTALL_DIR/.venv/bin/hub" "\$@"
EOF

cat > "$BIN_DIR/hub-desktop" <<EOF
#!/usr/bin/env bash
exec "$INSTALL_DIR/.venv/bin/hub-desktop" "\$@"
EOF

chmod +x \
    "$BIN_DIR/biohub" \
    "$BIN_DIR/hub" \
    "$BIN_DIR/hub-desktop"

# ------------------------------------------------------------
# Desktop entry
# ------------------------------------------------------------

echo "==> Installing application launcher..."

cat > "$DESKTOP_DIR/biohub.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=BioHub
Comment=Personal Command Center
Exec=$BIN_DIR/biohub %F
Icon=applications-utilities
Terminal=false
Categories=Utility;
StartupWMClass=biohub
X-GNOME-SingleWindow=true
StartupNotify=true
EOF

chmod 644 "$DESKTOP_DIR/biohub.desktop"

# ------------------------------------------------------------
# Update desktop database
# ------------------------------------------------------------

if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database "$DESKTOP_DIR" >/dev/null 2>&1 || true
fi

if command -v gio >/dev/null 2>&1; then
    gio mime x-scheme-handler/application-x-executable >/dev/null 2>&1 || true
fi

# ------------------------------------------------------------
# PATH notice
# ------------------------------------------------------------

case ":$PATH:" in
    *":$BIN_DIR:"*)
        ;;
    *)
        echo
        echo "NOTE:"
        echo "$BIN_DIR is not currently in your PATH."
        echo "Add it to your shell configuration if needed:"
        echo
        echo '  fish_add_path ~/.local/bin'
        echo
        ;;
esac

# ------------------------------------------------------------
# Done
# ------------------------------------------------------------

echo
echo "======================================"
echo "       BioHub installed successfully!"
echo "======================================"
echo
echo "Launch from your application menu:"
echo "  BioHub"
echo
echo "Or from terminal:"
echo "  biohub"
echo
echo "Installation:"
echo "  $INSTALL_DIR"
echo
