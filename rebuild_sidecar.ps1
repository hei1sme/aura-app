# Rebuild the Python sidecar binary
# Run this after making changes to any Python files in src-python/

Write-Host "🐍 Rebuilding Python sidecar..." -ForegroundColor Cyan

Set-Location "$PSScriptRoot\src-python"

pyinstaller --onefile --clean `
  --name aura-sidecar-x86_64-pc-windows-msvc `
  --distpath ../src-tauri `
  main.py

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Sidecar rebuilt successfully!" -ForegroundColor Green
    Write-Host "   Now restart: npm run tauri dev" -ForegroundColor White
} else {
    Write-Host "❌ Build failed!" -ForegroundColor Red
    exit 1
}

Set-Location $PSScriptRoot
