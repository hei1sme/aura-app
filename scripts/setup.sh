#!/bin/bash
# Aura Development Setup Script

set -e

echo "🌟 Setting up Aura Development Environment..."

# Check for Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is required but not installed."
    exit 1
fi

# Check for Node.js
if ! command -v node &> /dev/null; then
    echo "❌ Node.js is required but not installed."
    exit 1
fi

# Check for Rust
if ! command -v cargo &> /dev/null; then
    echo "❌ Rust is required but not installed."
    echo "   Install from: https://rustup.rs"
    exit 1
fi

echo "✅ All prerequisites found!"

# Install Node dependencies
echo "📦 Installing Node.js dependencies..."
npm install

# Setup Python virtual environment
echo "🐍 Setting up Python virtual environment..."
cd src-python
python3 -m venv .venv

# Activate and install Python dependencies
if [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "win32" ]]; then
    source .venv/Scripts/activate
else
    source .venv/bin/activate
fi

pip install --upgrade pip
pip install -r requirements.txt

cd ..

echo ""
echo "✨ Setup complete!"
echo ""
echo "To start development:"
echo "  npm run tauri dev"
echo ""
echo "For Python sidecar development (standalone):"
echo "  cd src-python && source .venv/bin/activate && python main.py"
