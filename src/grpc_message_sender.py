import os
import asyncio
from .log_config import setup_logging


logger = setup_logging(__name__)


class GrpcMessageSender:
    """Handles sending messages via gRPC streaming."""

    def __init__(self, response_queue: asyncio.Queue):
        """Initialize the message sender.

        Args:
            response_queue: AsyncQueue to queue messages for streaming to the client
        """
        self.response_queue = response_queue

    async def send_text(self, text: str) -> None:
        """Send a text message to the client via streaming.

        Args:
            text: The text to send (plain text, no escaping needed)
        """
        try:
            # Create a message response dict that matches the proto structure
            # This will be converted to the actual proto MessageResponse in the server
            response = {"text": text}
            await self.response_queue.put(response)
            logger.info(f"Queued text message for streaming: {text[:100]}...")
        except Exception as e:
            logger.error(f"Error queueing text message: {e}")

    async def send_image(self, image_path: str) -> None:
        """Send an image to the client via streaming.

        Args:
            image_path: Path to the image file
        """
        try:
            if os.path.exists(image_path):
                # Create an image response dict that matches the proto structure
                response = {
                    "image": {
                        "file_path": image_path,
                        "description": f"Image: {os.path.basename(image_path)}",
                    }
                }
                await self.response_queue.put(response)
                logger.info(f"Queued image {image_path} for streaming")
            else:
                logger.warning(f"Image file not found: {image_path}")
                await self.send_text(f"⚠️ Image was generated but file not found: {image_path}")
        except Exception as e:
            logger.error(f"Error queueing image: {e}")
            await self.send_text(f"❌ Error sending image: {str(e)}")
