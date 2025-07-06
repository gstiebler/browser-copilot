#!/usr/bin/env python3
import os
import logging
from datetime import datetime
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)
from pydantic_mcp import ConversationAgent, TEMP_FOLDER


class TelegramBot:
    """A simple Telegram bot that echoes messages and responds to commands."""

    def __init__(self):
        """Initialize the bot with configuration and logging."""
        # Load environment variables
        load_dotenv()

        # Set up logging
        self._setup_logging()

        # Get bot token
        self.token = os.getenv("TELEGRAM_TOKEN")
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
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            level=logging.INFO,
        )
        self.logger = logging.getLogger(__name__)

    def _setup_handlers(self) -> None:
        """Register all command and message handlers."""
        # Command handlers
        self.application.add_handler(CommandHandler("start", self.start_handler))
        self.application.add_handler(CommandHandler("help", self.help_handler))
        self.application.add_handler(CommandHandler("echo", self.echo_command_handler))

        # PDF document handler
        self.application.add_handler(MessageHandler(filters.Document.PDF, self.pdf_handler))

        # Message handler for non-command messages
        self.application.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, self.message_handler)
        )

        # Error handler
        self.application.add_error_handler(self.error_handler)

    async def start_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Send a welcome message when the command /start is issued."""
        user = update.effective_user
        if update.message:
            user_mention = user.mention_html() if user else "there"
            await update.message.reply_html(
                f"Hi {user_mention}! 👋\n\n"
                "I'm a helpful AI assistant bot. Here's what I can do:\n"
                "• /start - Show this welcome message\n"
                "• /help - Show available commands\n"
                "• /echo <text> - Echo back your message\n"
                "• Send me any text and I'll help you with it!\n"
                "• Send me PDF files and I'll process them for you!"
            )

    async def help_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Send a help message when the command /help is issued."""
        help_text = """
<b>Available commands:</b>

/start - Start the bot and see welcome message
/help - Show this help message
/echo <text> - Echo back your text

<b>What I can do:</b>
• Send me any text message and I'll help you with it!
• Send me PDF files and I'll process them for you!
• I can interact with web browsers and take screenshots
• I can help with various tasks using AI assistance
"""
        if update.message:
            await update.message.reply_html(help_text)

    async def echo_command_handler(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Echo the user message with /echo command."""
        if update.message:
            if context.args:
                text_to_echo = " ".join(context.args)
                await update.message.reply_text(f"Echo: {text_to_echo}")
            else:
                await update.message.reply_text(
                    "Please provide some text to echo!\nExample: /echo Hello World"
                )

    async def message_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Echo regular text messages."""
        if update.message and update.message.text:
            async for chunk in self.agent.run_query(update.message.text):
                if chunk["type"] == "text":
                    await update.message.reply_text(chunk["text"])
                elif chunk["type"] == "image":
                    await update.message.reply_photo(photo=chunk["filename"])

    async def pdf_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle PDF documents sent by users."""
        if update.message and update.message.document:
            try:
                document = update.message.document
                file_name = document.file_name or f"document_{document.file_id}.pdf"

                # Generate unique filename with timestamp
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                saved_filename = f"telegram_pdf_{timestamp}_{file_name}"
                file_path = os.path.join(TEMP_FOLDER, saved_filename)

                # Ensure TEMP_FOLDER exists
                os.makedirs(TEMP_FOLDER, exist_ok=True)

                # Notify user that we're downloading
                await update.message.reply_text("📥 Downloading PDF file...")

                # Download the file
                file = await context.bot.get_file(document.file_id)
                await file.download_to_drive(file_path)

                # Send message to agent about the PDF
                message = f"A PDF file has been received and saved to: {file_path}"

                # Process the response from the agent
                async for chunk in self.agent.run_query(message):
                    if chunk["type"] == "text":
                        await update.message.reply_text(chunk["text"])
                    elif chunk["type"] == "image":
                        await update.message.reply_photo(photo=chunk["filename"])

            except Exception as e:
                self.logger.error(f"Error handling PDF: {e}")
                await update.message.reply_text(
                    "❌ Sorry, there was an error processing your PDF file. Please try again."
                )

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


if __name__ == "__main__":
    main()
