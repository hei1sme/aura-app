
<div align="center">
  <img src="https://github.com/tauri-apps/tauri/raw/dev/.github/splash.png" width="200" alt="Aura Logo" />
  <h1>✨ Aura</h1>
  <p><strong>Your Intelligent Wellness Companion</strong></p>
  
  [![Tauri](https://img.shields.io/badge/Tauri-2.0-orange?style=flat&logo=tauri)](https://tauri.app)
  [![SvelteKit](https://img.shields.io/badge/SvelteKit-Latest-ff3e00?style=flat&logo=svelte)](https://kit.svelte.dev)
  [![Python](https://img.shields.io/badge/Python-3.11-blue?style=flat&logo=python)](https://www.python.org)
  [![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
</div>

<br />

**Aura** is a premium, AI-powered desktop application designed to help you maintain focus and wellness while you work. Built with the performance of **Rust (Tauri)**, the elegance of **SvelteKit**, and the intelligence of **Python**.

---

## 🌟 Features

*   **⚡ Premium Session Hub**: A beautiful, glowing circular timer that tracks your focus sessions with style.
*   **🧠 Intelligent Breaks**: Dynamic break suggestions (Micro vs. Macro) based on your work patterns.
*   **🎨 Adaptive UI**: A compact, unobtrusive interface that respects your screen space.
*   **🔌 Python Power**: A dedicated Python sidecar engine for advanced logic and data processing.
*   **🔔 Smart Notifications**: Gentle reminders to take a breath or stretch.

## 🛠️ Tech Stack

*   **Frontend**: SvelteKit, TypeScript, Tailwind CSS
*   **Backend**: Rust (Tauri Core) + Python (Data Engine)
*   **Build System**: Vite + PyInstaller

## 🚀 Getting Started

### Prerequisites

*   [Node.js](https://nodejs.org/) (v16+)
*   [Rust](https://www.rust-lang.org/) (for Tauri)
*   [Python 3.11](https://www.python.org/) (for the Sidecar)

### Installation

1.  **Clone the repository**:
    ```bash
    git clone https://github.com/yourusername/aura.git
    cd aura/aura-app
    ```

2.  **Install dependencies**:
    ```bash
    npm install
    # Install Python dependencies (suggested in a venv)
    cd src-python
    pip install -r requirements.txt
    cd ..
    ```

3.  **Run Development Mode**:
    ```bash
    npm run tauri dev
    ```

## 📦 Building for Production

We have streamlined the build process to automatically compile the Python engine and the Tauri frontend.

**For Windows (Git Bash / MinGW):**
```bash
./build_release.sh
```

**For Windows (PowerShell):**
```powershell
.\build_release.ps1
```

The installer will be generated in `src-tauri/target/release/bundle/nsis/`.

## 🤝 Contributing

Contributions are always welcome! Please create a PR or open an issue if you have ideas for improving Aura.

---

<div align="center">
  <i>Every pixel designed for peace.</i> 🌿
</div>
