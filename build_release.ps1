# build_release.ps1

Write-Host "🌟 Starting Aura Release Build..." -ForegroundColor Cyan

# 1. Clean Python Artifacts
Write-Host "🧹 Cleaning Python build files..." -ForegroundColor Yellow
Set-Location "src-python"
if (Test-Path "build") { Remove-Item -Recurse -Force "build" }
if (Test-Path "dist") { Remove-Item -Recurse -Force "dist" }
if (Test-Path "__pycache__") { Remove-Item -Recurse -Force "__pycache__" }
if (Test-Path "*.spec") { Remove-Item -Force "*.spec" }

# 2. Build Python Sidecar (Fresh)
Write-Host "🐍 Compiling Python Sidecar..." -ForegroundColor Yellow
pyinstaller --onefile --clean --name aura-sidecar-x86_64-pc-windows-msvc --distpath ../src-tauri main.py

if ($LASTEXITCODE -ne 0) {
    Write-Error "❌ Sidecar build failed!"
    exit 1
}

Set-Location ".."

# 3. Build Tauri Bundle
Write-Host "🦀 Building Tauri Installer (NSIS)..." -ForegroundColor Yellow
# This runs the production build pipeline
npm run tauri build

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Build Success!" -ForegroundColor Green
    Write-Host "📂 Installer located at: src-tauri\target\release\bundle\nsis" -ForegroundColor White
} else {
    Write-Error "❌ Tauri build failed!"
    exit 1
}
