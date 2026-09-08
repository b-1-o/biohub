#!/usr/bin/env bash

set -e

INSTALL_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/biohub"
BIN_DIR="${HOME}/.local/bin"
DESKTOP_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/applications"

echo
echo "======================================"
echo "         BioHub Uninstaller"
echo "======================================"
echo

echo "==> Removing BioHub installation..."

rm -rf "$INSTALL_DIR"

echo "==> Removing launchers..."

rm -f \
    "$BIN_DIR/biohub" \
    "$BIN_DIR/hub" \
    "$BIN_DIR/hub-desktop"

echo "==> Removing desktop entry..."

rm -f "$DESKTOP_DIR/biohub.desktop"

if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database "$DESKTOP_DIR" >/dev/null 2>&1 || true
fi

echo
echo "======================================"
echo "       BioHub removed successfully!"
echo "======================================"
echo
