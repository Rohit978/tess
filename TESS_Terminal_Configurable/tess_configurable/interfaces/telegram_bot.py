import logging
import asyncio
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters
from ..config_manager import get_config_manager
from ..core.orchestrator import process_action

logger = logging.getLogger("TelegramBot")

class TessBot:
    def __init__(self, brain, orchestrator):
        # Fix: config_manager is at package root, accessed via ..config_manager
        # But wait, config_manager is imported at module level.
        # I just need to fix the import line.
        self.config = get_config_manager()
        self.token = self.config.config.telegram.bot_token
        
        if not self.token:
            logger.warning("TELEGRAM_BOT_TOKEN not found in config.")
            
        self.brain = brain
        self.orchestrator = orchestrator
        
        # Helper to get components
        self.components = orchestrator.components

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await context.bot.send_message(
            chat_id=update.effective_chat.id, 
            text="🤖 *TESS Terminal Configurable* is Online.\n\nI am ready to serve you.",
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
        logger.info(f"Telegram User {user_id}: {user_text}")
        
        status_msg = await context.bot.send_message(chat_id=update.effective_chat.id, text="🧠 Thinking...")
        
        try:
            # 1. Use single brain instance
            brain = self.brain
            
            # 2. Bridge callback for Orchestrator -> Telegram
            loop = asyncio.get_event_loop()
            def tele_out(text):
                asyncio.run_coroutine_threadsafe(
                    context.bot.send_message(chat_id=update.effective_chat.id, text=text),
                    loop
                )

            # 3. Generate Action
            # Use generate_command instead of think
            response = await loop.run_in_executor(None, brain.generate_command, user_text)
            
            # 4. Execute Action
            await loop.run_in_executor(None, process_action, response, self.components, brain, tele_out)
            
            await status_msg.edit_text("✅ Done.")
            
        except Exception as e:
            logger.error(f"Telegram Handler Error: {e}")
            await context.bot.send_message(chat_id=update.effective_chat.id, text=f"❌ Error: {str(e)}")

    def run(self):
        if not self.token:
            logger.error("Cannot start Telegram Bot: No token provided.")
            return

        app = ApplicationBuilder().token(self.token).build()
        
        app.add_handler(CommandHandler("start", self.start))
        app.add_handler(CommandHandler("help", self.help_command))
        app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), self.handle_message))
        
        logger.info("🤖 Telegram Bot starting poll...")
        app.run_polling()
