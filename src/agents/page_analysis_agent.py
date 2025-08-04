import os
from typing import Any, Dict
from datetime import datetime
import black
from pydantic_ai import Agent
from pydantic_ai.mcp import MCPServerStdio

from ..input_utils import wait_for_input
from ..log_config import setup_logging, log_markdown
from ..node_utils import print_node
from .base_agent import BaseAgent
from ..telegram_message_sender import TelegramMessageSender


TEMP_FOLDER = os.getenv("TEMPDIR", "/tmp")
logger = setup_logging(__name__)


system_prompt = """You are a web page analysis expert that specializes in capturing and analyzing web page content.
Your primary focus is on:
- Analyzing page structure and layout
- Identifying interactable elements relevant to the current goal
- Providing detailed summaries of page content
- Extracting element references for future interactions

When analyzing pages, you should:
1. Use the browser_snapshot tool to get the accessibility tree
2. Analyze the snapshot to identify interactable elements RELEVANT TO THE CURRENT GOAL
3. Provide a clear, structured summary of what the page contains

IMPORTANT: You will be provided with a summary of the current goal. You should:
- Focus on elements that are relevant to achieving this goal
- Prioritize elements that would help accomplish the task at hand
- You may omit elements that are clearly unrelated to the goal (e.g., footer links when filling a form)
- However, include navigation elements if they might be needed to reach the goal

For each relevant interactable element you find, include:
- Element type (button, link, input, select, textarea, etc.)
- Element text or label
- Any relevant attributes (placeholder text, current value, disabled state, etc.)

If there are relevant hierarchical relationships between elements (e.g., form fields grouped under a form, dropdown options under a select, buttons in a toolbar), include this hierarchy information to help the caller understand the structure.

DO NOT include element reference IDs in your output.

Your analysis should be focused and goal-oriented, ensuring important elements for the task are not missed.

Format your responses as:
SUMMARY: [brief page description]

RELEVANT INTERACTABLE ELEMENTS:
- [element details]
- [element details]
etc.

IMPORTANT: If you capture a screenshot, use the send_telegram_image tool to send it to the user.
Use the send_telegram_message tool to send your analysis to the user.
Do not include the analysis in your output - instead, send it via the telegram tools.
"""


class PageAnalysisAgent(BaseAgent):
    """An agent specifically for web page analysis and screenshot capture."""

    def __init__(
        self,
        message_sender: TelegramMessageSender,
        model,
        mcp_servers,
        playwright_server: MCPServerStdio,
    ):
        """Initialize the page analysis agent.

        Args:
            message_sender: The TelegramMessageSender instance
            model: The AI model to use
            mcp_servers: List of MCP servers
            playwright_server: The Playwright MCP server instance for direct screenshot calls
        """
        super().__init__(message_sender)
        self.model = model
        self.playwright_server = playwright_server

        # Initialize the agent with page analysis system prompt
        self.agent = Agent(
            self.model,
            mcp_servers=mcp_servers,
            system_prompt=system_prompt,
            name="PageAnalysisAgent",
        )

        # Set up telegram tools from base class
        self._setup_telegram_tools()

    async def capture_page_snapshot(
        self, goal_summary: str = "", usage: Any = None
    ) -> Dict[str, Any]:
        """
        Capture a snapshot of the current web page and analyze it to extract interactable elements
        relevant to the current goal.

        Args:
            goal_summary: Summary of the current goal/task being performed
            usage: Usage tracking object

        Returns:
            Dictionary containing:
            - page_summary: Brief description of the page, and a list of goal-relevant clickable/fillable elements
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

            # Send the screenshot immediately
            await self.message_sender.send_image(screenshot_path)

        except Exception as e:
            logger.warning(f"Failed to capture screenshot directly: {e}")

        # Build the prompt with goal context
        goal_context = f"\n\nCURRENT GOAL: {goal_summary}" if goal_summary else ""

        # Now get the accessibility snapshot and analyze it
        snapshot_prompt = f"""Please: {goal_context}

1. Use browser_snapshot to get the accessibility tree
2. Analyze the snapshot and provide a summary of the page and list of goal-relevant interactable elements."""

        if not self.agent:
            logger.error("Agent not initialized")
            raise ValueError("Agent not initialized")

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
