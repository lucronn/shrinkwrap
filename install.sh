#!/usr/bin/env bash
# ShrinkWrap Automated Installer
# Usage: curl -fsSL https://raw.githubusercontent.com/lucronn/shrinkwrap/main/install.sh | bash


set -e

echo "🎁 Installing ShrinkWrap (shrinkwrap-cli)..."

# Install into a stable virtual environment (also works on externally managed Python installations).
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: python3 is required to install ShrinkWrap."
    exit 1
fi

install_dir="${XDG_DATA_HOME:-$HOME/.local/share}/shrinkwrap"
python3 -m venv "$install_dir/venv"
"$install_dir/venv/bin/python" -m pip install --upgrade shrinkwrap-cli

echo "⚡ Wrapping active local MCP client configurations..."
"$install_dir/venv/bin/python" -m shrinkwrap.cli install

echo ""
echo "✅ ShrinkWrap installation & wrapping complete!"
echo "Run '$install_dir/venv/bin/python -m shrinkwrap.cli status' to verify the installed version."
