import asyncio
import os
from typing import List, AsyncGenerator, Optional, Any
import black
from pydantic_ai import Agent
from pydantic_ai.mcp import MCPServerStdio
from pydantic_ai.messages import ModelMessage
from rich.console import Console
from ..model_config import get_model
from ..log_config import setup_logging
import logfire


LOGFIRE_TOKEN = os.getenv("LOGFIRE_TOKEN", "")
logfire.configure(token=LOGFIRE_TOKEN, scrubbing=False)  # type: ignore
logfire.instrument_pydantic_ai()

# Initialize rich console for colored output
console = Console()

# Set up logging
logger = setup_logging(__name__)

TEMP_FOLDER = os.getenv("TEMPDIR", "/tmp")
MAIN_MODEL_NAME = os.getenv("MAIN_MODEL", "")

system_prompt = """
You are a browser automation assistant that helps a developer interact with web browsers,
and troubleshoot issues with Playwright MCP server.
Always execute one command at a time and wait for the user feedback before proceeding withe the next command.
"""


class ConsoleAgent:
    """A simple console-based agent with Playwright MCP server."""

    def __init__(self) -> None:
        """Initialize the agent with Playwright MCP server configuration."""
        # Configure Playwright MCP server
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
            )
        ]

        # Initialize the model
        self.model = get_model(MAIN_MODEL_NAME)

        # Initialize the agent
        self.agent = Agent(
            self.model,
            mcp_servers=mcp_servers,
            system_prompt=system_prompt,
            name="ConsoleAgent",
        )
        # Store conversation history
        self.message_history: List[ModelMessage] = []
        self.mcp_context: Optional[Any] = None

    async def __aenter__(self) -> "ConsoleAgent":
        """Enter async context manager for MCP servers."""
        self.mcp_context = self.agent.run_mcp_servers()
        if self.mcp_context:
            await self.mcp_context.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit async context manager for MCP servers."""
        if self.mcp_context:
            await self.mcp_context.__aexit__(exc_type, exc_val, exc_tb)

    def clear_history(self) -> None:
        """Clear the conversation history."""
        self.message_history = []
        console.print("Conversation history cleared.", style="yellow")

    async def run_query(self, query: str) -> AsyncGenerator[str, None]:
        """
        Run a query and yield streaming responses.

        Args:
            query: The user's query

        Yields:
            Response text chunks
        """
        try:
            async with self.agent.iter(query, message_history=self.message_history) as agent_run:
                async for node in agent_run:
                    # Extract text from the node if available
                    formatted_str = black.format_str(repr(node), mode=black.Mode())
                    # Replace \n with actual newlines
                    formatted_str = formatted_str.replace("\\n", "\n")
                    console.print(formatted_str, style="green")

                # Update conversation history
                if agent_run.result is not None:
                    self.message_history = agent_run.result.all_messages()

        except Exception as e:
            logger.error(f"Error running query: {e}")
            yield f"Error: {str(e)}"


async def main():
    """Main console interaction loop."""
    console.print("Browser Automation Console Chat", style="cyan")
    console.print("=" * 40, style="cyan")
    console.print("Type [green]/exit[/green] to quit")
    console.print("Type [green]/clear[/green] to clear conversation history")
    print()

    async with ConsoleAgent() as agent:
        while True:
            try:
                # Get user input
                user_input = console.input("[blue]> [/blue]")

                # Handle commands
                if user_input.lower() in ["/exit", "/quit"]:
                    console.print("Goodbye!", style="yellow")
                    break
                elif user_input.lower() == "/clear":
                    agent.clear_history()
                    continue
                elif not user_input.strip():
                    continue

                # Process the query
                console.print("Assistant: ", style="green", end="")

                response_parts = []
                async for chunk in agent.run_query(user_input):
                    print(chunk, end="", flush=True)
                    response_parts.append(chunk)

                print()  # New line after response
                print()  # Extra line for spacing

            except KeyboardInterrupt:
                console.print("\nInterrupted. Type /exit to quit.", style="yellow")
                continue
            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                console.print(f"Error: {str(e)}", style="red")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        console.print("\nGoodbye!", style="yellow")
