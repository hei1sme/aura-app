#!/bin/bash
# Aura Build Script

set -e

echo "🔨 Building Aura..."

# Build Python sidecar with PyInstaller
echo "📦 Building Python sidecar..."
cd src-python

# Activate virtual environment
if [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "win32" ]]; then
    source .venv/Scripts/activate
else
    source .venv/bin/activate
fi

# Install PyInstaller if not present
pip install pyinstaller

# Build the sidecar binary
# The binary name must match the pattern: <name>-<target-triple>
# For Windows: aura-engine-x86_64-pc-windows-msvc.exe
# For macOS: aura-engine-x86_64-apple-darwin or aura-engine-aarch64-apple-darwin
pyinstaller --onefile --name aura-engine main.py

cd ..

# Create binaries directory in src-tauri
mkdir -p src-tauri/binaries

# Copy binary with correct target triple name
if [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "win32" ]]; then
    cp src-python/dist/aura-engine.exe src-tauri/binaries/aura-engine-x86_64-pc-windows-msvc.exe
elif [[ "$OSTYPE" == "darwin"* ]]; then
    # Check architecture
    if [[ $(uname -m) == "arm64" ]]; then
        cp src-python/dist/aura-engine src-tauri/binaries/aura-engine-aarch64-apple-darwin
    else
        cp src-python/dist/aura-engine src-tauri/binaries/aura-engine-x86_64-apple-darwin
    fi
else
    cp src-python/dist/aura-engine src-tauri/binaries/aura-engine-x86_64-unknown-linux-gnu
fi

echo "✅ Python sidecar built!"

# Build Tauri app
echo "🦀 Building Tauri application..."
npm run tauri build

echo ""
echo "✨ Build complete!"
echo "   Check src-tauri/target/release for the output"
