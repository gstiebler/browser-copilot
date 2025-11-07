#!/usr/bin/env python3
import os
import sys
import asyncio
import importlib
from typing import Dict, Any, AsyncIterator, Type, cast
from pathlib import Path
from concurrent import futures

from agents.conversation_agent import ConversationAgent
from .grpc_message_sender import GrpcMessageSender
from .log_config import setup_logging

# Set up module logger first
logger = setup_logging(__name__)

# Import gRPC runtime dynamically to avoid static import errors before dependencies are installed
grpc: Any
try:
    grpc = importlib.import_module("grpc")
except ImportError as exc:  # pragma: no cover - handled at runtime by installation instructions
    raise ImportError(
        "grpc module not found. Install dependencies with `uv sync` or `pip install grpcio`."
    ) from exc

# Import generated proto types
# These will be generated from proto/browser_copilot.proto using:
# python -m grpc_tools.protoc -I proto --python_out=proto --grpc_python_out=proto proto/browser_copilot.proto
pb2: Any = None
pb2_grpc: Any = None

try:
    # Add proto directory to path if not already there
    proto_path = Path(__file__).parent.parent / "proto"
    if str(proto_path) not in sys.path:
        sys.path.insert(0, str(proto_path))

    pb2 = importlib.import_module("browser_copilot_pb2")
    pb2_grpc = importlib.import_module("browser_copilot_pb2_grpc")
except ImportError as e:
    # Fallback for when proto files haven't been generated yet
    logger.warning(
        f"Proto files import failed: {e}. Run: python -m grpc_tools.protoc -I proto --python_out=proto --grpc_python_out=proto proto/browser_copilot.proto"
    )

# Define base class for gRPC servicer
_BaseServicer = cast(
    Type[Any],
    pb2_grpc.BrowserCopilotServiceServicer if pb2_grpc else object,
)


