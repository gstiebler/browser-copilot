"""Utilities for processing Pydantic AI nodes and displaying their content."""

import json
import black
from pydantic_ai import CallToolsNode, ModelRequestNode
from pydantic_ai.messages import (
    ToolReturnPart,
    ThinkingPart,
    ToolCallPart,
    UserPromptPart,
    SystemPromptPart,
)
from pydantic_graph import End
from .log_config import console, log_markdown


def print_node(node):
    """Process different types of Pydantic AI nodes and display their content."""
    try:
        if isinstance(node, ModelRequestNode):
            # Process model request nodes
            for part in node.request.parts:
                if isinstance(part, ToolReturnPart):
                    log_markdown("### Tool Return Part")
                    log_markdown(f"Tool call: `{part.tool_name}`")

                    # Check if content is a dict and format it as JSON
                    if isinstance(part.content, dict):
                        formatted_json = json.dumps(part.content, indent=2)
                        log_markdown(f"```json\n{formatted_json}\n```")
                    else:
                        log_markdown(str(part.content))
                elif isinstance(part, UserPromptPart):
                    log_markdown("### User Prompt Part")
                    log_markdown(part.content)  # type: ignore
                elif isinstance(part, SystemPromptPart):
                    log_markdown("### System Prompt Part")
                    log_markdown(part.content)
        elif isinstance(node, CallToolsNode):
            # Handle tool calls
            for part in node.model_response.parts:
                if isinstance(part, ThinkingPart):
                    log_markdown("### Thinking Part")
                    log_markdown(part.content)
                elif isinstance(part, ToolCallPart):
                    log_markdown("### Tool Call Part")
                    log_markdown(f"`Tool call: `{part.tool_name}`")
                    log_markdown(f"Arguments: ```json \n{part.args}\n```")
        elif isinstance(node, End):
            # End of the agent run
            log_markdown("### End of Agent Run")
    except Exception as e:
        log_markdown(f"Error processing node: {e}")
        console.print(
            f"{node.__class__.__name__}: {black.format_str(str(node), mode=black.Mode())}"
        )
        raise e
