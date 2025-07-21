import asyncio
import os
from typing import List, AsyncGenerator, Any
from pydantic_ai import Agent, CallToolsNode, ModelRequestNode, UserPromptNode, RunContext
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
from browser_agent import BrowserAgent


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

    def __init__(self, node_processor=None):
        """Initialize the agent with model and MCP server configuration."""
        self.node_processor = node_processor
        mcp_servers = [
            MCPServerStdio("uvx", args=["mcp-server-calculator"]),
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
            system_prompt="""You are a helpful AI assistant that can help users with various tasks.
You have access to:
- A calculator for mathematical operations
- A PDF reader for processing PDF documents
- A memory server for storing and retrieving information
- A filesystem server for managing files in the temp folder
- A browser interaction tool for web-related tasks

When users ask you to interact with websites, take screenshots, or perform browser automation tasks,
use the browser_interact tool to delegate these tasks to the browser agent.

After each iteration, reflect if there's something useful that you should store in the memory server.
Examples of useful information to store include:
- Important URLs or web pages
- User preferences
- User information that can be useful in future interactions
- Processes that have a chance to be repeated in the future

ALWAYS start by listing the memories in the root of the memory server.
""",
        )

        # Store conversation history
        self.message_history: List[ModelMessage] = []
        self.mcp_context = None

        # Initialize browser agent
        self.browser_agent = None

        # Create browser interaction tool
        @self.agent.tool
        async def browser_interact(ctx: RunContext[None], task: str) -> str:
            """Interact with web browsers to perform tasks like navigation, screenshots, and automation.

            Args:
                task: Description of the browser task to perform

            Returns:
                Result of the browser interaction
            """
            if not self.browser_agent:
                return "Browser agent not initialized. Please try again."

            results = []
            async for chunk in self.browser_agent.execute_browser_task(task, usage=ctx.usage):
                if chunk["type"] == "text":
                    results.append(chunk["text"])
                elif chunk["type"] == "image":
                    # Store the image path for the main agent to process
                    self._pending_screenshot = chunk["filename"]
                    results.append(f"Screenshot saved to: {chunk['filename']}")

            return "\n".join(results) if results else "Browser task completed."

    async def __aenter__(self) -> "ConversationAgent":
        """Enter async context manager for MCP servers."""
        self.mcp_context = self.agent.run_mcp_servers()
        await self.mcp_context.__aenter__()

        # Initialize browser agent
        self.browser_agent = BrowserAgent(self.model)
        await self.browser_agent.__aenter__()

        self._pending_screenshot = None
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit async context manager for MCP servers."""
        if self.browser_agent:
            await self.browser_agent.__aexit__(exc_type, exc_val, exc_tb)
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
            nodes_so_far = []
            async for node in agent_run:
                nodes_so_far.append(node)
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
                        if isinstance(part, TextPart):
                            result = {
                                "type": "text",
                                "node_type": "CallToolsNode",
                                "text": part.content,
                            }
                            yield result
                # Check if we have a pending screenshot from browser agent
                if self._pending_screenshot:
                    yield {
                        "type": "image",
                        "node_type": "BrowserScreenshot",
                        "filename": self._pending_screenshot,
                    }
                    self._pending_screenshot = None

            if agent_run.result is not None:
                self.message_history = self.memory_summarizer(agent_run.result.all_messages())

    def memory_summarizer(self, nodes: List[ModelMessage]) -> List[ModelMessage]:
        """
        Summarize the memory nodes and return a list of ModelMessage objects.

        Args:
            nodes: List of ModelMessage objects to summarize
        Returns:
            List of summarized ModelMessage objects
        """
        # count the number of ToolResult parts in the nodes
        tool_result_count = sum(
            sum(1 for part in node.parts if isinstance(part, ToolReturnPart)) for node in nodes
        )
        # if theres more than 1 ToolResult part, leave only the last one, replacing the others with a TextPart
        if tool_result_count > 1:
            removed_tool_return_count = 0
            for node in nodes:
                if isinstance(node, ModelRequestNode):
                    processed_parts: list = []
                    for part in node.request.parts:
                        if isinstance(part, ToolReturnPart):
                            removed_tool_return_count += 1
                            if removed_tool_return_count == tool_result_count:
                                processed_parts.append(part)
                            else:
                                processed_parts.append(
                                    TextPart(content="Tool return removed for memory reasons")
                                )
                        else:
                            processed_parts.append(part)
                    node.request.parts = processed_parts

            return nodes

        return nodes

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

        logger.info(black.format_str(repr(agent.get_messages()), mode=black.Mode()))


if __name__ == "__main__":
    asyncio.run(main())
