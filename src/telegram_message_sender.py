import os
import re
from telegram import Bot
from .log_config import setup_logging


logger = setup_logging(__name__)


class TelegramMessageSender:
    """Handles sending messages to Telegram users."""

    def __init__(self, bot: Bot, chat_id: int):
        """Initialize the message sender.

        Args:
            bot: The Telegram Bot instance
            chat_id: The chat ID to send messages to
        """
        self.bot = bot
        self.chat_id = chat_id

    async def send_text(self, text: str) -> None:
        """Send a text message to the user.

        Args:
            text: The text to send (will be escaped for MarkdownV2)
        """
        try:
            escaped_text = self._escape_markdown_v2(text)
            await self.bot.send_message(
                chat_id=self.chat_id, text=escaped_text, parse_mode="MarkdownV2"
            )
            logger.info(f"Sent text message to chat {self.chat_id}")
        except Exception as e:
            logger.error(f"Error sending text message: {e}")
            # Try sending without markdown as fallback
            try:
                await self.bot.send_message(chat_id=self.chat_id, text=text)
            except Exception as e2:
                logger.error(f"Error sending plain text message: {e2}")

    async def send_image(self, image_path: str) -> None:
        """Send an image to the user.

        Args:
            image_path: Path to the image file
        """
        try:
            if os.path.exists(image_path):
                await self.bot.send_photo(chat_id=self.chat_id, photo=image_path)
                logger.info(f"Sent image {image_path} to chat {self.chat_id}")
            else:
                logger.warning(f"Image file not found: {image_path}")
                await self.send_text(f"⚠️ Image was generated but file not found: {image_path}")
        except Exception as e:
            logger.error(f"Error sending image: {e}")
            await self.send_text(f"❌ Error sending image: {str(e)}")

    @staticmethod
    def _escape_markdown_v2(text: str) -> str:
        """
        Escape special characters for Telegram's MarkdownV2 parse mode.

        According to Telegram docs, any character with code between 1 and 126
        can be escaped with a preceding '\' character.
        """
        # Characters that need to be escaped in MarkdownV2
        escape_chars = r"_*[]()~`>#+-=|{}.!"

        # Escape each special character with a backslash
        escaped_text = re.sub(f"([{re.escape(escape_chars)}])", r"\\\1", text)

        return escaped_text
