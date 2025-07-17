import asyncio
import json
import os
from typing import List, AsyncGenerator, Any
from pydantic_ai import Agent, CallToolsNode, ModelRequestNode, UserPromptNode
from pydantic_ai.mcp import MCPServerStdio
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.models.gemini import GeminiModel
from pydantic_ai.providers.openrouter import OpenRouterProvider
from pydantic_ai.providers.google_gla import GoogleGLAProvider
from pydantic_ai.messages import (
    ModelMessage,
    ToolCallPart,
    UserPromptPart,
    SystemPromptPart,
    TextPart,
    ToolReturnPart,
)
import logfire
from pydantic_graph import End
from log_config import setup_logging
from colorama import Fore, Style
import black


OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "")
LOGFIRE_TOKEN = os.getenv("LOGFIRE_TOKEN", "")

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")


# Set up logging
logger = setup_logging(__name__)

logfire.configure(token=LOGFIRE_TOKEN)
logfire.instrument_pydantic_ai()


TEMP_FOLDER = os.getenv("TEMPDIR", "/tmp")


def get_model():
    if OPENROUTER_MODEL != "":
        print(f"Using openrouter model: {OPENROUTER_MODEL}")
        return OpenAIModel(
            OPENROUTER_MODEL,
            provider=OpenRouterProvider(api_key=OPENROUTER_API_KEY),
        )
    else:
        print(f"Using Gemini model: {GEMINI_MODEL}")
        return GeminiModel(GEMINI_MODEL, provider=GoogleGLAProvider(api_key=GEMINI_API_KEY))


class ConversationAgent:
    """A conversational agent that maintains message history across interactions."""

    def __init__(self):
        """Initialize the agent with model and MCP server configuration."""
        mcp_servers = [
            MCPServerStdio("uvx", args=["mcp-server-calculator"]),
            MCPServerStdio(
                "npx",
                args=[
                    "@playwright/mcp@latest",
                    "--output-dir",
                    TEMP_FOLDER,
                    "--image-responses",
                    "omit",
                ],
            ),
            MCPServerStdio(
                "uvx",
                args=[
                    "--from",
                    "git+https://github.com/gstiebler/pdf-mcp-server.git",
                    "pdf-mcp-server",
                ],
            ),
            MCPServerStdio(
                "uvx",
                args=[
                    "--from",
                    "git+https://github.com/gstiebler/h-memory-mcp-server.git",
                    "h-memory-mcp-server",
                    "--memory-file",
                    "memory.json",
                ],
            ),
            MCPServerStdio(
                "npx",
                args=["@modelcontextprotocol/server-filesystem", TEMP_FOLDER],
            ),
        ]

        # Initialize the model
        self.model = get_model()

        # Initialize the agent with MCP server
        self.agent = Agent(
            self.model,
            mcp_servers=mcp_servers,
            system_prompt="""You are a helpful agent that interacts with the browser in behalf of the user.
You can open websites, take screenshots, and perform other tasks using the browser.
You can also use tools like a calculator, PDF reader, and memory server to assist the user.
You will receive user queries and respond with the appropriate actions or information.
You will use the tools provided by the MCP servers to perform tasks.
After each iteration, reflect if there's something useful that you should store in the memory server.
Examples of useful information to store include:
- Important URLs or web pages
- Interactions with Playwright or other browser actions
- User preferences
- User informations that can be useful in future interactions
- Processes that has a chance to be repeated in the future
ALWAYS start by listing the memories in the root of the memory server.
""",
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
                color_by_node: dict[type, str] = {
                    CallToolsNode: Fore.GREEN,
                    ModelRequestNode: Fore.BLUE,
                    UserPromptNode: Fore.YELLOW,
                    End: Fore.MAGENTA,
                }
                color = color_by_node.get(type(node), Fore.RED)
                logger.debug(
                    f"Processing node: {color}{black.format_str(repr(node), mode=black.Mode())}{Style.RESET_ALL}"
                )
                # if isinstance(node, End):
                #     yield {"type": "text", "node_type": "End", "text": node.data.output}
                if isinstance(node, CallToolsNode):
                    for part in node.model_response.parts:
                        if isinstance(part, ToolCallPart):
                            last_tool_call = part
                        elif isinstance(part, TextPart):
                            result = {
                                "type": "text",
                                "node_type": "CallToolsNode",
                                "text": part.content,
                            }
                            yield result
                elif isinstance(node, ModelRequestNode):
                    for part in node.request.parts:  # type: ignore[assignment]
                        if (
                            isinstance(part, ToolReturnPart)
                            and last_tool_call
                            and part.tool_name
                            == last_tool_call.tool_name
                            == "browser_take_screenshot"
                        ):
                            logger.info(f"screenshot args: {last_tool_call.args}")
                            print(f"screenshot args: {last_tool_call.args}")
                            if isinstance(last_tool_call.args, str):
                                parsed_args = json.loads(last_tool_call.args)
                            elif isinstance(last_tool_call.args, dict):
                                parsed_args = last_tool_call.args
                            else:
                                parsed_args = {}
                            result = {
                                "type": "image",
                                "node_type": "ModelRequestNode",
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


async def main():
    """Simple usage example demonstrating the ConversationAgent."""
    logger.info("Starting ConversationAgent example")

    # Create a conversation agent
    async with ConversationAgent() as agent:
        # Example 2: Taking a screenshot
        logger.info("Open the Canada Life website, and take a screenshot")
        logger.info("\n=== Example 2: Taking a screenshot ===")
        async for chunk in agent.run_query("Open the Canada Life website, and take a screenshot"):
            logger.info(chunk)


if __name__ == "__main__":
    asyncio.run(main())
