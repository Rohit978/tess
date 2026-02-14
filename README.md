# 🧠 TESS Terminal Pro (v5.0)
> **The AI System Administrator that lives in your terminal.**

![Python](https://img.shields.io/badge/Python-3.10%2B-yellow?style=for-the-badge)
![License](https://img.shields.io/badge/License-MIT-blue?style=for-the-badge)
![Status](https://img.shields.io/badge/Status-Active-green?style=for-the-badge)

**TESS** (Terminal Embedded System Supervisor) is not just a chatbot. It is a **Hybrid AI Agent** capable of controlling your Operating System, managing files, automating workflows, and browsing the web—all from a simple command-line interface.

It combines **Local LLMs** (via Ollama) and **Cloud APIs** (Groq, OpenAI, Gemini) to deliver fast, secure, and intelligent automation.

---

## ✨ Features

### 🖥️ Native System Control
-   **SysAdmin Commands:** "Turn off WiFi", "Check battery health", "Get system specs".
-   **Process Management:** List, kill, or monitor running processes.
-   **Power Control:** Sleep, Shutdown, or Restart your PC with a voice command.

### 🌐 Advanced Web Automation
-   **Headless Browsing:** Search Google/DuckDuckGo without opening a window.
-   **Page Scraping:** extract text and data from any URL.
-   **Screenshots:** Capture full-page screenshots of websites.
-   **YouTube Player:** Play music/videos directly in the background (`play [song]`).

### 📂 Intelligent File Management
-   **Active Learning (Librarian):** TESS watches your project folders and learns from your code automatically.
-   **Smart Search (RAG):** "How does the `auth` module work?" (Answers based on your files).
-   **Organizer:** Automatically organize cluttered folders (Downloads, Desktop) into categories.

### 🤖 Multi-Modal Interfaces
-   **CLI Mode:** Professional terminal interface with autocomplete and rich text.
-   **Telegram Bot:** Control your PC remotely via Telegram.
-   **Voice Mode:** Speak to TESS using Whisper AI (STT) and receive audio responses.
-   **WhatsApp:** Send messages and monitor chats via web automation.

### 🛠️ Developer Tools
-   **The Architect:** Auto-fix coding errors by analyzing tracebacks.
-   **Code Generation:** Write and execute Python scripts on the fly.
-   **Task Scheduler:** "Remind me to push code at 5 PM".

---

## 📦 Installation

### Option 1: Install via Pip (Recommended)
You can install the latest version directly from GitHub:

```bash
pip install git+https://github.com/Rohit978/tess.git
```

### Option 2: Clone for Development
If you want to modify the source code:

```bash
git clone https://github.com/Rohit978/tess.git
cd tess
pip install -e .
```

---

## ⚡ Quick Start

### 1. Initialize
Run the interactive setup wizard to configure your API keys:

```bash
tess init
```
*This will create `~/.tess/config.env` and guide you through adding Groq/OpenAI keys.*

### 2. Launch
Start the agent from any terminal:

```bash
tess
```

### 3. Basic Commands
| Command | Description |
| :--- | :--- |
| `help` | Show available commands |
| `learn basedir` | Index the current folder for RAG memory |
| `watch [path]` | Auto-learn changes in a specific folder |
| `voice` | Switch to Voice Input mode |
| `exit` | Quit the application |

---

## 🎮 Usage Examples

**System Control:**
> "Lock my PC."
> "Turn off Bluetooth."
> "What is my IP address?"

**Web & Research:**
> "Research the history of Quantum Computing (Depth: 2)."
> "Who is the CEO of NVIDIA?"
> "Play 'Lo-Fi Hip Hop' on YouTube."

**Coding & Files:**
> "Create a Python script to calculate Fibonacci numbers."
> "Organize my Downloads folder."
> "Explain the `main.py` file in this directory."

**Communication:**
> "Send a WhatsApp message to Dad: 'I will be late'."
> "Check my unread emails (Gmail)."

---

## 🧩 Architecture

TESS is built on a modular "Brain-Component" architecture:

-   **The Brain:** Central LLM processor (Groq/Llama-3). Handles intent classification and planning.
-   **Orchestrator:** Routes actions to the correct component (System, Web, File, etc.).
-   **Librarian:** Background service that watches filesystem changes and updates the Vector DB (ChromaDB).
-   **Executor:** Sandboxed environment for running system commands and generated code.

---

## 🛠️ Troubleshooting

**"PlaywrightBrowser object has no attribute..."**
-   Update TESS: `pip install . --upgrade`
-   Ensure you ran `tess init` to set up paths.

**"Google Generative AI Warnings"**
-   These are suppressed in the latest CLI version. Run via `python -m tess_cli` if issues persist.

**"File Locked / Permission Denied"**
-   Close any other terminal windows using TESS.
-   Run `taskkill /F /IM python.exe` in PowerShell.

---

## � License
MIT License.
Copyright (c) 2024 **Rohit Kumar**.
