import asyncio
import os
from typing import List, AsyncGenerator
from pydantic_ai import Agent, CallToolsNode, ModelRequestNode
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
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL")
LOGFIRE_TOKEN = os.getenv("LOGFIRE_TOKEN")

logfire.configure(token=LOGFIRE_TOKEN)
logfire.instrument_pydantic_ai()

print(f"Using model: {OPENROUTER_MODEL}")

user_home = os.path.expanduser("~")
TEMP_FOLDER = f"{user_home}/Documents/temp"


class ConversationAgent:
    """A conversational agent that maintains message history across interactions."""

    def __init__(self):
        """Initialize the agent with model and MCP server configuration."""
        mcp_servers = [
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
            MCPServerStdio(
                "npx",
                args=["-y", "@modelcontextprotocol/server-memory"],
                env={"MEMORY_FILE_PATH": f"{user_home}/Documents/datas/ai_memory.json"},
            ),
            MCPServerStdio(
                "npx",
                args=[
                    "@modelcontextprotocol/server-filesystem",
                    TEMP_FOLDER,
                    "/var",
                    "/tmp",
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
            mcp_servers=mcp_servers,
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

    async def run_query(self, query: str) -> AsyncGenerator[str, None]:
        """
        Run a query and store the messages in history, yielding intermediate results.

        Args:
            query: The user's query

        Yields:
            Intermediate messages and final response
        """
        # Run the query with existing message history
        async with self.agent.iter(
            query, message_history=self.message_history
        ) as agent_run:
            async for node in agent_run:
                if isinstance(node, CallToolsNode):
                    parts = node.model_response.parts

                    for part in parts:
                        yield self.get_part_text(part)
                elif isinstance(node, ModelRequestNode):
                    parts = node.request.parts
                    for part in parts:
                        if isinstance(part, UserPromptPart):
                            print(f"User prompt: {part.content}")

            self.message_history = agent_run.result.all_messages()

    def get_messages(self) -> List[ModelMessage]:
        """Get the complete conversation history."""
        return self.message_history.copy()

    def print_messages(self):
        """Print the messages in the conversation history."""
        messages = self.get_messages()
        for message in messages:
            for part in message.parts:
                self.print_part(part)

    def print_part(self, part):
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

    def get_part_text(self, part):
        if isinstance(part, ToolCallPart):
            return f"Tool call: {part.tool_name}\nTool call args: {part.args}"
        elif isinstance(part, UserPromptPart):
            return part.content
        elif isinstance(part, SystemPromptPart):
            return part.content
        elif isinstance(part, TextPart):
            return part.content
        elif isinstance(part, ToolReturnPart):
            return part.content


async def main():
    # Create a conversation agent
    async with ConversationAgent() as agent:
        # First query
        print("Response 1:")
        async for chunk in agent.run_query(
            f"""Open the google website, take a screenshot of the page and save it to the temp folder. 
            You may need to move the file from /var to the temp folder. The temp folder is {TEMP_FOLDER}.
            When moving the file, use the full path of the file both in 'destination' and 'source' arguments.
            """
        ):
            print(chunk, end="", flush=True)
            print()
        print()


if __name__ == "__main__":
    asyncio.run(main())
