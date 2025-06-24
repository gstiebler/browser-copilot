import asyncio
import os
from typing import List
from pydantic_ai import Agent
from pydantic_ai.mcp import MCPServerStdio
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openrouter import OpenRouterProvider
from pydantic_ai.messages import (
    ModelMessage,
    ToolCallPart,
    UserPromptPart,
    SystemPromptPart,
    TextPart,
    ToolReturnPart,
)
from dotenv import load_dotenv
import logfire

load_dotenv()


OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_MODEL = "anthropic/claude-sonnet-4"
LOGFIRE_TOKEN = os.getenv("LOGFIRE_TOKEN")

logfire.configure(token=LOGFIRE_TOKEN)
logfire.instrument_pydantic_ai()

print(OPENROUTER_MODEL)


class ConversationAgent:
    """A conversational agent that maintains message history across interactions."""

    def __init__(self):
        """Initialize the agent with model and MCP server configuration."""
        self.servers = [
            MCPServerStdio("uvx", args=["mcp-server-calculator"]),
            MCPServerStdio("npx", args=["@playwright/mcp@latest"]),
            MCPServerStdio(
                "uvx",
                args=[
                    "--from",
                    "git+https://github.com/gstiebler/pdf-mcp-server.git",
                    "pdf-mcp-server",
                ],
            ),
        ]

        # Initialize the model
        self.model = OpenAIModel(
            OPENROUTER_MODEL,
            provider=OpenRouterProvider(api_key=OPENROUTER_API_KEY),
        )

        # Initialize the agent with MCP server
        self.agent = Agent(
            self.model,
            mcp_servers=self.servers,
            system_prompt="You are a helpful agent that interacts with the browser in behalf of the user.",
        )

        # Store conversation history
        self.message_history: List[ModelMessage] = []
        self.mcp_context = None

    async def __aenter__(self):
        """Enter async context manager for MCP servers."""
        self.mcp_context = self.agent.run_mcp_servers()
        await self.mcp_context.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit async context manager for MCP servers."""
        if self.mcp_context:
            await self.mcp_context.__aexit__(exc_type, exc_val, exc_tb)

    async def run_query(self, query: str) -> str:
        """
        Run a query and store the messages in history.

        Args:
            query: The user's query

        Returns:
            The agent's response as a string
        """
        # Run the query with existing message history
        result = await self.agent.run(query, message_history=self.message_history)

        # Add all new messages to history
        self.message_history = result.all_messages()

        return result.output

    def get_messages(self) -> List[ModelMessage]:
        """Get the complete conversation history."""
        return self.message_history.copy()

    def print_messages(self):
        """Print the messages in the conversation history."""
        messages = self.get_messages()
        for i, message in enumerate(messages, 1):
            for part in message.parts:
                if isinstance(part, ToolCallPart):
                    print(f"Tool call: {part.tool_name}")
                    print(f"Tool call args: {part.args}")
                elif isinstance(part, UserPromptPart):
                    print(f"User prompt: {part.content}")
                elif isinstance(part, SystemPromptPart):
                    print(f"System prompt: {part.content}")
                elif isinstance(part, TextPart):
                    print(f"Text part: {part.content}")
                elif isinstance(part, ToolReturnPart):
                    print(f"Tool return: {part.content}")


async def main():
    # Create a conversation agent
    async with ConversationAgent() as agent:
        # First query
        response1 = await agent.run_query(
            "How many days between 2000-01-01 and 2025-03-18?"
        )
        print(f"Response 1: {response1}")

        # Second query that references the first
        response2 = await agent.run_query("What is that number divided by 365?")
        print(f"Response 2: {response2}")

        agent.print_messages()


if __name__ == "__main__":
    asyncio.run(main())
