from abc import ABC
from typing import Optional
from pydantic_ai import Agent, RunContext
from ..grpc_message_sender import GrpcMessageSender
from ..log_config import setup_logging


logger = setup_logging(__name__)


class BaseAgent(ABC):
    """Base class for all agents that need to send messages."""

    def __init__(self, message_sender: GrpcMessageSender):
        """Initialize the base agent.

        Args:
            message_sender: The GrpcMessageSender instance for sending messages
        """
        self.message_sender = message_sender
        self.agent: Optional[Agent[None, str]] = None

    def _setup_telegram_tools(self):
        """Set up messaging tools for the agent.

        This should be called after self.agent is initialized in the subclass.
        """
        if not self.agent:
            raise ValueError("Agent must be initialized before setting up tools")

        @self.agent.tool
        async def send_message(ctx: RunContext[None], text: str) -> str:
            """Send a text message to the user.

            Args:
                text: The text message to send

            Returns:
                Status message indicating success or failure
            """
            try:
                await self.message_sender.send_text(text)
                logger.debug(f"Sent message: {text[:100]}...")
                return "Message sent successfully"
            except Exception as e:
                logger.error(f"Failed to send message: {e}")
                return f"Failed to send message: {str(e)}"

        @self.agent.tool
        async def send_image(ctx: RunContext[None], image_path: str) -> str:
            """Send an image to the user.

            Args:
                image_path: Path to the image file to send

            Returns:
                Status message indicating success or failure
            """
            try:
                await self.message_sender.send_image(image_path)
                logger.debug(f"Sent image: {image_path}")
                return "Image sent successfully"
            except Exception as e:
                logger.error(f"Failed to send image: {e}")
                return f"Failed to send image: {str(e)}"
