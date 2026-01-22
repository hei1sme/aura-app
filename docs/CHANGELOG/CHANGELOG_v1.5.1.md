# Changelog v1.5.1

## [1.5.1] - 2026-01-22

### ✨ New Features

- **Auto-Update on Startup**: App automatically checks for new versions on startup (5-second delay)
- **Update Modal**: Beautiful modal displaying new version info and release notes
- **Skip Version**: Allow users to skip specific versions (similar to VS Code, Chrome)
- **Update Preferences**: Toggle auto-check on/off in Settings > About

### � Bug Fixes

- Added `createUpdaterArtifacts` to Tauri config to always generate signature files
- Fixed CI/CD workflow: auto-generate `latest.json`, upload all `.sig` files
- Fixed hardcoded version in dashboard, now fetches version dynamically from sidecar

### 📁 Files Changed

- `src-ui/lib/components/UpdateModal.svelte` - [NEW] Modal component
- `src-ui/routes/+layout.svelte` - Auto-check logic integration
- `src-ui/lib/components/settings/SettingsAbout.svelte` - Update preferences UI

---
See the repository for more details on all changes.
