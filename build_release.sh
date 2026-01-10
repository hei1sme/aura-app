#!/bin/bash

echo "🌟 Starting Aura Release Build..."

# 1. Clean Python
echo "🧹 Cleaning Python build files..."
cd src-python
rm -rf build dist __pycache__ *.spec

# 2. Build Sidecar
echo "🐍 Compiling Python Sidecar..."
pyinstaller --onefile --clean --name aura-sidecar-x86_64-pc-windows-msvc --distpath ../src-tauri main.py

if [ $? -ne 0 ]; then
    echo "❌ Sidecar build failed!"
    exit 1
fi

cd ..

# 3. Build Tauri
echo "🦀 Building Tauri Installer (NSIS)..."
npm run tauri build

if [ $? -eq 0 ]; then
    echo "✅ Build Success!"
    echo "📂 Installer located at: src-tauri/target/release/bundle/nsis"
else
    echo "❌ Tauri build failed!"
    exit 1
fi
