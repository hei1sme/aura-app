# Changelog v1.5.5

## [1.5.5] - 2026-01-23

### ✨ New Features

#### Enhanced "What's New" Experience

- **Rich Markdown Support**: The update dialog now renders the "What's New" content in beautiful, formatted Markdown (headings, lists, bold text, code blocks) instead of plain text.
- **Smart Changelog Fetching**: The app now dynamically fetches the detailed changelog directly from GitHub for the specific version being updated to.

### 🔧 Improvements

- **Update Dialog UI**:
  - Increased scrollable area for longer release notes.
  - Improved scrollbar styling for better visibility.
  - Added robust fallback to default messages if changelog fetching fails.

### 📁 Files Changed

- `src-ui/routes/+layout.svelte` - Added changelog fetching logic.
- `src-ui/lib/components/UpdateModal.svelte` - Added Markdown parsing (using `marked`) and styling.
- `package.json` - Added `marked` dependency.
- Configuration files bumped to v1.5.5.

---

**Full Changelog**: [v1.5.4...v1.5.5](https://github.com/hei1sme/aura-app/compare/v1.5.4...v1.5.5)
