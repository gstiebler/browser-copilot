import os
from typing import Any, Dict
from datetime import datetime
import black
from pydantic_ai import Agent
from pydantic_ai.mcp import MCPServerStdio

from .input_utils import wait_for_input
from .log_config import setup_logging, log_markdown
from .node_utils import print_node


TEMP_FOLDER = os.getenv("TEMPDIR", "/tmp")
logger = setup_logging(__name__)


system_prompt = """You are a web page analysis expert that specializes in capturing and analyzing web page content.
Your primary focus is on:
- Taking comprehensive screenshots of web pages
- Analyzing page structure and layout
- Identifying all interactable elements (buttons, links, forms, inputs, dropdowns, etc.)
- Providing detailed summaries of page content
- Extracting element references for future interactions

When analyzing pages, you should:
1. First capture a screenshot to document the visual state
2. Use the browser_snapshot tool to get the accessibility tree
3. Analyze the snapshot to identify ALL interactable elements
4. Provide a clear, structured summary of what the page contains

For each interactable element you find, include:
- Element type (button, link, input, select, textarea, etc.)
- Element text or label
- Element reference ID (for future interactions)
- Any relevant attributes (placeholder text, current value, disabled state, etc.)

Your analysis should be thorough and systematic, ensuring no important elements are missed.
Format your responses clearly with proper sections for the summary and element listings."""


class PageAnalysisAgent:
    """An agent specifically for web page analysis and screenshot capture."""

    def __init__(self, model, mcp_servers, playwright_server: MCPServerStdio):
        """Initialize the page analysis agent.

        Args:
            model: The AI model to use
            mcp_servers: List of MCP servers
            playwright_server: The Playwright MCP server instance for direct screenshot calls
        """
        self.model = model
        self.playwright_server = playwright_server

        # Initialize the agent with page analysis system prompt
        self.agent = Agent(
            self.model,
            mcp_servers=mcp_servers,
            system_prompt=system_prompt,
            name="PageAnalysisAgent",
        )

    async def capture_page_snapshot(self, usage: Any = None) -> Dict[str, Any]:
        """
        Capture a snapshot of the current web page and analyze it to extract interactable elements.

        Returns:
            Dictionary containing:
            - page_summary: Brief description of the page, and a list of all clickable/fillable elements with their details
            - screenshot_path: Path to the screenshot if taken
        """
        result: Dict[str, Any] = {
            "page_summary": "",
            "screenshot_path": None,
        }

        # First, ALWAYS capture a screenshot directly via MCP
        try:
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
            log_markdown("### PageAnalysisAgent - capture_page_snapshot")
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
