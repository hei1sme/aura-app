# Aura v1.5.0 Release Notes

**Release Date**: January 22, 2026  
**Previous Version**: 1.4.0

---

## 🎯 What's New

### ⚡ Auto-Update System

Experience seamless updates with our new OTA (Over-The-Air) update engine:

- **Instant Checks**: One-click "Check for Updates" in the new About page.
- **Background Downloads**: Updates download silently while you work.
- **Secure Verification**: All updates are cryptographically signed with Ed25519 keys to ensure authenticity.
- **Smart Restart**: Installs updates and restarts the app automatically.

### ℹ️ New About Section

A dedicated space for application information:

- Accessed via the new Info icon (ℹ️) in the header.
- Displays current version synced with the Python engine.
- Direct links to GitHub and Website.
- Integrated update management interface.

### 🔧 GitHub Actions Integration

Automated release pipeline for faster delivery:

- **CI/CD**: Every tagged release triggers an automatic build/sign/publish workflow.
- **Reliability**: Eliminates manual build errors and inconsistent environments.

---

## 🐛 Bug Fixes

- Fixed minor syntax errors in settings navigation.
- Resolved potential "overwrite" issues during key generation.
- Improved error handling for missing update manifests.

---

## 📦 Files Changed

- `package.json` - Updated to 1.5.0
- `Cargo.toml` - Updated to 1.5.0
- `tauri.conf.json` - Updated to 1.5.0, configured updater plugin
- `src-python/main.py` - Updated VERSION to 1.5.0
- `src-ui/lib/components/settings/SettingsAbout.svelte` - [NEW] update interface
- `.github/workflows/release.yml` - [NEW] automated build pipeline

---

## 🚀 Upgrade Instructions

1. **Download** the latest installer (this will be the last manual download!).
2. **Install** v1.5.0 over your existing version.
3. **Enjoy** automatic updates for all future versions!

---
