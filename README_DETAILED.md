# 🧠 TESS Terminal Pro (v5.0)

> **An AI-Powered System Administrator for Your Terminal**

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-green.svg?style=flat-square)](LICENSE)
[![Version](https://img.shields.io/badge/Version-5.0.0-blue.svg?style=flat-square)](https://github.com/Rohit978/tess/releases)
[![Status](https://img.shields.io/badge/Status-Production%20Ready-brightgreen.svg?style=flat-square)]()

**TESS** (Terminal Embedded System Supervisor) is a production-grade, hybrid AI agent that transforms your terminal into an intelligent system administrator. Built with a modular architecture, TESS combines local LLMs and cloud APIs to deliver secure, fast, and intelligent automation.

---

## 🎯 Project Overview

| Attribute | Details |
|-----------|---------|
| **Language** | Python 3.10+ |
| **Architecture** | Modular Component-Based |
| **Total Modules** | 50+ Core Components |
| **Lines of Code** | 15,000+ |
| **Test Coverage** | Unit + Integration Tests |
| **Distribution** | pip installable |

---

## ✨ Core Features

### 🤖 AI & Language Models
- **Multi-Provider Support**: Groq, OpenAI, DeepSeek, Gemini
- **Intelligent Fallbacks**: Auto-switching between providers
- **Context Memory**: Persistent conversation history
- **RAG Integration**: Retrieval-Augmented Generation with ChromaDB

### 🖥️ System Administration
- **Process Management**: List, monitor, kill processes
- **Power Control**: Sleep, shutdown, restart remotely
- **Hardware Monitoring**: Battery, CPU, RAM, disk usage
- **Network Tools**: IP config, WiFi/Bluetooth toggle
- **App Launcher**: Start applications via natural language

### 🌐 Web Automation
- **Headless Browser**: Playwright-powered web scraping
- **Search Integration**: Google, DuckDuckGo
- **YouTube Control**: Background music playback
- **Screenshot Capture**: Full-page web captures
- **WhatsApp Automation**: Message sending via web

### 📚 Knowledge Management
- **Librarian System**: Auto-indexing project files
- **Vector Database**: ChromaDB for semantic search
- **Active Learning**: Watches file changes in real-time
- **Code Analysis**: Understands your codebase structure

### 🎙️ Multi-Modal Interfaces
- **CLI**: Rich terminal UI with autocomplete
- **Telegram Bot**: Remote PC control via messaging
- **Voice Mode**: Whisper STT + audio responses
- **API Server**: RESTful endpoints for integration

### 🛠️ Developer Tools
- **The Architect**: Auto-debugs Python errors
- **Code Generator**: Creates scripts on-the-fly
- **Task Scheduler**: Cron-like job management
- **File Organizer**: Auto-sorts cluttered folders

---

## 🏗️ Architecture

```
TESS Terminal Pro
├── 🧠 Brain (LLM Processor)
│   ├── Multi-provider routing
│   ├── Intent classification
│   └── Response generation
├── 🎛️ Orchestrator
│   ├── Action routing
│   └── Component coordination
├── 📦 Components
│   ├── System Controller
│   ├── Web Browser
│   ├── File Manager
│   ├── Knowledge Base
│   ├── Voice Client
│   └── Scheduler
├── 💾 Memory
│   ├── Conversation History
│   ├── Vector DB (ChromaDB)
│   └── User Profiles
└── 🔌 Interfaces
    ├── Terminal CLI
    ├── Telegram Bot
    └── REST API
```

---

## 📦 Installation

### Prerequisites
- Python 3.10+
- Windows 10/11 (primary support)
- API keys for Groq/OpenAI (optional)

### Quick Install
```bash
# Install from GitHub
pip install git+https://github.com/Rohit978/tess.git

# Or clone for development
git clone https://github.com/Rohit978/tess.git
cd tess
pip install -e .
```

### Initial Setup
```bash
# Run interactive setup wizard
tess init

# This creates:
# ~/.tess/config.env      # API keys
# ~/.tess/memory/         # User data
# ~/.tess/logs/           # Application logs
```

---

## 🚀 Usage

### Launch TESS
```bash
tess
```

### Basic Commands
| Command | Description |
|---------|-------------|
| `help` | Show available commands |
| `learn [path]` | Index folder for RAG |
| `watch [path]` | Monitor folder changes |
| `voice` | Switch to voice mode |
| `status` | Show system status |
| `exit` | Quit application |

### Natural Language Examples
```bash
# System Control
> "Lock my PC"
> "Turn off WiFi"
> "Show me my IP address"

# Web & Research  
> "Search for Python best practices"
> "Play lo-fi beats on YouTube"
> "Take a screenshot of google.com"

# File Management
> "Organize my Downloads folder"
> "Explain the main.py file"
> "Find all TODO comments in this project"

# Coding
> "Create a script to backup my Documents"
> "Fix the error in test.py"
> "Generate a requirements.txt"
```

---

## 🧪 Testing

```bash
# Run all tests
pytest tests/

# Run specific test
pytest tests/test_brain.py -v

# With coverage
pytest --cov=tess_cli tests/
```

---

## 📁 Project Structure

```
TESS_Terminal_Pro/
├── tess_cli/               # Main package
│   ├── core/              # Core components (50+ modules)
│   │   ├── brain.py       # LLM processor
│   │   ├── orchestrator.py # Action router
│   │   ├── system_controller.py
│   │   ├── web_browser.py
│   │   ├── file_manager.py
│   │   ├── knowledge_base.py
│   │   └── ...
│   ├── interfaces/        # User interfaces
│   │   ├── telegram_bot.py
│   │   └── api_server.py
│   ├── skills/            # Specialized skills
│   │   ├── sysadmin.py
│   │   ├── converter.py
│   │   └── trip_planner.py
│   ├── cli.py             # Entry point
│   └── __main__.py        # Module runner
├── tests/                 # Test suite
├── data/                  # Static data
├── requirements.txt       # Dependencies
├── setup.py              # Package config
└── README.md             # Documentation
```

---

## 🔧 Configuration

### Environment Variables (`~/.tess/config.env`)
```env
# LLM Providers (at least one required)
GROQ_API_KEY=your_key_here
OPENAI_API_KEY=your_key_here
GEMINI_API_KEY=your_key_here

# Optional: Telegram Bot
TELEGRAM_BOT_TOKEN=your_bot_token

# Optional: Custom Settings
TESS_PERSONALITY=professional
TESS_LOG_LEVEL=INFO
```

---

## 🛡️ Security Features

- **Sandboxed Execution**: Code runs in isolated environment
- **Permission Prompts**: Dangerous actions require confirmation
- **API Key Encryption**: Secure storage of credentials
- **Command Validation**: Prevents malicious system commands

---

## 🐛 Troubleshooting

### Common Issues

**"Module not found" errors**
```bash
pip install -r requirements.txt --upgrade
```

**"Playwright browser not found"**
```bash
playwright install chromium
```

**"Permission denied"**
- Run terminal as Administrator (Windows)
- Check file locks: `taskkill /F /IM python.exe`

---

## 🗺️ Roadmap

- [ ] macOS/Linux full support
- [ ] VS Code extension
- [ ] Docker containerization
- [ ] Plugin system for custom skills
- [ ] Multi-language support
- [ ] Cloud sync for settings

---

## 📄 License

MIT License - see [LICENSE](LICENSE) file

Copyright (c) 2024 Rohit Kumar

---

## 🙏 Acknowledgments

- [Groq](https://groq.com) for fast inference
- [ChromaDB](https://chromadb.com) for vector storage
- [Playwright](https://playwright.dev) for web automation
- [Rich](https://rich.readthedocs.io) for terminal UI

---

<p align="center">
  <strong>Built with 🧠 and ☕ by Rohit Kumar</strong><br>
  <em>Third Year Computer Science Student</em>
</p>
