from abc import ABC
from typing import Optional
from pydantic_ai import Agent, RunContext
from .telegram_message_sender import TelegramMessageSender
from .log_config import setup_logging


logger = setup_logging(__name__)


class BaseAgent(ABC):
    """Base class for all agents that need to send Telegram messages."""

    def __init__(self, message_sender: TelegramMessageSender):
        """Initialize the base agent.

        Args:
            message_sender: The TelegramMessageSender instance for sending messages
        """
        self.message_sender = message_sender
        self.agent: Optional[Agent[None, str]] = None

    def _setup_telegram_tools(self):
        """Set up Telegram messaging tools for the agent.

        This should be called after self.agent is initialized in the subclass.
        """
        if not self.agent:
            raise ValueError("Agent must be initialized before setting up tools")

        @self.agent.tool
        async def send_telegram_message(ctx: RunContext[None], text: str) -> str:
            """Send a text message to the Telegram user.

            Args:
                text: The text message to send

            Returns:
                Status message indicating success or failure
            """
            try:
                await self.message_sender.send_text(text)
                logger.debug(f"Sent telegram message: {text[:100]}...")
                return "Message sent successfully"
            except Exception as e:
                logger.error(f"Failed to send telegram message: {e}")
                return f"Failed to send message: {str(e)}"

        @self.agent.tool
        async def send_telegram_image(ctx: RunContext[None], image_path: str) -> str:
            """Send an image to the Telegram user.

            Args:
                image_path: Path to the image file to send

            Returns:
                Status message indicating success or failure
            """
            try:
                await self.message_sender.send_image(image_path)
                logger.debug(f"Sent telegram image: {image_path}")
                return "Image sent successfully"
            except Exception as e:
                logger.error(f"Failed to send telegram image: {e}")
                return f"Failed to send image: {str(e)}"
