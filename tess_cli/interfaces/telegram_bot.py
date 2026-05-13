import asyncio
import logging
import os
import tempfile

from telegram import (
    Update,
    BotCommand,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.constants import ChatAction
from telegram.ext import (
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from ..core.config import Config
from ..core.logger import setup_logger
from ..core.orchestrator import process_action

logger = setup_logger("TelegramBot")

# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────

def _truncate(text: str, limit: int = 4000) -> str:
    """Telegram messages cap at 4096 chars."""
    if len(text) <= limit:
        return text
    return text[: limit - 20] + "\n…[truncated]"


class TessBot:
    """
    Full-featured Telegram interface for TESS.

    Commands
    ────────
    /start          — greeting + quick-action keyboard
    /help           — capability list
    /status         — system status (screencast URL, running services)
    /screenshot     — capture & send screen
    /screencast     — start/stop/link the screencast
    /run <cmd>      — execute a shell command and return output
    /recall <query> — query TESS memory
    /clear          — wipe conversation context for this user
    """

    def __init__(
        self,
        profile_manager,
        launcher,
        sys_ctrl,
        file_mgr,
        knowledge_db,
        planner,
        web_browser,
        task_registry,
        whatsapp,
        youtube_client,
        executor,
        screencast=None,
    ):
        self.token = Config.TELEGRAM_BOT_TOKEN
        if not self.token:
            raise ValueError("TELEGRAM_BOT_TOKEN not set in config.")

        self.profile_manager = profile_manager
        self.components = {
            "launcher":       launcher,
            "sys_ctrl":       sys_ctrl,
            "file_mgr":       file_mgr,
            "knowledge_db":   knowledge_db,
            "planner":        planner,
            "web_browser":    web_browser,
            "task_registry":  task_registry,
            "whatsapp":       whatsapp,
            "youtube_client": youtube_client,
            "executor":       executor,
            "screencast":     screencast,
        }
        self.screencast = screencast

    # ──────────────────────────────────────────
    # Internal helpers
    # ──────────────────────────────────────────

    def _brain(self, user_id: str):
        return self.profile_manager.get_brain(str(user_id))

    async def _typing(self, update: Update):
        await update.effective_chat.send_action(ChatAction.TYPING)

    async def _reply(self, update: Update, text: str, **kwargs):
        await update.effective_message.reply_text(
            _truncate(text), parse_mode="Markdown", **kwargs
        )

    async def _run_in_executor(self, loop, fn, *args):
        return await loop.run_in_executor(None, fn, *args)

    def _make_callback(self, update: Update, loop: asyncio.AbstractEventLoop):
        """Returns a sync callback that safely sends a Telegram message."""
        chat_id = update.effective_chat.id

        def tele_out(text):
            asyncio.run_coroutine_threadsafe(
                update.effective_chat.send_message(
                    _truncate(str(text)), parse_mode="Markdown"
                ),
                loop,
            )

        return tele_out

    # ──────────────────────────────────────────
    # Command: /start
    # ──────────────────────────────────────────

    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        keyboard = [
            [
                InlineKeyboardButton("📸 Screenshot", callback_data="screenshot"),
                InlineKeyboardButton("📡 Screencast", callback_data="screencast_status"),
            ],
            [
                InlineKeyboardButton("💻 System Status", callback_data="sys_status"),
                InlineKeyboardButton("❓ Help", callback_data="help"),
            ],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.effective_message.reply_text(
            "🤖 *TESS Terminal Pro* is Online.\n\n"
            "Talk to me naturally, or use the quick actions below.\n"
            "Type /help to see all commands.",
            parse_mode="Markdown",
            reply_markup=reply_markup,
        )

    # ──────────────────────────────────────────
    # Command: /help
    # ──────────────────────────────────────────

    async def cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = (
            "*TESS Command Center*\n\n"
            "*Slash Commands*\n"
            "`/screenshot` — Capture & send your screen\n"
            "`/screencast` — Start/stop internet screen share\n"
            "`/run <cmd>` — Execute a shell command\n"
            "`/recall <query>` — Search TESS memory\n"
            "`/status` — Show running services\n"
            "`/clear` — Reset your conversation context\n\n"
            "*Natural Language*\n"
            "Just type anything — launch apps, control system, browse web, "
            "manage files, send WhatsApp, play YouTube, code, plan, and more.\n\n"
            "*Voice Messages*\n"
            "Send a voice note and TESS will transcribe + execute it."
        )
        await self._reply(update, text)

    # ──────────────────────────────────────────
    # Command: /status
    # ──────────────────────────────────────────

    async def cmd_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await self._typing(update)

        lines = ["*TESS Status*\n"]

        # Screencast
        sc = self.screencast
        if sc:
            lines.append(f"📡 Screencast: {sc.status()}")
        else:
            lines.append("📡 Screencast: disabled")

        # System info via psutil
        try:
            import psutil
            cpu = psutil.cpu_percent(interval=0.5)
            ram = psutil.virtual_memory()
            disk = psutil.disk_usage("/")
            lines.append(
                f"\n🖥️ CPU: `{cpu}%`\n"
                f"💾 RAM: `{ram.percent}%` ({ram.used // 1024**2} MB / {ram.total // 1024**2} MB)\n"
                f"💿 Disk: `{disk.percent}%` used"
            )
        except Exception:
            lines.append("\n_(psutil unavailable for system metrics)_")

        await self._reply(update, "\n".join(lines))

    # ──────────────────────────────────────────
    # Command: /screenshot
    # ──────────────────────────────────────────

    async def cmd_screenshot(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.effective_chat.send_action(ChatAction.UPLOAD_PHOTO)
        try:
            import mss
            from PIL import Image
            import io

            with mss.mss() as sct:
                monitors = sct.monitors
                monitor = monitors[1] if len(monitors) > 1 else monitors[0]
                raw = sct.grab(monitor)
                img = Image.frombytes("RGB", raw.size, raw.bgra, "raw", "BGRX")
                # Downscale for Telegram (max 5 MB)
                img.thumbnail((1920, 1080))
                buf = io.BytesIO()
                img.save(buf, format="JPEG", quality=75)
                buf.seek(0)

            await update.effective_message.reply_photo(
                photo=buf, caption="📸 Screenshot taken."
            )
        except Exception as e:
            await self._reply(update, f"❌ Screenshot failed: `{e}`")

    # ──────────────────────────────────────────
    # Command: /screencast
    # ──────────────────────────────────────────

    async def cmd_screencast(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await self._typing(update)
        sc = self.screencast
        if not sc:
            await self._reply(update, "❌ Screencast module not loaded.")
            return

        args = context.args  # e.g. ["stop"] or []
        sub = args[0].lower() if args else "start"

        if sub == "stop":
            result = await asyncio.get_event_loop().run_in_executor(None, sc.stop)
        elif sub == "status":
            result = sc.status()
        else:
            result = await asyncio.get_event_loop().run_in_executor(None, sc.start)

        keyboard = [
            [
                InlineKeyboardButton("⏹ Stop", callback_data="screencast_stop"),
                InlineKeyboardButton("🔄 Status", callback_data="screencast_status"),
            ]
        ]
        await update.effective_message.reply_text(
            f"📡 {result}",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )

    # ──────────────────────────────────────────
    # Command: /run <shell command>
    # ──────────────────────────────────────────

    async def cmd_run(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        cmd = " ".join(context.args).strip()
        if not cmd:
            await self._reply(update, "Usage: `/run <shell command>`")
            return

        await self._typing(update)
        exe = self.components.get("executor")
        if not exe:
            await self._reply(update, "❌ Executor component not available.")
            return

        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, exe.execute_command, cmd)
        await self._reply(update, f"```\n{result}\n```")

    # ──────────────────────────────────────────
    # Command: /recall <query>
    # ──────────────────────────────────────────

    async def cmd_recall(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = " ".join(context.args).strip()
        if not query:
            await self._reply(update, "Usage: `/recall <what to remember>`")
            return

        await self._typing(update)
        kb = self.components.get("knowledge_db")
        if not kb:
            await self._reply(update, "❌ Memory module not available.")
            return

        loop = asyncio.get_event_loop()
        results = await loop.run_in_executor(None, kb.search_memory, query, 5)
        await self._reply(update, f"🧠 *Memory Results:*\n{results}")

    # ──────────────────────────────────────────
    # Command: /clear
    # ──────────────────────────────────────────

    async def cmd_clear(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = str(update.effective_user.id)
        try:
            brain = self._brain(user_id)
            brain.clear_history()
            await self._reply(update, "🗑️ Conversation context cleared.")
        except Exception as e:
            await self._reply(update, f"❌ Could not clear context: `{e}`")

    # ──────────────────────────────────────────
    # Free-text message handler
    # ──────────────────────────────────────────

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = str(update.effective_user.id)
        user_text = update.message.text
        logger.debug(f"Telegram [{user_id}]: {user_text}")

        await self._typing(update)
        status_msg = await update.effective_message.reply_text("🧠 _Thinking…_", parse_mode="Markdown")

        try:
            loop = asyncio.get_event_loop()
            brain = self._brain(user_id)
            tele_out = self._make_callback(update, loop)

            response = await loop.run_in_executor(None, brain.generate_command, user_text)
            await loop.run_in_executor(
                None, process_action, response, self.components, brain, tele_out
            )
            await status_msg.delete()

        except Exception as e:
            logger.error(f"Message handler error: {e}", exc_info=True)
            await status_msg.edit_text(f"❌ Error: `{e}`", parse_mode="Markdown")

    # ──────────────────────────────────────────
    # Voice message handler
    # ──────────────────────────────────────────

    async def handle_voice(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await self._typing(update)
        status_msg = await update.effective_message.reply_text("🎙️ _Transcribing voice…_", parse_mode="Markdown")

        try:
            # Download the voice file
            voice_file = await context.bot.get_file(update.message.voice.file_id)
            with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as tmp:
                await voice_file.download_to_drive(tmp.name)
                tmp_path = tmp.name

            # Transcribe with whisper (if available) or fallback message
            transcript = None
            try:
                import whisper
                loop = asyncio.get_event_loop()
                model = await loop.run_in_executor(None, whisper.load_model, "base")
                result = await loop.run_in_executor(None, model.transcribe, tmp_path)
                transcript = result.get("text", "").strip()
            except ImportError:
                await status_msg.edit_text(
                    "⚠️ Voice transcription requires `openai-whisper`. "
                    "Run `pip install openai-whisper` to enable it.",
                    parse_mode="Markdown",
                )
                return
            finally:
                try:
                    os.unlink(tmp_path)
                except Exception:
                    pass

            if not transcript:
                await status_msg.edit_text("⚠️ Could not transcribe voice message.")
                return

            await status_msg.edit_text(f"🎙️ *Heard:* _{transcript}_\n\n🧠 _Processing…_", parse_mode="Markdown")

            # Re-use text pipeline
            user_id = str(update.effective_user.id)
            loop = asyncio.get_event_loop()
            brain = self._brain(user_id)
            tele_out = self._make_callback(update, loop)

            response = await loop.run_in_executor(None, brain.generate_command, transcript)
            await loop.run_in_executor(
                None, process_action, response, self.components, brain, tele_out
            )
            await status_msg.delete()

        except Exception as e:
            logger.error(f"Voice handler error: {e}", exc_info=True)
            await status_msg.edit_text(f"❌ Voice error: `{e}`", parse_mode="Markdown")

    # ──────────────────────────────────────────
    # Inline button callbacks
    # ──────────────────────────────────────────

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        data = query.data

        if data == "screenshot":
            await self.cmd_screenshot(update, context)

        elif data == "screencast_status":
            sc = self.screencast
            text = sc.status() if sc else "Screencast module not loaded."
            await query.edit_message_text(f"📡 {text}")

        elif data == "screencast_stop":
            sc = self.screencast
            if sc:
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(None, sc.stop)
                await query.edit_message_text(f"⏹ {result}")
            else:
                await query.edit_message_text("Screencast not available.")

        elif data == "sys_status":
            # Reuse status command
            await self.cmd_status(update, context)

        elif data == "help":
            await self.cmd_help(update, context)

    # ──────────────────────────────────────────
    # Bot setup & run
    # ──────────────────────────────────────────

    def run(self):
        app = ApplicationBuilder().token(self.token).build()

        # Register slash commands (shows up in Telegram UI)
        async def post_init(application):
            await application.bot.set_my_commands([
                BotCommand("start",      "Start TESS & show quick actions"),
                BotCommand("help",       "List all features"),
                BotCommand("screenshot", "Capture & send screen"),
                BotCommand("screencast", "Start/stop internet screen share"),
                BotCommand("run",        "Run a shell command"),
                BotCommand("recall",     "Search TESS memory"),
                BotCommand("status",     "Show system & service status"),
                BotCommand("clear",      "Clear your conversation context"),
            ])

        app.post_init = post_init

        # Handlers
        app.add_handler(CommandHandler("start",       self.cmd_start))
        app.add_handler(CommandHandler("help",        self.cmd_help))
        app.add_handler(CommandHandler("status",      self.cmd_status))
        app.add_handler(CommandHandler("screenshot",  self.cmd_screenshot))
        app.add_handler(CommandHandler("screencast",  self.cmd_screencast))
        app.add_handler(CommandHandler("run",         self.cmd_run))
        app.add_handler(CommandHandler("recall",      self.cmd_recall))
        app.add_handler(CommandHandler("clear",       self.cmd_clear))

        # Inline button callbacks
        app.add_handler(CallbackQueryHandler(self.handle_callback))

        # Voice messages
        app.add_handler(MessageHandler(filters.VOICE, self.handle_voice))

        # Free-text (last, so commands take priority)
        app.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message)
        )

        logger.info("🤖 TESS Telegram Bot polling…")
        app.run_polling()
