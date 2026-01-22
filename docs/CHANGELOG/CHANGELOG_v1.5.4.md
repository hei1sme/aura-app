# Changelog v1.5.4

## [1.5.4] - 2026-01-23

### ✨ New Features

#### Smart App Categorization

- Replaced hardcoded app mapping with **intelligent keyword-based detection**
- Now supports 100+ apps across 6 categories:
  - **Code**: IDEs, editors, terminals, dev tools (VS Code, PyCharm, Terminal, Docker, etc.)
  - **Web**: All major browsers (Chrome, Firefox, Edge, Arc, Brave, etc.)
  - **Communication**: Chat, video calls, email (Discord, Slack, Zoom, Teams, etc.)
  - **Productivity**: Office, notes, design tools (Notion, Obsidian, Figma, Word, etc.)
  - **Video**: Players, streaming, editing (VLC, OBS, Premiere, DaVinci, etc.)
  - **Game**: Launchers and popular games (Steam, Valorant, League, Minecraft, etc.)

#### Interactive Dashboard Tooltips

- **Focus Distribution**: Hover over donut chart segments to see category name, percentage, and sample count
- **Break Compliance**: Hover over bar chart columns to see completed/snoozed/skipped breakdown per day
- **Hydration Trends**: Hover over data points to see daily intake and percentage of goal

### 🔧 Improvements

- **Activity Intensity**: Now benefits from periodic sampling (every 5 minutes) for more accurate heatmap data
- **Focus Distribution**: Also benefits from periodic sampling for better app usage tracking
- Enhanced accessibility with ARIA labels on interactive chart elements

### 📁 Files Changed

- `src-python/aura_engine/ml/collector.py` - Smart keyword-based app categorization
- `src-ui/lib/components/FocusDistributionCard.svelte` - Hover tooltips
- `src-ui/lib/components/BreakComplianceCard.svelte` - Hover tooltips
- `src-ui/lib/components/HydrationTrendsCard.svelte` - Hover tooltips
- `package.json`, `src-tauri/tauri.conf.json`, `src-tauri/Cargo.toml`, `src-python/main.py` - Version bump

---

**Full Changelog**: [v1.5.3...v1.5.4](https://github.com/hei1sme/aura-app/compare/v1.5.3...v1.5.4)
