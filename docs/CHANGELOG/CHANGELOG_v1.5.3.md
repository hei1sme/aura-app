# Changelog v1.5.3

## [1.5.3] - 2026-01-22

### 🚑 Hotfixes

- **Break Notification Loop**: Fixed a critical issue where the "Start Break" screen would reappear immediately after starting a break, causing a loop.
- **Duplicate Sounds**: Resolved an issue where the break completion sound would play twice due to overlapping timer intervals ("zombie intervals").

### 🔧 Technical Details

- **Overlay State Machine**: Implemented a robust state check in `BreakOverlay` to ignore redundant `show-break` events if a break is already in progress (`state !== "nudge"`).
- **Interval Management**: Added explicit `clearInterval` calls before starting any new countdown to prevent multiple intervals running in parallel.
- **Event Deduplication**: Introduced `currentBreakId` tracking to ensure state resets only happen for disjoint break events.

### 📁 Files Changed

- `src-ui/routes/overlay/+page.svelte` - Critical fixes for state management and timer logic.
- `package.json`, `src-tauri/tauri.conf.json`, `src-tauri/Cargo.toml`, `src-python/main.py` - Bumped version to 1.5.3.

---
See the repository for more details on all changes.
