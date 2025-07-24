import json
import os
from typing import List, Any, Optional, AsyncGenerator, Dict
from pydantic_ai import Agent, CallToolsNode, ModelRequestNode, UserPromptNode
from pydantic_ai.mcp import MCPServerStdio
from pydantic_ai.messages import (
    ToolCallPart,
    TextPart,
    ToolReturnPart,
)
from log_config import setup_logging
from colorama import Fore, Style
import black


TEMP_FOLDER = os.getenv("TEMPDIR", "/tmp")

logger = setup_logging(__name__)


class BrowserAgent:
    """An agent specifically for browser automation using Playwright MCP server."""

    def __init__(self, model):
        """Initialize the browser agent with Playwright MCP server configuration."""
        self.model = model

        # Initialize the Playwright and Memory MCP servers
        mcp_servers = [
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
                    "git+https://github.com/gstiebler/h-memory-mcp-server.git",
                    "h-memory-mcp-server",
                    "--memory-file",
                    "memory.json",
                ],
            ),
        ]

        # Initialize the agent with browser-specific system prompt
        self.agent = Agent(
            self.model,
            mcp_servers=mcp_servers,
            system_prompt="""You are a browser automation agent that interacts with web browsers on behalf of users.
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
""",
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
        Execute a browser task and yield results including screenshots.

        Args:
            task: The browser task to execute
            usage: Usage tracking from parent agent
            message_history: Previous message history to include

        Yields:
            Dictionaries containing response chunks and screenshot info
        """
        async with self.agent.iter(task, usage=usage) as agent_run:
            nodes_so_far = []

            async for node in agent_run:
                nodes_so_far.append(node)

                # Log node processing
                color_by_node: dict[type, str] = {
                    CallToolsNode: Fore.GREEN,
                    ModelRequestNode: Fore.BLUE,
                    UserPromptNode: Fore.YELLOW,
                }
                color = color_by_node.get(type(node), Fore.RED)
                logger.debug(
                    f"BrowserAgent processing node: {color}{black.format_str(repr(node), mode=black.Mode())}{Style.RESET_ALL}"
                )

                # Yield text responses
                if isinstance(node, CallToolsNode):
                    for part in node.model_response.parts:
                        if isinstance(part, TextPart):
                            yield {
                                "type": "text",
                                "text": part.content,
                            }

                # Check for screenshots
                screenshot_result = self._process_screenshot_nodes(nodes_so_far)
                if screenshot_result:
                    yield screenshot_result

    def _process_screenshot_nodes(self, nodes: List[Any]) -> Optional[dict]:
        """
        Process nodes to find browser screenshot results.

        Args:
            nodes: List of nodes to process

        Returns:
            Dictionary with screenshot info if found, None otherwise
        """
        for i in range(1, len(nodes)):
            previous_node = nodes[i - 1]
            current_node = nodes[i]

            if not isinstance(current_node, ModelRequestNode):
                continue

            previous_node_parts = (
                previous_node.model_response.parts
                if hasattr(previous_node, "model_response")
                else []
            )
            previous_node_tool_call_part = next(
                (part for part in previous_node_parts if isinstance(part, ToolCallPart)),
                None,
            )

            for part in current_node.request.parts:
                if (
                    isinstance(part, ToolReturnPart)
                    and previous_node_tool_call_part
                    and part.tool_name
                    == previous_node_tool_call_part.tool_name
                    == "browser_take_screenshot"
                ):
                    if isinstance(previous_node_tool_call_part.args, str):
                        parsed_args = json.loads(previous_node_tool_call_part.args)
                    elif isinstance(previous_node_tool_call_part.args, dict):
                        parsed_args = previous_node_tool_call_part.args
                    else:
                        parsed_args = {}

                    return {
                        "type": "image",
                        "filename": f"{TEMP_FOLDER}/{parsed_args.get('filename', 'screenshot.png')}",
                    }

        return None

    async def capture_page_snapshot(self, usage: Any = None) -> Dict[str, Any]:
        """
        Capture a snapshot of the current web page and analyze it to extract interactable elements.

        Returns:
            Dictionary containing:
            - page_summary: Brief description of the page
            - interactable_elements: List of all clickable/fillable elements with their details
            - screenshot_path: Path to the screenshot if taken
        """
        snapshot_prompt = """Please:
1. Take a screenshot of the current page
2. Use browser_snapshot to get the accessibility tree
3. Analyze the snapshot and provide:
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

        result: Dict[str, Any] = {
            "page_summary": "",
            "interactable_elements": [],
            "screenshot_path": None,
        }

        async with self.agent.iter(snapshot_prompt, usage=usage) as agent_run:
            full_response = []
            nodes_collected = []

            async for node in agent_run:
                nodes_collected.append(node)

                # Collect text responses
                if isinstance(node, CallToolsNode):
                    for part in node.model_response.parts:
                        if isinstance(part, TextPart):
                            full_response.append(part.content)

                # Check for screenshot
                screenshot_info = self._process_screenshot_nodes(nodes_collected)
                if screenshot_info:
                    result["screenshot_path"] = screenshot_info["filename"]

            # Process the response to extract summary and elements
            full_text = "\n".join(full_response)

            # Extract summary
            if "SUMMARY:" in full_text:
                summary_start = full_text.find("SUMMARY:") + len("SUMMARY:")
                summary_end = full_text.find("\n", summary_start)
                if summary_end == -1:
                    summary_end = full_text.find("INTERACTABLE", summary_start)
                if summary_end != -1:
                    result["page_summary"] = full_text[summary_start:summary_end].strip()

            # Extract interactable elements
            if "INTERACTABLE ELEMENTS:" in full_text:
                elements_start = full_text.find("INTERACTABLE ELEMENTS:") + len(
                    "INTERACTABLE ELEMENTS:"
                )
                elements_text = full_text[elements_start:].strip()

                # Split by lines and filter element entries
                for line in elements_text.split("\n"):
                    line = line.strip()
                    if line and line.startswith("-"):
                        if isinstance(result["interactable_elements"], list):
                            result["interactable_elements"].append(line)

        return result
