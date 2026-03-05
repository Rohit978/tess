# 🧠 TESS Terminal Pro (v2.0)
> **The AI Operating System that lives in your terminal.**

![Python](https://img.shields.io/badge/Python-3.10%2B-yellow?style=for-the-badge)
![License](https://img.shields.io/badge/License-MIT-blue?style=for-the-badge)
![Status](https://img.shields.io/badge/Status-Active-green?style=for-the-badge)
![AI](https://img.shields.io/badge/AI-Multi%20Model-purple?style=for-the-badge)

**TESS** (Terminal Embedded System Supervisor) is a **Hybrid AI Agent** capable of controlling your OS, managing files, automating workflows, and browsing the web—all from a simple command-line interface.

It combines **Local Execution** (PowerShell, Python) with **Cloud Intelligence** (Gemini, OpenAI, Groq, or Local LLMs) to deliver fast, secure, and intelligent automation.

---

## ✨ What's New in v5.0?

### 🎵 Intelligent Media Control
- **YouTube:** Just type `play him and i` to launch a visible Chrome window and start playing music. TESS handles ads and playback control.
- **Strict Mode:** No more accidental web searches when you ask for music.

### 💬 WhatsApp Automation with Personas
- **"Chat with Ashi":** Launches a dedicated WhatsApp monitor.
- **Persona Swapping:**
    - **"TESS Mode":** Acts as an AI assistant (default).
    - **"Rohit Mode":** Impersonates YOU (the user) for natural replies.
- **Auto-Reply:** Reads incoming messages and replies in your style.

### 📄 Advanced PDF Engineering
- **Create:** `create a pdf about Narendra Modi` -> Generates a full biography PDF.
- **Read:** Can read and summarize local PDFs (`read report.pdf`).
- **Manipulate:** Merge (`merge a.pdf, b.pdf`), Split (`split pages 1-3`), and Extract Text.

### 🧠 Enhanced Brain & Memory (v5.1)
- **Deep Memory Engine:** Memories now persist safely in a centralized database rather than volatile working directories.
- **Advanced Context:** Upgraded support for **High-Reasoning Models** (e.g., Gemini 1.5/2.0 Pro, GPT-4o) with strict safety rail control for default modes. Context window expanded to 100 turns.
- **True Key Rotation:** Built-in sequential API key rotation on rate limits guarantees continuous service.

### 🛡️ Core Stability & Security (v2.0)
- **Hardened Execution:** Command execution now features strict 60-second timeouts.
- **Workspace Sandboxing:** The AI coding agent is strictly bounded to the active workspace.
- **Autonomous Mode:** ⚡ TESS now operates with full autonomy in coding mode. No more "Allow? (Y/n)" prompts for every file edit or command execution.
- **Robust Configuration:** Deep-merged JSON configuration cleanly preserves user choices across upgrades.

---

## 🔄 Updating from v1.x / v5.x

If you are already using TESS, follow these steps to upgrade to **v2.0**:

1. **Pull the latest changes:**
   ```bash
   git pull origin main
   ```
2. **Update dependencies:**
   ```bash
   pip install -r requirements.txt
   playwright install
   ```
3. **Reset or Migrate Config:**
   TESS v2.0 will automatically attempt to migrate your `~/.tess/config.json`. If you face issues, you can reset it by deleting the file:
   ```powershell
   Remove-Item ~\.tess\config.json
   tess init
   ```

---

## 🚀 Features at a Glance

### 🖥️ Native System Control
- **SysAdmin:** "Turn off WiFi", "Check battery health", "Get system specs".
- **Process Management:** List, kill, or monitor running processes.
- **Power:** Sleep, Shutdown, or Restart with voice commands.

### 🌐 Web & Research
- **Deep Research:** "Research the history of Quantum Computing (Depth: 2)."
- **Headless Browsing:** Scrape data without opening windows.
- **Screenshots:** Capture full-page snaps of any website.

### 📂 File & Coding
- **Active Learning (Librarian):** Watches your project folders and learns code structure.
- **Organizer:** "Organize my Downloads folder" sorts files into categories.
- **The Architect:** Auto-fixes Python errors by reading tracebacks.

### 🧪 Digital Twin (Sandbox)
- **Safe Execution:** Ask "What if I run `rm -rf /`?" to see a simulation without damage.
- **Docker Integration:** Execute risky code in isolated containers.

---

## 📦 Installation

### Prerequisites
- Python 3.10+
- Chrome/Chromium (for Playwright)

### Option 1: Quick Install (pip)
```bash
pip install git+https://github.com/Rohit978/tess.git
playwright install
tess init
```

### Option 2: Development Install (Clone)
```bash
git clone https://github.com/Rohit978/tess.git
cd tess
pip install -r requirements.txt
playwright install
```

### 2. Initialize
Run the setup wizard to configure your **API Keys** (Gemini, OpenAI, Groq, etc.):
```bash
tess init
```
*This creates `~/.tess/config.env`.*

### 3. Launch
```bash
tess
```

---

## 🎮 Usage Guide

| Goal | Command Example |
| :--- | :--- |
| **Play Music** | `play starboy` |
| **Chat on WhatsApp** | `chat with mom` |
| **Research Topic** | `research quantum physics` |
| **Create PDF** | `create a pdf summary of this project` |
| **Organize Files** | `organize downloads` |
| **System Info** | `what is my ip` |
| **Code Help** | `write a python script to ping google` |
| **Switch Persona** | `persona cute` / `persona professional` |

---

## ⚙️ Configuration

TESS uses a dual-config system:
1.  **Code Defaults:** `tess_cli/core/config.py`
2.  **User Overrides:** `~/.tess/config.json`

**To reset configuration:**
Delete `~/.tess/config.json` and restart TESS.

---

## 🛠️ Troubleshooting

**"win11toast not installed"**
- Run `pip install win11toast`. (Now fails silently if missing).

**"YouTube opens search instead of playing"**
- TESS v5.0 strictly separates `youtube_op` (Play) from `web_search_op` (Research). Ensure you say "play [song]".

**"Rate Limit Exceeded"**
- We've added a smart backoff (10s wait). Just wait a moment, it will retry automatically.

---


---

## 🔌 Plugin System (New!)

Version 5.1 introduces a **Dynamic Plugin Architecture**. You can now extend TESS's capabilities without modifying the core code.

### How to Add Custom Skills
1. Go to your home directory: `C:\Users\YourName\.tess\plugins`
2. Create a Python file (e.g., `spotify_skill.py`).
3. Inherit from `BaseSkill` and define your intent.

**Example `spotify_skill.py`:**
```python
from tess_cli.skills.base_skill import BaseSkill

class SpotifySkill(BaseSkill):
    name = "Spotify"
    description = "Controls Spotify Desktop App"
    intents = ["spotify_op"] # TESS will route 'spotify_op' actions here

    def execute(self, action_data, context):
        sub = action_data.get("sub_action")
        if sub == "play":
            return "Playing Spotify..." # Your logic here
        return f"Unknown action: {sub}"
```
4. **Restart TESS.** It will automatically discover and load your plugin!

---

## 👨‍💻 Author
**Rohit Kumar**

![Python](https://img.shields.io/badge/Made%20with-Love-red?style=for-the-badge)
