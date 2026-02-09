#!/bin/bash
# Setup script for PartLogic backend with Python 3.12

set -e

echo "Setting up PartLogic backend with Python 3.12..."

# Remove old venv if it exists
if [ -d "venv" ]; then
    echo "Removing old virtual environment..."
    rm -rf venv
fi

# Create new venv with Python 3.12 using clean environment
echo "Creating virtual environment with Python 3.12..."
env -i /usr/bin/python3.12 -m venv venv

# Fix Python symlinks if they're broken
if [ -L "venv/bin/python" ]; then
    TARGET=$(readlink venv/bin/python)
    if [[ "$TARGET" == *"cursor.AppImage"* ]] || [[ "$TARGET" == *"cursor"* ]]; then
        echo "Fixing broken Python symlinks..."
        rm -f venv/bin/python venv/bin/python3
        ln -sf /usr/bin/python3.12 venv/bin/python
        ln -sf /usr/bin/python3.12 venv/bin/python3
    fi
fi

# Upgrade pip
echo "Upgrading pip..."
venv/bin/python -m pip install --upgrade pip setuptools wheel

# Install requirements
echo "Installing requirements..."
venv/bin/pip install -r requirements.txt

echo ""
echo "✅ Setup complete!"
echo ""
echo "To activate the virtual environment, run:"
echo "  source venv/bin/activate"
echo ""
echo "Then start the server with:"
echo "  uvicorn app.main:app --reload --port 8000"
