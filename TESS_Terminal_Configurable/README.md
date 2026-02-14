# 🤖 TESS Terminal - Configurable Edition

A **standalone, user-configurable** terminal AI agent that puts you in control. No hardcoded secrets, no complex setup—just a clean, interactive configuration experience.

[![Python](https://img.shields.io/badge/python-3.8+-blue.svg)](https://python.org)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![PyPI](https://img.shields.io/badge/install-pip-blue.svg)](#installation)

---

## ✨ Features

- **🔧 Interactive Setup Wizard** - Configure everything through a beautiful TUI
- **🔑 Secure API Key Management** - Local storage with proper permissions
- **🔄 Multi-Provider Support** - Groq, OpenAI, DeepSeek, Gemini with automatic failover
- **🛡️ Configurable Security** - Choose your security level (LOW/MEDIUM/HIGH)
- **📊 Settings Menu** - Change configuration anytime without editing files
- **💬 Natural Language** - Control your computer with plain English
- **⚡ Extensible** - Easy to add new capabilities

---

## 🚀 Installation

### Option 1: Install from GitHub (Recommended)

```bash
pip install git+https://github.com/Rohit978/tess-terminal.git
```

### Option 2: Clone and Install

```bash
git clone https://github.com/Rohit978/tess-terminal.git
cd tess-terminal
pip install -e .
```

### Option 3: Download ZIP

1. Download and extract this repository
2. `cd tess-terminal`
3. `pip install -e .`

---

## 🎯 Quick Start

### 1. Configure

```bash
tess --setup
```

This interactive wizard will:
- Help you get a free API key
- Set your security preferences
- Configure optional features

### 2. Run

```bash
# Interactive mode
tess

# Or execute a single command
tess "open chrome"
tess "list files in downloads"
```

---

## 📖 Usage

### Interactive Mode

```
$ tess

┌─────────────────────────────────┐
│     TESS Terminal               │
│     Configurable Edition        │
├─────────────────────────────────┤
│  Provider: GROQ                 │
│  Model: llama-3.3-70b-versatile │
│  Security: MEDIUM               │
└─────────────────────────────────┘

Type 'help' for commands, 'exit' to quit

You: open notepad
[TESS] Launched notepad

You: take a screenshot
[TESS] Screenshot saved to Desktop

You: search for python tutorials
[TESS] Searching: python tutorials
```

### Special Commands

| Command | Description |
|---------|-------------|
| `help` | Show help message |
| `config` | Open settings menu |
| `history` | Show conversation history |
| `status` | Show system status |
| `clear` | Clear screen |
| `!command` | Execute shell command directly |
| `exit` / `quit` | Exit TESS |

### CLI Options

```bash
tess --setup             # Run main configuration wizard
tess --settings          # Open settings menu
tess --google-setup      # Setup Gmail and Calendar
tess --notion-setup      # Setup Notion integration
tess --telegram-setup    # Setup Telegram bot
tess --reset             # Reset to defaults
tess --version           # Show version
tess "your command"      # Execute single command
```

---

## 🔑 Getting API Keys (FREE)

TESS works with multiple LLM providers. **Groq is recommended** (free & fast):

| Provider | Get Key | Free Tier |
|----------|---------|-----------|
| **Groq** ⭐ | [console.groq.com/keys](https://console.groq.com/keys) | ✅ $200/month |
| **Gemini** | [aistudio.google.com](https://aistudio.google.com/app/apikey) | ✅ Generous |
| **DeepSeek** | [platform.deepseek.com](https://platform.deepseek.com/api_keys) | ✅ Available |
| **OpenAI** | [platform.openai.com](https://platform.openai.com/api-keys) | ❌ Paid |

> 💡 **Tip**: Add multiple keys for automatic failover!

---

## 🔌 Integrations

TESS supports integrations with popular services. Each has an interactive setup wizard:

### 📧 Gmail & Calendar

```bash
tess --google-setup
```

This wizard will guide you through:
1. Creating a Google Cloud project
2. Enabling Gmail and Calendar APIs
3. Creating OAuth credentials
4. Authenticating with your Google account

### 📝 Notion

```bash
tess --notion-setup
```

Steps:
1. Create a Notion integration at notion.so/my-integrations
2. Copy the Internal Integration Token
3. Share your databases/pages with the integration
4. Configure default parent page (optional)

### 💬 Telegram Bot

```bash
tess --telegram-setup
```

Steps:
1. Message @BotFather on Telegram
2. Create a new bot with `/newbot`
3. Copy the API token
4. Get your User ID from @userinfobot
5. TESS saves the configuration

Once set up, you can control TESS remotely via Telegram!

---

## ⚙️ Configuration

Settings are stored in:
- **Windows**: `%USERPROFILE%\.tess\config.json`
- **macOS/Linux**: `~/.tess/config.json`

Change anytime with:
```bash
tess --settings
```

Or in-app:
```
You: config
[Settings Menu opens...]
```

---

## 🏗️ Architecture

```
tess_configurable/
├── config_manager.py         # Settings persistence
├── setup_wizard.py           # First-time setup TUI
├── settings_menu.py          # Configuration menu
├── google_setup_wizard.py    # Google OAuth setup
├── telegram_setup_wizard.py  # Telegram bot setup
├── main.py                   # Entry point & CLI
└── core/
    ├── brain.py              # Multi-provider LLM
    ├── orchestrator.py       # Action routing
    ├── schemas.py            # Data validation
    ├── document_ai.py        # PDF/OCR processing
    ├── workflow_engine.py    # Automation
    ├── preference_memory.py  # User learning
    ├── notion_client.py      # Notion API
    ├── google_client.py      # Gmail/Calendar
    ├── whatsapp_client.py    # WhatsApp Web
    └── ...
└── skills/
    ├── research.py           # Deep research
    ├── trip_planner.py       # Travel planning
    └── converter.py          # File conversion
```

---

## 🧠 Smart Features

### Document AI
Extract and analyze documents:
```bash
tess "extract text from report.pdf"
tess "summarize document.pdf"
tess "read text from image.png"
```

### Workflow Automation
Create automated routines:
```bash
tess "create morning routine"
tess "run focus mode"
tess "list my workflows"
```

### Preference Memory
TESS learns your preferences:
```bash
You: I prefer Chrome over Firefox
You: My name is John
You: I work 9 to 5
```

---

## 🛡️ Security Features

- 🔐 API keys stored locally with 0600 permissions
- 🚫 No hardcoded credentials
- ✅ Command validation before execution
- ⚠️ Configurable confirmation prompts
- 🛡️ Blocked dangerous commands: `rm -rf`, `format`, `shutdown`

---

## 🐛 Troubleshooting

### "No API keys configured"
```bash
tess --setup
```

### Import errors
```bash
pip install --upgrade -r requirements.txt
```

### Playwright not found
```bash
pip install playwright
playwright install chromium
```

### WhatsApp/Chrome crashes
TESS now uses **Playwright** (modern browser automation) by default instead of Selenium.
```bash
# Install Playwright browsers
playwright install chromium
```

### Reset everything
```bash
tess --reset
# Or manually delete ~/.tess/
```

---

## 🤝 Contributing

Contributions welcome! Areas to help:
- 🐛 Bug fixes
- ✨ New actions/skills
- 🌍 Cross-platform improvements
- 📚 Documentation

---

## 📄 License

MIT License - See [LICENSE](LICENSE) file.

---

## 🙏 Credits

Inspired by the original TESS Terminal Pro. This configurable edition focuses on user control, easy setup, and clean architecture.

---

## ⭐ Star History

If you find TESS useful, please consider starring the repo!

[![Star History Chart](https://api.star-history.com/svg?repos=Rohit978/tess-terminal&type=Date)](https://star-history.com/Rohit978/tess-terminal&Date)

