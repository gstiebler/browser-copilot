import os
from typing import List, Any, Optional
from pydantic_ai import Agent, RunContext
from pydantic_ai.mcp import MCPServerStdio
from pydantic_ai.messages import ModelMessage
import logfire

from src.input_utils import wait_for_input
from .log_config import setup_logging, log_markdown
import black
from .browser_interaction_agent import BrowserInteractionAgent
from .page_analysis_agent import PageAnalysisAgent
from .model_config import get_model
from .node_utils import print_node
from .base_agent import BaseAgent
from .telegram_message_sender import TelegramMessageSender


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
After each iteration, reflect if there's something useful that you should store in the memory server.
Examples of useful information to store include:
- Important URLs or web pages
- User preferences
- User information that can be useful in future interactions
- Processes that have a chance to be repeated in the future

IMPORTANT: When you have a response for the user, you MUST use the send_telegram_message tool to send it.
Do not include the response in your output - instead, send it via the telegram tool.
"""


class ConversationAgent(BaseAgent):
    """A conversational agent that maintains message history across interactions."""

    def __init__(self, message_sender: TelegramMessageSender) -> None:
        """Initialize the agent with model and MCP server configuration."""
        super().__init__(message_sender)

        # Create single instances of each MCP server
        self.calculator_server = MCPServerStdio("uvx", args=["mcp-server-calculator"])
        self.pdf_server = MCPServerStdio(
            "uvx",
            args=[
                "--from",
                "git+https://github.com/gstiebler/pdf-mcp-server.git",
                "pdf-mcp-server",
            ],
        )
        self.memory_server = MCPServerStdio(
            "uvx",
            args=[
                "--from",
                "git+https://github.com/gstiebler/h-memory-mcp-server.git",
                "h-memory-mcp-server",
                "--memory-file",
                "memory.json",
            ],
        )
        self.filesystem_server = MCPServerStdio(
            "npx",
            args=["@modelcontextprotocol/server-filesystem", TEMP_FOLDER],
        )
        self.playwright_server = MCPServerStdio(
            "npx",
            args=[
                "@playwright/mcp@latest",
                "--output-dir",
                TEMP_FOLDER,
                "--image-responses",
                "omit",
            ],
        )

        # Collect all servers for the main agent
        mcp_servers = [
            self.calculator_server,
            self.pdf_server,
            self.memory_server,
            self.filesystem_server,
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

        # Set up telegram tools from base class
        self._setup_telegram_tools()

        # Store conversation history
        self.message_history: List[ModelMessage] = []
        self.mcp_context: Optional[Any] = None

        # Initialize browser agents
        self.browser_interaction_agent: Optional[BrowserInteractionAgent] = None
        self.page_analysis_agent: Optional[PageAnalysisAgent] = None

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
            if not self.browser_interaction_agent:
                return "Browser interaction agent not initialized. Please try again."

            # Execute browser task - it will send messages directly
            result = await self.browser_interaction_agent.execute_browser_task(
                task, usage=ctx.usage
            )

            # Return the result directly
            return result

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
            if not self.page_analysis_agent:
                return "Page analysis agent not initialized. Please navigate to a webpage first."

            snapshot = await self.page_analysis_agent.capture_page_snapshot(usage=ctx.usage)

            # Note: The agent will send the screenshot via the telegram tool if needed
            # We'll include the path in the response for the agent to handle

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
        if not self.agent:
            raise ValueError("Agent not initialized")
        self.mcp_context = self.agent.run_mcp_servers()
        await self.mcp_context.__aenter__()

        # Initialize browser agents
        browser_model = get_model(BROWSER_MODEL_NAME)

        # Browser interaction agent gets both Playwright and Memory servers
        interaction_mcp_servers = [self.playwright_server, self.memory_server]
        self.browser_interaction_agent = BrowserInteractionAgent(
            self.message_sender, browser_model, interaction_mcp_servers
        )

        # Page analysis agent only gets Playwright server
        analysis_mcp_servers = [self.playwright_server]
        self.page_analysis_agent = PageAnalysisAgent(
            self.message_sender, browser_model, analysis_mcp_servers, self.playwright_server
        )

        # Start MCP servers for interaction agent (which will start both Playwright and Memory)
        if self.browser_interaction_agent and self.browser_interaction_agent.agent:
            self.browser_interaction_context = (
                self.browser_interaction_agent.agent.run_mcp_servers()
            )
            await self.browser_interaction_context.__aenter__()

        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit async context manager for MCP servers."""
        if hasattr(self, "browser_interaction_context") and self.browser_interaction_context:
            await self.browser_interaction_context.__aexit__(exc_type, exc_val, exc_tb)
        if self.mcp_context:
            await self.mcp_context.__aexit__(exc_type, exc_val, exc_tb)

    async def run_query(self, query: str) -> None:
        """
        Run a query and store the messages in history.

        Args:
            query: The user's query
        """
        # Run the query with existing message history
        if not self.agent:
            logger.error("Agent not initialized")
            return

        async with self.agent.iter(query, message_history=self.message_history) as agent_run:
            log_markdown("# pydantic mcp")
            async for node in agent_run:
                log_markdown("## pydantic mcp node")
                logger.debug(
                    f"{node.__class__.__name__}: {black.format_str(str(node), mode=black.Mode())}"
                )

                print_node(node, 3)

                # Pause and wait for user confirmation
                wait_for_input()

            if agent_run.result is not None:
                # Store conversation history
                self.message_history = agent_run.result.all_messages()

                # The agent should have already sent messages via the telegram tools
                # Log the output for debugging
                if agent_run.result.output:
                    logger.debug(f"Agent output: {agent_run.result.output}")

    def get_messages(self) -> List[ModelMessage]:
        """Get the complete conversation history."""
        return self.message_history.copy()
