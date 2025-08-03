from typing import Any, AsyncGenerator
import black
from pydantic_ai import Agent

from .input_utils import wait_for_input
from .log_config import setup_logging, log_markdown
from .node_utils import print_node


logger = setup_logging(__name__)


system_prompt = """You are a browser automation specialist that interacts with web browsers on behalf of users.
Your primary focus is on executing browser automation tasks such as:
- Navigating to websites and URLs
- Clicking on buttons, links, and other interactive elements
- Filling out forms and input fields
- Submitting forms and handling form interactions
- Extracting specific information from web pages
- Performing complex multi-step browser automation workflows

When interacting with page elements, you have access to the Playwright browser automation tools.

Important notes for clicking elements:
- The `browser_click` tool may not work reliably
- Use `browser_evaluate` to click on elements instead, with parameters like:
  ```json
  {
      'ref': 'element_reference_id',
      'element': 'description of the element to click',
      'function': '(element) => { element.click(); }'
  }
  ```

Always be precise and methodical in your browser interactions. When performing multi-step tasks,
complete each step before moving to the next. Provide clear feedback about what actions you're taking."""


class BrowserInteractionAgent:
    """An agent specifically for browser interaction and automation tasks."""

    def __init__(self, model, mcp_servers):
        """Initialize the browser interaction agent.

        Args:
            model: The AI model to use
            mcp_servers: List of MCP servers (typically Playwright and Memory servers)
        """
        self.model = model

        # Initialize the agent with browser interaction system prompt
        self.agent = Agent(
            self.model,
            mcp_servers=mcp_servers,
            system_prompt=system_prompt,
            name="BrowserInteractionAgent",
        )

    async def execute_browser_task(
        self, task: str, usage: Any = None
    ) -> AsyncGenerator[dict, None]:
        """
        Execute a browser automation task and yield results.

        Args:
            task: The browser task to execute
            usage: Usage tracking from parent agent

        Yields:
            Dictionaries containing response chunks
        """
        async with self.agent.iter(task, usage=usage) as agent_run:
            log_markdown("## BrowserInteractionAgent - execute_browser_task")
            async for node in agent_run:
                log_markdown("### Browser interaction node")
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
