#!/usr/bin/env python3
import os
import logging
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from pydantic_mcp import ConversationAgent

class TelegramBot:
    """A simple Telegram bot that echoes messages and responds to commands."""
    
    def __init__(self):
        """Initialize the bot with configuration and logging."""
        # Load environment variables
        load_dotenv()
        
        # Set up logging
        self._setup_logging()
        
        # Get bot token
        self.token = os.getenv('TELEGRAM_TOKEN')
        if not self.token:
            raise ValueError("No TELEGRAM_TOKEN found in environment variables!")
        
        # Create application
        self.application = Application.builder().token(self.token).build()
        
        self.agent = ConversationAgent()
        
        # Set up handlers
        self._setup_handlers()
        
        # Set up startup/shutdown handlers
        self.application.post_init = self.startup
        self.application.post_shutdown = self.shutdown
    
    def _setup_logging(self) -> None:
        """Configure logging for the bot."""
        logging.basicConfig(
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            level=logging.INFO
        )
        self.logger = logging.getLogger(__name__)
    
    def _setup_handlers(self) -> None:
        """Register all command and message handlers."""
        # Command handlers
        self.application.add_handler(CommandHandler("start", self.start_handler))
        self.application.add_handler(CommandHandler("help", self.help_handler))
        self.application.add_handler(CommandHandler("echo", self.echo_command_handler))
        
        # Message handler for non-command messages
        self.application.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, self.message_handler)
        )
        
        # Error handler
        self.application.add_error_handler(self.error_handler)
    
    async def start_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Send a welcome message when the command /start is issued."""
        user = update.effective_user
        await update.message.reply_html(
            f"Hi {user.mention_html()}! 👋\n\n"
            "I'm a simple Telegram bot. Here's what I can do:\n"
            "• /start - Show this welcome message\n"
            "• /help - Show available commands\n"
            "• /echo <text> - Echo back your message\n"
            "• Send me any text and I'll echo it back!"
        )
    
    async def help_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Send a help message when the command /help is issued."""
        help_text = """
<b>Available commands:</b>

/start - Start the bot and see welcome message
/help - Show this help message
/echo <text> - Echo back your text

You can also send me any message and I'll echo it back to you!
"""
        await update.message.reply_html(help_text)
    
    async def echo_command_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Echo the user message with /echo command."""
        if context.args:
            text_to_echo = ' '.join(context.args)
            await update.message.reply_text(f"Echo: {text_to_echo}")
        else:
            await update.message.reply_text(
                "Please provide some text to echo!\nExample: /echo Hello World"
            )
    
    async def message_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Echo regular text messages."""
        await update.message.reply_text(f"You said: {update.message.text}")
        response = await self.agent.run_query(update.message.text)
        await update.message.reply_text(response)
    
    async def error_handler(self, update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Log errors caused by updates."""
        self.logger.error("Exception while handling an update:", exc_info=context.error)
    
    async def startup(self, application: Application) -> None:
        """Initialize the agent and start MCP servers on startup."""
        await self.agent.__aenter__()
        self.logger.info("MCP servers started successfully")
    
    async def shutdown(self, application: Application) -> None:
        """Cleanup agent and stop MCP servers on shutdown."""
        await self.agent.__aexit__(None, None, None)
        self.logger.info("MCP servers stopped")
    
    def run(self) -> None:
        """Start the bot and run until interrupted."""
        self.logger.info("Bot is starting...")
        self.application.run_polling(allowed_updates=Update.ALL_TYPES)


def main() -> None:
    """Create and run the bot."""
    bot = TelegramBot()
    bot.run()


if __name__ == '__main__':
    main()