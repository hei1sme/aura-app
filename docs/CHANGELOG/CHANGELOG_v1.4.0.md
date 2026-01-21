# Aura v1.4.0 Release Notes

**Release Date**: January 21, 2026  
**Previous Version**: 1.3.0

---

## 🎯 What's New

### Analytics Dashboard Redesign

Complete overhaul of the main dashboard with enterprise-level analytics focus:

- **Break Compliance Analytics**
  - Visual breakdown of completed, skipped, and snoozed breaks
  - 7-day compliance trends with interactive charts
  - Daily break history with timestamps and outcomes

- **Hydration Tracking**
  - Daily intake progress with visual indicators
  - 7-day hydration trends
  - Goal achievement tracking

- **Activity Patterns**
  - Real-time keyboard activity (keys/min)
  - Mouse velocity tracking
  - Activity heatmap showing work patterns by hour

- **Quick Actions**
  - One-click pause/resume toggle
  - Streamlined interface for session control
  - Removed development test buttons for cleaner UX

### Enhanced Settings UI

- Improved visual hierarchy for schedule management
- Better organization of break interval settings
- Refined immersive mode tracking options

### Visual Improvements

- **Break Overlay Enhancement**
  - Fixed visible outline artifact around notification card
  - Enhanced glassmorphism effect with stronger backdrop blur (24px)
  - Multi-layer shadows for better depth perception
  - Improved border definition and corner radius
  - Added rendering optimizations for smoother animations

---

## 🐛 Bug Fixes

- Removed unwanted white outline around break overlay card
- Fixed rendering artifacts with explicit border/outline/shadow removal
- Enhanced anti-aliasing for crisper text and UI elements
- Improved GPU acceleration for better performance

---

## 🔧 Technical Improvements

- Verified work schedule control logic (pause/resume/reset/start/end)
- Confirmed thread-safe state management
- Validated session state persistence across restarts
- Ensured proper timer behavior for all state transitions

---

## 📦 Files Changed

- `package.json` - Updated to 1.4.0
- `Cargo.toml` - Updated to 1.4.0
- `tauri.conf.json` - Updated to 1.4.0
- `src-python/main.py` - Updated VERSION to 1.4.0

---

## 🚀 Upgrade Instructions

1. **Download** the latest installer: `Aura_1.4.0_x64-setup.exe`
2. **Run** the installer (will upgrade existing installation)
3. **Restart** Aura to see the new analytics dashboard

---

## 📝 Notes

- All existing settings and data are preserved during upgrade
- Work schedule rules remain intact
- No breaking changes from v1.3.0

---

## 🙏 Credits

This release includes contributions focused on:

- Enhanced user experience with comprehensive analytics
- Visual polish and bug fixes
- System stability verification

---

## 🔗 Resources

- [GitHub Repository](https://github.com/your-repo/aura)
- [Documentation](https://github.com/your-repo/aura#readme)
- [Report Issues](https://github.com/your-repo/aura/issues)
