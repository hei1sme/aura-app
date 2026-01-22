# Changelog v1.5.1

## [1.5.1] - 2026-01-22

### ✨ New Features

- **Auto-Update on Startup**: App tự động kiểm tra phiên bản mới khi khởi động (delay 5 giây)
- **Update Modal**: Hiển thị modal đẹp mắt với thông tin version mới và release notes
- **Skip Version**: Cho phép người dùng bỏ qua phiên bản cụ thể (giống VS Code, Chrome)
- **Update Preferences**: Toggle bật/tắt auto-check trong Settings > About

### 🔧 Fixed

- Bổ sung `createUpdaterArtifacts` vào cấu hình Tauri để luôn sinh file chữ ký (signature)
- Sửa workflow CI/CD: tự động tạo `latest.json`, upload đầy đủ file `.sig`
- Sửa lỗi hardcode version ở dashboard, chuyển sang lấy version động từ sidecar

### 📁 Files Changed

- `src-ui/lib/components/UpdateModal.svelte` - [NEW] Modal component
- `src-ui/routes/+layout.svelte` - Auto-check logic integration
- `src-ui/lib/components/settings/SettingsAbout.svelte` - Update preferences UI

---
Xem thêm chi tiết các thay đổi tại repository.