class BrowserCopilotServicer(_BaseServicer):  # type: ignore[misc, valid-type]
    """gRPC service implementation for browser copilot."""

    def __init__(self) -> None:
        """Initialize the servicer with session management."""
        # Dictionary to store agents by session_id
        self.agents: Dict[str, ConversationAgent] = {}
        self.message_senders: Dict[str, GrpcMessageSender] = {}

    async def SendMessage(self, request: Any, context: Any) -> AsyncIterator[Any]:
        """
        Handle SendMessage requests with server-side streaming.

        Args:
            request: SendMessageRequest with session_id, message_type, and content
            context: gRPC context for streaming responses

        Yields:
            MessageResponse objects for streaming back to client
        """
        session_id = request.session_id
        message_type = request.message_type
        content = request.content

        logger.info(
            f"Received message for session {session_id}: type={message_type}, content={content[:100]}..."
        )

        # Create response queue for this request
        response_queue: asyncio.Queue[Dict[str, Any]] = asyncio.Queue()

        # Get or create agent for this session
        agent = await self._get_or_create_agent(session_id, response_queue)

        # Handle different message types
        try:
            if pb2 is None:
                raise ImportError("Proto files not generated")

            if message_type == pb2.MessageType.TEXT:  # type: ignore[attr-defined]
                query = content
            elif message_type == pb2.MessageType.IMAGE:  # type: ignore[attr-defined]
                # For images, pass the file path to the agent
                query = f"An image file has been received at: {content}"
            elif message_type == pb2.MessageType.PDF:  # type: ignore[attr-defined]
                # For PDFs, save the file and pass path to agent
                if os.path.exists(content):
                    query = f"A PDF file has been received and saved to: {content}"
                else:
                    query = f"A PDF file path was provided but file not found: {content}"
            else:
                query = content

            # Run agent query in background task
            agent_task = asyncio.create_task(agent.run_query(query))

            # Stream responses from queue while agent is running
            while True:
                try:
                    # Wait for response with timeout to check if agent is done
                    try:
                        response_dict = await asyncio.wait_for(response_queue.get(), timeout=0.5)
                    except asyncio.TimeoutError:
                        # Check if agent task is done
                        if agent_task.done():
                            # Agent finished, check for any remaining messages
                            try:
                                response_dict = response_queue.get_nowait()
                            except asyncio.QueueEmpty:
                                break
                        else:
                            # Agent still running, continue waiting
                            continue

                    # Convert response dict to proto MessageResponse
                    if pb2 is None:
                        raise ImportError("Proto files not generated")

                    response = pb2.MessageResponse()  # type: ignore[attr-defined]

                    if "text" in response_dict:
                        response.text = response_dict["text"]
                    elif "image" in response_dict:
                        image_resp = pb2.ImageResponse()  # type: ignore[attr-defined]
                        image_resp.file_path = response_dict["image"]["file_path"]
                        image_resp.description = response_dict["image"].get("description", "")
                        response.image.CopyFrom(image_resp)

                    yield response

                except Exception as e:
                    logger.error(f"Error streaming response: {e}")
                    # Send error message
                    if pb2 is not None:
                        error_response = pb2.MessageResponse()  # type: ignore[attr-defined]
                        error_response.text = f"Error: {str(e)}"
                        yield error_response
                    break

            # Wait for agent task to complete
            await agent_task

        except Exception as e:
            logger.error(f"Error processing message: {e}", exc_info=True)
            if pb2 is not None:
                error_response = pb2.MessageResponse()  # type: ignore[attr-defined]
                error_response.text = f"Error processing message: {str(e)}"
                yield error_response

    async def _get_or_create_agent(
        self, session_id: str, response_queue: asyncio.Queue[Dict[str, Any]]
    ) -> ConversationAgent:
        """Get existing agent for session_id or create a new one.

        Args:
            session_id: The session identifier
            response_queue: Queue for streaming responses

        Returns:
            ConversationAgent instance for this session
        """
        if session_id not in self.agents:
            # Create message sender for this session
            message_sender = GrpcMessageSender(response_queue)

            # Create new agent
            agent = ConversationAgent(message_sender)
            await agent.__aenter__()

            self.agents[session_id] = agent
            self.message_senders[session_id] = message_sender
            logger.info(f"Created new agent for session {session_id}")

        else:
            # Update existing message sender's queue
            self.message_senders[session_id].response_queue = response_queue

        return self.agents[session_id]

    async def cleanup_session(self, session_id: str) -> None:
        """Clean up agent and resources for a session.

        Args:
            session_id: The session identifier to clean up
        """
        if session_id in self.agents:
            try:
                await self.agents[session_id].__aexit__(None, None, None)
                logger.info(f"Cleaned up agent for session {session_id}")
            except Exception as e:
                logger.error(f"Error cleaning up agent for session {session_id}: {e}")

            del self.agents[session_id]
            if session_id in self.message_senders:
                del self.message_senders[session_id]

    async def cleanup_all(self) -> None:
        """Cleanup all agents and stop MCP servers on shutdown."""
        for session_id in list(self.agents.keys()):
            await self.cleanup_session(session_id)
        logger.info("All agents cleaned up")


async def serve(port: int = 50051) -> None:
    """Start the gRPC server.

    Args:
        port: Port number to listen on
    """
    if pb2 is None or pb2_grpc is None:
        raise ImportError(
            "Proto files not generated. Run: python -m grpc_tools.protoc -I proto --python_out=proto --grpc_python_out=proto proto/browser_copilot.proto"
        )

    server = grpc.aio.server(futures.ThreadPoolExecutor(max_workers=10))
    servicer = BrowserCopilotServicer()

    pb2_grpc.add_BrowserCopilotServiceServicer_to_server(servicer, server)

    listen_addr = f"[::]:{port}"
    server.add_insecure_port(listen_addr)

    logger.info(f"Starting gRPC server on {listen_addr}")
    await server.start()

    try:
        await server.wait_for_termination()
    except KeyboardInterrupt:
        logger.info("Shutting down server...")
        await servicer.cleanup_all()
        await server.stop(5)


def main() -> None:
    """Create and run the gRPC server."""
    port = int(os.getenv("GRPC_PORT", "50051"))
    logger.info("gRPC server is starting...")
    asyncio.run(serve(port))


if __name__ == "__main__":
    main()
