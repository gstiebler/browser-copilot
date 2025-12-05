#!/usr/bin/env python3
"""REST API server with SSE support for browser copilot."""

import asyncio
import json
import os
from typing import Any, AsyncGenerator, Dict
from enum import Enum

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from agents.conversation_agent import ConversationAgent
from .sse_message_sender import SSEMessageSender
from .log_config import setup_logging
from agents.model_config import AgentConfig

# Set up module logger
logger = setup_logging(__name__)

# FastAPI app instance
app = FastAPI(
    title="Browser Copilot API",
    description="REST API with SSE for browser automation",
    version="1.0.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class MessageType(str, Enum):
    """Message types that can be sent to the service."""

    TEXT = "text"
    IMAGE = "image"
    PDF = "pdf"


class SendMessageRequest(BaseModel):
    """Request to send a message to the agent."""

    session_id: str
    message_type: MessageType = MessageType.TEXT
    content: str


class SessionManager:
    """Manages agent sessions."""

    def __init__(self) -> None:
        """Initialize the session manager."""
        self.agents: Dict[str, ConversationAgent] = {}
        self.message_senders: Dict[str, SSEMessageSender] = {}

    async def get_or_create_agent(
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


# Global session manager
session_manager = SessionManager()


@app.on_event("shutdown")
async def shutdown_event() -> None:
    """Clean up all sessions on server shutdown."""
    await session_manager.cleanup_all()


@app.get("/health")
async def health_check() -> Dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy"}


@app.post("/api/message")
async def send_message(request: SendMessageRequest) -> EventSourceResponse:
    """Send a message and stream responses via SSE.

    Args:
        request: The message request containing session_id, message_type, and content

    Returns:
        EventSourceResponse for streaming SSE events
    """
    logger.info(
        f"Received message for session {request.session_id}: "
        f"type={request.message_type}, content={request.content[:100]}..."
    )

    async def event_generator() -> AsyncGenerator[Dict[str, Any], None]:
        """Generate SSE events from agent responses."""
        # Create response queue for this request
        response_queue: asyncio.Queue[Dict[str, Any]] = asyncio.Queue()

        # Get or create agent for this session
        agent = await session_manager.get_or_create_agent(
            request.session_id, response_queue
        )

        # Prepare query based on message type
        if request.message_type == MessageType.TEXT:
            query = request.content
        elif request.message_type == MessageType.IMAGE:
            query = f"An image file has been received at: {request.content}"
        elif request.message_type == MessageType.PDF:
            if os.path.exists(request.content):
                query = f"A PDF file has been received and saved to: {request.content}"
            else:
                query = f"A PDF file path was provided but file not found: {request.content}"
        else:
            query = request.content

        # Run agent query in background task
        agent_task = asyncio.create_task(agent.run_query(query))

        # Stream responses from queue while agent is running
        try:
            while True:
                try:
                    # Wait for response with timeout to check if agent is done
                    try:
                        response_dict = await asyncio.wait_for(
                            response_queue.get(), timeout=0.5
                        )
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

                    # Convert response dict to SSE event data
                    yield {
                        "event": "message",
                        "data": json.dumps(response_dict),
                    }

                except Exception as e:
                    logger.error(f"Error streaming response: {e}")
                    yield {
                        "event": "error",
                        "data": json.dumps({"error": str(e)}),
                    }
                    break

            # Wait for agent task to complete
            await agent_task

            # Send done event
            yield {
                "event": "done",
                "data": json.dumps({"status": "complete"}),
            }

        except Exception as e:
            logger.error(f"Error processing message: {e}", exc_info=True)
            yield {
                "event": "error",
                "data": json.dumps({"error": f"Error processing message: {str(e)}"}),
            }

    return EventSourceResponse(event_generator())


@app.delete("/api/session/{session_id}")
async def delete_session(session_id: str) -> Dict[str, str]:
    """Delete a session and clean up resources.

    Args:
        session_id: The session identifier to delete

    Returns:
        Status message
    """
    await session_manager.cleanup_session(session_id)
    return {"status": "session deleted", "session_id": session_id}


def main() -> None:
    """Run the REST server."""
    import uvicorn

    config = AgentConfig.from_env()
    port = config.rest_port
    logger.info(f"Starting REST server on port {port}...")
    uvicorn.run(app, host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
