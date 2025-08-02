import asyncio
import os
from typing import List, AsyncGenerator, Any, Optional
from pydantic_ai import Agent, RunContext
from pydantic_ai.mcp import MCPServerStdio
from pydantic_ai.messages import ModelMessage
import logfire

from src.input_utils import wait_for_input
from .log_config import setup_logging, console
import black
from .browser_agent import BrowserAgent
from .model_config import get_model
from rich.markdown import Markdown
from .node_utils import print_node


LOGFIRE_TOKEN = os.getenv("LOGFIRE_TOKEN", "")


# Set up logging
logger = setup_logging(__name__)

file_log_level = os.getenv("FILE_LOG_LEVEL", "DEBUG").upper()
logfire_scrubbing = False if file_log_level == "DEBUG" else None
logfire.configure(token=LOGFIRE_TOKEN, scrubbing=logfire_scrubbing, service_name="pydantic_ai")  # type: ignore
logfire.instrument_pydantic_ai()


TEMP_FOLDER = os.getenv("TEMPDIR", "/tmp")

MAIN_MODEL_NAME = os.getenv("MAIN_MODEL", "")
BROWSER_MODEL_NAME = os.getenv("BROWSER_MODEL", "")

system_prompt = """You are a helpful AI assistant that can help users with various tasks.
You have access to:
- A calculator for mathematical operations
- A PDF reader for processing PDF documents
- A memory server for storing and retrieving information
- A filesystem server for managing files in the temp folder
- A browser interaction tool for web-related tasks

When users ask you to interact with websites, take screenshots, or perform browser automation tasks,
use the browser_interact tool to delegate these tasks to the browser agent.

You can also use the capture_webpage_snapshot tool to get a comprehensive view of the current webpage,
including a summary and list of all interactable elements, which is useful for understanding what
actions are possible on the page.

After each iteration, reflect if there's something useful that you should store in the memory server.
Examples of useful information to store include:
- Important URLs or web pages
- User preferences
- User information that can be useful in future interactions
- Processes that have a chance to be repeated in the future

ALWAYS start by listing the memories in the root of the memory server.
"""


class ConversationAgent:
    """A conversational agent that maintains message history across interactions."""

    def __init__(self, node_processor: Any = None) -> None:
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
        self.model = get_model(MAIN_MODEL_NAME)

        # Initialize the agent with MCP server
        self.agent = Agent(
            self.model,
            mcp_servers=mcp_servers,
            system_prompt=system_prompt,
            name="ConversationAgent",
        )

        # Store conversation history
        self.message_history: List[ModelMessage] = []
        self.mcp_context: Optional[Any] = None

        # Initialize browser agent
        self.browser_agent: Optional[BrowserAgent] = None
        self._pending_screenshot: Optional[str] = None

        # Create browser interaction tool
        @self.agent.tool
        async def browser_interact(ctx: RunContext[None], task: str) -> str:
            """Interact with web browsers to perform tasks like navigation, screenshots, and automation.
            It can:
            - Navigate to websites
            - Take screenshots
            - Click on elements
            - Fill forms
            - Extract information from web pages
            - Perform various browser automation tasks

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

        # Create page snapshot tool
        @self.agent.tool
        async def capture_webpage_snapshot(ctx: RunContext[None]) -> str:
            """Capture a comprehensive snapshot of the current web page including:
            - A screenshot of the current page
            - A summary of the page content
            - A complete list of all interactable UI elements

            This tool analyzes the page and returns a structured list of all elements
            you can interact with (buttons, links, inputs, etc.) along with their
            reference IDs for use in subsequent interactions.

            Returns:
                A formatted summary and list of interactable elements
            """
            if not self.browser_agent:
                return "Browser agent not initialized. Please navigate to a webpage first."

            snapshot = await self.browser_agent.capture_page_snapshot(usage=ctx.usage)

            if snapshot.get("screenshot_path"):
                # Store screenshot path for the main agent to process
                self._pending_screenshot = snapshot["screenshot_path"]

            # Format the response
            response_parts = []

            if snapshot.get("page_summary"):
                response_parts.append(f"**Page Summary:** {snapshot['page_summary']}")

            if snapshot.get("interactable_elements"):
                response_parts.append("\n**Interactable Elements:**")
                for element in snapshot["interactable_elements"]:
                    response_parts.append(element)
            else:
                response_parts.append("\nNo interactable elements found on the page.")

            if snapshot.get("screenshot_path"):
                response_parts.append(f"\n**Screenshot saved to:** {snapshot['screenshot_path']}")

            return "\n".join(response_parts)

    async def __aenter__(self) -> "ConversationAgent":
        """Enter async context manager for MCP servers."""
        self.mcp_context = self.agent.run_mcp_servers()
        await self.mcp_context.__aenter__()

        # Initialize browser agent
        browser_model = get_model(BROWSER_MODEL_NAME)
        self.browser_agent = BrowserAgent(browser_model)
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
            console.log(Markdown("## pydantic mcp"))
            async for node in agent_run:
                console.log(Markdown("### pydantic mcp node"))
                logger.debug(
                    f"{node.__class__.__name__}: {black.format_str(str(node), mode=black.Mode())}"
                )

                print_node(node)

                # Pause and wait for user confirmation
                wait_for_input()

                # Check if we have a pending screenshot from browser agent
                if self._pending_screenshot:
                    yield {
                        "type": "image",
                        "node_type": "BrowserScreenshot",
                        "filename": self._pending_screenshot,
                    }
                    self._pending_screenshot = None

            if agent_run.result is not None:
                # Store conversation history
                self.message_history = agent_run.result.all_messages()
                yield {
                    "type": "text",
                    "text": agent_run.result.output,  # type: ignore
                }

    def get_messages(self) -> List[ModelMessage]:
        """Get the complete conversation history."""
        return self.message_history.copy()


async def main():
    """Simple usage example demonstrating the ConversationAgent."""
    console.log(Markdown("# Starting ConversationAgent example"))

    # Create a conversation agent
    async with ConversationAgent() as agent:
        # Example 2: Taking a screenshot
        console.log(Markdown("## Example 2: Taking a screenshot"))
        async for chunk in agent.run_query("Open the Canada Life website"):
            console.log(chunk)


if __name__ == "__main__":
    asyncio.run(main())
