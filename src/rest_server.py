#!/usr/bin/env python3
import os
import asyncio
import uuid
from typing import Dict, Any, AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException, UploadFile, File, BackgroundTasks
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from agents.conversation_agent import ConversationAgent
from .sse_message_sender import SSEMessageSender
from .log_config import setup_logging
from agents.model_config import AgentConfig

# Set up module logger
logger = setup_logging(__name__)


class MessageRequest(BaseModel):
    """Request model for sending messages."""

    message_type: str  # "TEXT", "IMAGE", "PDF"
    content: str


class RestServer:
    """REST server implementation for browser copilot with SSE streaming."""

    def __init__(self) -> None:
        """Initialize the server with session management."""
        # Dictionary to store agents by session_id
        self.agents: Dict[str, ConversationAgent] = {}
        self.message_senders: Dict[str, SSEMessageSender] = {}

    async def startup(self) -> None:
        """Startup tasks for the server."""
        logger.info("REST server starting up...")

    async def shutdown(self) -> None:
        """Shutdown tasks for the server."""
        logger.info("REST server shutting down...")
        await self.cleanup_all()

    async def send_message(
        self, session_id: str, message: MessageRequest
    ) -> AsyncGenerator[str, None]:
        """
        Handle message requests with SSE streaming.

        Args:
            session_id: Session identifier
            message: MessageRequest with message_type and content

        Yields:
            SSE formatted strings for streaming back to client
        """
        logger.info(
            f"Received message for session {session_id}: type={message.message_type}, content={message.content[:100]}..."
        )

        # Create response queue for this request
        response_queue: asyncio.Queue[Dict[str, Any]] = asyncio.Queue()

        # Get or create agent for this session
        agent = await self._get_or_create_agent(session_id, response_queue)

        # Handle different message types
        try:
            if message.message_type.upper() == "TEXT":
                query = message.content
            elif message.message_type.upper() == "IMAGE":
                # For images, pass the file path to the agent
                query = f"An image file has been received at: {message.content}"
            elif message.message_type.upper() == "PDF":
                # For PDFs, check if file exists and pass path to agent
                if os.path.exists(message.content):
                    query = f"A PDF file has been received and saved to: {message.content}"
                else:
                    query = f"A PDF file path was provided but file not found: {message.content}"
            else:
                query = message.content

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

                    # Convert response dict to SSE format
                    if "text" in response_dict:
                        yield f"event: text\ndata: {response_dict['text']}\n\n"
                    elif "image" in response_dict:
                        import json

                        image_data = json.dumps(
                            {
                                "file_path": response_dict["image"]["file_path"],
                                "description": response_dict["image"].get("description", ""),
                            }
                        )
                        yield f"event: image\ndata: {image_data}\n\n"

                except Exception as e:
                    logger.error(f"Error streaming response: {e}")
                    # Send error event
                    yield f"event: error\ndata: Error: {str(e)}\n\n"
                    break

            # Wait for agent task to complete
            await agent_task

            # Send completion event
            yield "event: complete\ndata: {}\n\n"

        except Exception as e:
            logger.error(f"Error processing message: {e}", exc_info=True)
            yield f"event: error\ndata: Error processing message: {str(e)}\n\n"

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
            message_sender = SSEMessageSender(response_queue)

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
        """Cleanup all agents on shutdown."""
        for session_id in list(self.agents.keys()):
            await self.cleanup_session(session_id)
        logger.info("All agents cleaned up")


# Global server instance
rest_server = RestServer()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for FastAPI app."""
    await rest_server.startup()
    yield
    await rest_server.shutdown()


# Create FastAPI app
app = FastAPI(
    title="Browser Copilot API",
    description="REST API for Browser Copilot with Server-Sent Events streaming",
    version="0.1.0",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/api/v1/sessions/{session_id}/messages")
async def send_message_endpoint(session_id: str, message: MessageRequest):
    """Send a message and get SSE stream of responses."""
    if not session_id:
        raise HTTPException(status_code=400, detail="Session ID is required")

    return StreamingResponse(
        rest_server.send_message(session_id, message),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "*",
        },
    )


@app.post("/api/v1/sessions/{session_id}/upload")
async def upload_file_endpoint(
    session_id: str, file: UploadFile = File(...), file_type: str = "IMAGE"
):
    """Upload a file and return its path for message sending."""
    if not session_id:
        raise HTTPException(status_code=400, detail="Session ID is required")

    # Create temp directory if it doesn't exist
    temp_dir = Path(os.environ.get("TEMPDIR", "/tmp")) / "browser_copilot" / session_id
    temp_dir.mkdir(parents=True, exist_ok=True)

    # Generate unique filename
    file_extension = Path(file.filename or "").suffix if file.filename else ""
    file_path = temp_dir / f"{uuid.uuid4()}{file_extension}"

    # Save file
    with open(file_path, "wb") as f:
        content = await file.read()
        f.write(content)

    logger.info(f"Uploaded file for session {session_id}: {file_path}")

    return {"file_path": str(file_path), "file_type": file_type.upper(), "filename": file.filename}


@app.delete("/api/v1/sessions/{session_id}")
async def delete_session_endpoint(session_id: str, background_tasks: BackgroundTasks):
    """Clean up a session and its resources."""
    if not session_id:
        raise HTTPException(status_code=400, detail="Session ID is required")

    if session_id not in rest_server.agents:
        raise HTTPException(status_code=404, detail="Session not found")

    # Clean up session in background
    background_tasks.add_task(rest_server.cleanup_session, session_id)

    return {"message": f"Session {session_id} cleanup initiated"}


@app.get("/api/v1/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "active_sessions": len(rest_server.agents)}


async def serve(host: str = "0.0.0.0", port: int = 8000) -> None:
    """Start the REST server.

    Args:
        host: Host to bind to
        port: Port number to listen on
    """
    config = uvicorn.Config(
        app,
        host=host,
        port=port,
        log_config=None,  # Use our existing logging config
        access_log=False,  # Disable uvicorn access logs to avoid duplication
    )
    server = uvicorn.Server(config)

    logger.info(f"Starting REST server on {host}:{port}")
    await server.serve()


def main() -> None:
    """Create and run the REST server."""
    config = AgentConfig.from_env()
    port = config.rest_port
    logger.info("REST server is starting...")
    asyncio.run(serve(port=port))


if __name__ == "__main__":
    main()
