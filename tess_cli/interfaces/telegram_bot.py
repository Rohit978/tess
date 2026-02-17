import logging
import asyncio
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters
from ..core.config import Config
from ..core.logger import setup_logger
from ..core.profile_manager import ProfileManager
from ..core.orchestrator import process_action

logger = setup_logger("TelegramBot")

class TessBot:
    def __init__(self, profile_manager, launcher, browser_ctrl, sys_ctrl, file_mgr, knowledge_db, planner, web_browser, task_registry, whatsapp_client, youtube_client, executor, screencast=None):
        self.token = Config.TELEGRAM_BOT_TOKEN
        if not self.token:
            raise ValueError("TELEGRAM_BOT_TOKEN not found.")
            
        # Dependencies
        self.profile_manager = profile_manager
        
        # Bundle components for orchestrator
        self.components = {
            'launcher': launcher,
            'browser_ctrl': browser_ctrl,
            'sys_ctrl': sys_ctrl,
            'file_mgr': file_mgr,
            'knowledge_db': knowledge_db,
            'planner': planner,
            'web_browser': web_browser,
            'task_registry': task_registry,
            'whatsapp': whatsapp_client, # Renamed from 'whatsapp_client' to match orchestrator
            'youtube_client': youtube_client,
            'executor': executor,
            'screencast': screencast
        }

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await context.bot.send_message(
            chat_id=update.effective_chat.id, 
            text="🤖 *TESS Terminal Pro* is Online.\n\nMulti-user profiles are active. Your memory and history are isolated to your ID.",
            parse_mode='Markdown'
        )

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        help_text = """
*TESS Command Center*
Just talk to me naturally. I can:
- Launch apps ("Open Notepad")
- Run commands ("Ping google.com")
- Browse web ("Search for TESS AI")
- Control system ("Volume up")
- Handle files ("List files in Desktop")
- And more!
        """
        await context.bot.send_message(chat_id=update.effective_chat.id, text=help_text, parse_mode='Markdown')

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = str(update.effective_user.id)
        user_text = update.message.text
        logger.debug(f"Telegram User {user_id}: {user_text}")
        
        status_msg = await context.bot.send_message(chat_id=update.effective_chat.id, text="🧠 Thinking...")
        
        try:
            # 1. Get isolated brain
            brain = self.profile_manager.get_brain(user_id)
            
            # 2. Bridge callback for Orchestrator -> Telegram
            loop = asyncio.get_event_loop()
            def tele_out(text):
                asyncio.run_coroutine_threadsafe(
                    context.bot.send_message(chat_id=update.effective_chat.id, text=text),
                    loop
                )

            # 3. Generate Action
            response = await loop.run_in_executor(None, brain.generate_command, user_text)
            
            # 4. Execute Action
            await loop.run_in_executor(None, process_action, response, self.components, brain, tele_out)
            
            await status_msg.edit_text("✅ Done.")
            
        except Exception as e:
            logger.error(f"Telegram Handler Error: {e}")
            await context.bot.send_message(chat_id=update.effective_chat.id, text=f"❌ Error: {str(e)}")

    def run(self):
        app = ApplicationBuilder().token(self.token).build()
        
        app.add_handler(CommandHandler("start", self.start))
        app.add_handler(CommandHandler("help", self.help_command))
        app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), self.handle_message))
        
        logger.debug("🤖 Telegram Bot starting poll...")
        app.run_polling()
