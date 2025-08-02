import os
from typing import Any, AsyncGenerator, Dict
import black
from pydantic_ai import Agent
from pydantic_ai.mcp import MCPServerStdio

from .input_utils import wait_for_input
from .log_config import setup_logging, log_markdown
from .node_utils import print_node


TEMP_FOLDER = os.getenv("TEMPDIR", "/tmp")

logger = setup_logging(__name__)


system_prompt = """You are a browser automation agent that interacts with web browsers on behalf of users.
You can:
- Navigate to websites
- Take screenshots
- Click on elements
- Fill forms
- Extract information from web pages
- Perform various browser automation tasks
- Store and retrieve persistent information using memory tools

You have access to Playwright browser automation tools and memory storage. 
When taking screenshots, always specify a meaningful filename that describes what's being captured.
You can use memory tools to save important information from browsing sessions for future reference.
Add any learnings you had while interacting with Playwright to the memory server.
`browser_click` doesn't work. Use browser_evaluate to click on elements instead, using the parameters as follows (example):
```json
{
    'ref': 'e1234',
    'element': 'name of the element to click on',
    'function': '(element) => { element.click(); }',
},
```
"""


class BrowserAgent:
    """An agent specifically for browser automation using Playwright MCP server."""

    def __init__(self, model):
        """Initialize the browser agent with Playwright MCP server configuration."""
        self.model = model

        # Initialize the Playwright and Memory MCP servers
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

        memory_server = MCPServerStdio(
            "uvx",
            args=[
                "--from",
                "git+https://github.com/gstiebler/h-memory-mcp-server.git",
                "h-memory-mcp-server",
                "--memory-file",
                "memory.json",
            ],
        )

        mcp_servers = [self.playwright_server, memory_server]

        # Initialize the agent with browser-specific system prompt
        self.agent = Agent(
            self.model,
            mcp_servers=mcp_servers,
            system_prompt=system_prompt,
            name="BrowserAgent",
        )

        self.mcp_context = None

    async def __aenter__(self) -> "BrowserAgent":
        """Enter async context manager for MCP servers."""
        self.mcp_context = self.agent.run_mcp_servers()
        await self.mcp_context.__aenter__()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit async context manager for MCP servers."""
        if self.mcp_context:
            await self.mcp_context.__aexit__(exc_type, exc_val, exc_tb)

    async def execute_browser_task(
        self, task: str, usage: Any = None
    ) -> AsyncGenerator[dict, None]:
        """
        Execute a browser task and yield results.

        Args:
            task: The browser task to execute
            usage: Usage tracking from parent agent
            message_history: Previous message history to include

        Yields:
            Dictionaries containing response chunks and screenshot info
        """
        async with self.agent.iter(task, usage=usage) as agent_run:
            log_markdown("## execute_browser_task")
            async for node in agent_run:
                log_markdown("### execute_browser_task node")
                print_node(node, 4)

                # Pause and wait for user confirmation
                wait_for_input()
                logger.debug(
                    f"{node.__class__.__name__}: {black.format_str(str(node), mode=black.Mode())}"
                )

            yield {
                "type": "text",
                "text": agent_run.result.output,  # type: ignore
            }

    async def capture_page_snapshot(self, usage: Any = None) -> Dict[str, Any]:
        """
        Capture a snapshot of the current web page and analyze it to extract interactable elements.

        Returns:
            Dictionary containing:
            - page_summary: Brief description of the page, and a list of all clickable/fillable elements with their details
            - screenshot_path: Path to the screenshot if taken
        """
        from datetime import datetime

        result: Dict[str, Any] = {
            "page_summary": "",
            "screenshot_path": None,
        }

        # First, ALWAYS capture a screenshot directly via MCP
        try:
            if self.mcp_context:
                # Generate filename with current datetime
                timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
                screenshot_filename = f"page-snapshot-{timestamp}.png"

                # Call the screenshot tool directly using the Playwright server property
                screenshot_result = await self.playwright_server.call_tool(
                    "browser_take_screenshot", {"filename": screenshot_filename}
                )
                logger.debug(f"Screenshot taken: {screenshot_result}")

                # Set the screenshot path
                screenshot_path = f"{TEMP_FOLDER}/{screenshot_filename}"
                result["screenshot_path"] = screenshot_path

                # Log the screenshot in markdown
                log_markdown(f"![Screenshot]({screenshot_filename})")

        except Exception as e:
            logger.warning(f"Failed to capture screenshot directly: {e}")

        # Now get the accessibility snapshot and analyze it
        snapshot_prompt = """Please:
1. Use browser_snapshot to get the accessibility tree
2. Analyze the snapshot and provide:
   - A brief summary of what the page contains
   - A comprehensive list of ALL interactable elements (buttons, links, inputs, dropdowns, etc.)
   
For each interactable element, include:
- Element type (button, link, input, select, etc.)
- Text/label of the element
- Element reference ID (for interaction)
- Any additional relevant attributes (placeholder text, current value, etc.)

Format the response as:
SUMMARY: [brief page description]

INTERACTABLE ELEMENTS:
- [element details]
- [element details]
etc."""

        async with self.agent.iter(snapshot_prompt, usage=usage) as agent_run:
            log_markdown("### capture_page_snapshot")
            async for node in agent_run:
                print_node(node, 4)

                wait_for_input()
                logger.debug(
                    f"{node.__class__.__name__}: {black.format_str(str(node), mode=black.Mode())}"
                )

            if not agent_run.result:
                raise ValueError("No result from agent run")
            result["page_summary"] = agent_run.result.output
        return result
