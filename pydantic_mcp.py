import asyncio
import json
import os
from typing import List, AsyncGenerator, Union, Any
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
    RetryPromptPart,
    ThinkingPart,
)
from dotenv import load_dotenv
import logfire

load_dotenv()


OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "")
LOGFIRE_TOKEN = os.getenv("LOGFIRE_TOKEN", "")

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
            MCPServerStdio("npx", args=["@playwright/mcp@latest", "--output-dir", TEMP_FOLDER]),
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
                args=["@modelcontextprotocol/server-filesystem", TEMP_FOLDER],
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

    async def __aenter__(self) -> "ConversationAgent":
        """Enter async context manager for MCP servers."""
        self.mcp_context = self.agent.run_mcp_servers()
        await self.mcp_context.__aenter__()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit async context manager for MCP servers."""
        if self.mcp_context:
            await self.mcp_context.__aexit__(exc_type, exc_val, exc_tb)

    async def run_query(self, query: str) -> AsyncGenerator[dict, None]:
        """
        Run a query and store the messages in history, yielding intermediate results.

        Args:
            query: The user's query

        Yields:
            Intermediate messages and final response
        """
        # Run the query with existing message history
        async with self.agent.iter(query, message_history=self.message_history) as agent_run:
            last_tool_call = None
            async for node in agent_run:
                if isinstance(node, CallToolsNode):
                    for part in node.model_response.parts:
                        if isinstance(part, ToolCallPart):
                            last_tool_call = part
                        yield {"type": "text", "text": self.get_part_text(part)}
                elif isinstance(node, ModelRequestNode):
                    for part in node.request.parts:  # type: ignore[assignment]
                        if (
                            isinstance(part, ToolReturnPart)
                            and last_tool_call
                            and part.tool_name
                            == last_tool_call.tool_name
                            == "browser_take_screenshot"
                        ):
                            print(f"screenshot args: {last_tool_call.args}")
                            if isinstance(last_tool_call.args, str):
                                parsed_args = json.loads(last_tool_call.args)
                            elif isinstance(last_tool_call.args, dict):
                                parsed_args = last_tool_call.args
                            else:
                                parsed_args = {}
                            result = {
                                "type": "image",
                                "filename": f"{TEMP_FOLDER}/{parsed_args.get('filename', 'screenshot.png')}",
                            }
                            yield result

            if agent_run.result is not None:
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

    def print_part(self, part: Any) -> None:
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

    def get_part_text(
        self,
        part: Union[
            ToolCallPart,
            UserPromptPart,
            SystemPromptPart,
            TextPart,
            ToolReturnPart,
            RetryPromptPart,
            ThinkingPart,
        ],
    ) -> str:
        if isinstance(part, ToolCallPart):
            return f"Tool call: {part.tool_name}\nTool call args: {part.args}"
        elif isinstance(part, UserPromptPart):
            content = part.content
            if isinstance(content, str):
                return content
            else:
                return str(content)
        elif isinstance(part, SystemPromptPart):
            return part.content
        elif isinstance(part, TextPart):
            return part.content
        elif isinstance(part, ToolReturnPart):
            return part.content
        elif isinstance(part, RetryPromptPart):
            content = part.content  # type: ignore[assignment]
            if isinstance(content, str):
                return content
            else:
                return str(content)
        elif isinstance(part, ThinkingPart):
            return part.content
        else:
            return ""


async def main():
    # Create a conversation agent
    async with ConversationAgent() as agent:
        # First query
        print("Response 1:")
        async for chunk in agent.run_query(
            "Open the google website, take a screenshot of the page to the file screenshot.png"
        ):
            print(chunk, end="", flush=True)
            print()
        print()


if __name__ == "__main__":
    asyncio.run(main())
