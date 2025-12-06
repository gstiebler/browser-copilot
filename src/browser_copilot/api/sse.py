import asyncio
import os

from ..config import setup_logging

logger = setup_logging(__name__)


class SSEMessageSender:
    """Handles sending messages via Server-Sent Events streaming."""

    def __init__(self, response_queue: asyncio.Queue):
        """Initialize the message sender.

        Args:
            response_queue: AsyncQueue to queue messages for streaming to the client
        """
        self.response_queue = response_queue

    async def send_text(self, text: str) -> None:
        """Send a text message to the client via SSE streaming.

        Args:
            text: The text to send (plain text, no escaping needed)
        """
        try:
            # Create a message response dict for SSE streaming
            # This will be converted to SSE format in the REST server
            response = {"text": text}
            await self.response_queue.put(response)
            logger.info(f"Queued text message for SSE streaming: {text[:100]}...")
        except Exception as e:
            logger.error(f"Error queueing text message: {e}")

    async def send_text_chunk(self, text_chunk: str) -> None:
        """Send a text chunk for streaming (incremental updates).

        Args:
            text_chunk: A chunk of text to stream (can be partial)
        """
        try:
            # Create a message response dict for streaming chunks
            # The client will accumulate these chunks
            response = {"text": text_chunk}
            await self.response_queue.put(response)
            logger.debug(f"Queued text chunk for SSE streaming: {text_chunk[:50]}...")
        except Exception as e:
            logger.error(f"Error queueing text chunk: {e}")

    async def send_image(self, image_path: str) -> None:
        """Send an image to the client via SSE streaming.

        Args:
            image_path: Path to the image file
        """
        try:
            if os.path.exists(image_path):
                # Create an image response dict for SSE streaming
                response = {
                    "image": {
                        "file_path": image_path,
                        "description": f"Image: {os.path.basename(image_path)}",
                    }
                }
                await self.response_queue.put(response)
                logger.info(f"Queued image {image_path} for SSE streaming")
            else:
                logger.warning(f"Image file not found: {image_path}")
                await self.send_text(f"⚠️ Image was generated but file not found: {image_path}")
        except Exception as e:
            logger.error(f"Error queueing image: {e}")
            await self.send_text(f"❌ Error sending image: {str(e)}")
