# Changelog v1.5.2

## [1.5.2] - 2026-01-22

### 🐛 Bug Fixes

- **Session Hub Version Store**: Fixed missing `sidecarVersion` import in Session Hub page. Previously, navigating from Session Hub → Settings → About would show incorrect version due to the store not being set.
- **Version Display**: App version now correctly displays across all entry points (Dashboard, Session Hub).

### 🔧 Technical Improvements

- Unified version store initialization across all page entry points
- Added proper store subscription for dynamic version updates

### 📁 Files Changed

- `src-ui/routes/session/+page.svelte` - Added missing `sidecarVersion` import from stores

---
See the repository for more details on all changes.
