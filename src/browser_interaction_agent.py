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

IMPORTANT: When given a goal, you must execute ONE STEP at a time:
1. Determine what the logical first/next step should be
2. Execute only that single step
3. Clearly indicate when the step is completed
4. Return a concise summary of what was accomplished in this step

For example, if the goal is "determine who was the FIFA World Champion in 1958":
- First step might be: Search Google for "FIFA official website"
- After finding it's www.fifa.com, return: "Found the FIFA website: www.fifa.com"
- Do NOT continue to the next step (visiting the website)

Always be clear about:
- What step you're executing
- What the result of that step is
- That you've completed this single step

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

    async def execute_goal_step(self, goal: str, usage: Any = None) -> AsyncGenerator[dict, None]:
        """
        Execute a single step towards completing a goal using the browser.

        This method determines what constitutes the first step of the goal
        and executes it. The agent will decide when the step is completed
        and return the result.

        Args:
            goal: The overall goal to be achieved
            usage: Usage tracking from parent agent

        Yields:
            Dictionaries containing response chunks with step results
        """
        step_prompt = f"""Goal: {goal}

Execute the next appropriate step towards completing this goal."""

        async with self.agent.iter(step_prompt, usage=usage) as agent_run:
            log_markdown("## BrowserInteractionAgent - execute_goal_step")
            log_markdown(f"### Goal: {goal}")

            async for node in agent_run:
                log_markdown("### Browser interaction node")
                print_node(node, 4)

                # Pause and wait for user confirmation
                wait_for_input()
                logger.debug(
                    f"{node.__class__.__name__}: {black.format_str(str(node), mode=black.Mode())}"
                )

            result = agent_run.result.output if agent_run.result else "No result"

            yield {
                "type": "text",
                "text": result,
                "step_completed": True,
            }

    async def execute_browser_task(
        self, task: str, usage: Any = None
    ) -> AsyncGenerator[dict, None]:
        """
        Execute a browser automation task and yield results.

        This method is kept for backward compatibility but delegates
        to execute_goal_step for consistency.

        Args:
            task: The browser task to execute
            usage: Usage tracking from parent agent

        Yields:
            Dictionaries containing response chunks
        """
        # Delegate to the new method for consistency
        async for chunk in self.execute_goal_step(task, usage):
            yield chunk
