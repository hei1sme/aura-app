#!/bin/bash
# Rebuild the Python sidecar binary
# Run this after making changes to any Python files in src-python/

echo "🐍 Rebuilding Python sidecar..."

cd "$(dirname "$0")/src-python" || exit 1

pyinstaller --onefile --clean \
  --name aura-sidecar-x86_64-pc-windows-msvc \
  --distpath ../src-tauri \
  main.py

if [ $? -eq 0 ]; then
  echo "✅ Sidecar rebuilt successfully!"
  echo "   Now restart: npm run tauri dev"
else
  echo "❌ Build failed!"
  exit 1
fi
