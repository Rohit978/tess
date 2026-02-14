#!/bin/bash

set -e

echo "=========================================="
echo "   TESS Terminal - Configurable Edition"
echo "          Installation Script"
echo "=========================================="
echo

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 is not installed"
    echo "Please install Python 3.8 or higher"
    exit 1
fi

echo "[1/3] Python found: $(python3 --version)"
echo

# Install dependencies
echo "[2/3] Installing dependencies..."
pip3 install -r requirements.txt
echo

echo "[3/3] Installation complete!"
echo
echo "=========================================="
echo "  Next steps:"
echo "  1. Run: python3 -m tess_configurable --setup"
echo "  2. Follow the wizard to configure"
echo "  3. Run: python3 -m tess_configurable"
echo "=========================================="
