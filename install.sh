#!/usr/bin/env bash
# ShrinkWrap Automated Installer
# Usage: curl -fsSL https://raw.githubusercontent.com/shrinkwrap-mcp/shrinkwrap/main/install.sh | bash

set -e

echo "🎁 Installing ShrinkWrap (shrinkwrap-mcp)..."

# Ensure python3 and pip are available
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: python3 is required to install ShrinkWrap."
    exit 1
fi

python3 -m pip install --upgrade shrinkwrap-mcp || python3 -m pip install -e .

echo "⚡ Wrapping active local MCP client configurations..."
shrinkwrap install

echo ""
echo "✅ ShrinkWrap installation & wrapping complete!"
echo "Run 'shrinkwrap status' to verify your active adapters."
