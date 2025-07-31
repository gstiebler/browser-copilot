"""Utilities for processing Pydantic AI nodes and displaying their content."""

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
from rich.markdown import Markdown
from .log_config import console


def print_node(node):
    """Process different types of Pydantic AI nodes and display their content."""
    try:
        if isinstance(node, ModelRequestNode):
            # Process model request nodes
            for part in node.request.parts:
                if isinstance(part, ToolReturnPart):
                    console.log(Markdown("### Tool Return Part"))
                    console.log(Markdown(f"Tool call: {part.tool_name}"))

                    console.log(Markdown(part.content))
                elif isinstance(part, UserPromptPart):
                    console.log(Markdown("### User Prompt Part"))
                    console.log(Markdown(part.content))  # type: ignore
                elif isinstance(part, SystemPromptPart):
                    console.log(Markdown("### System Prompt Part"))
                    console.log(Markdown(part.content))
        elif isinstance(node, CallToolsNode):
            # Handle tool calls
            for part in node.model_response.parts:
                if isinstance(part, ThinkingPart):
                    console.log(Markdown("### Thinking Part"))
                    console.log(Markdown(part.content))
                elif isinstance(part, ToolCallPart):
                    console.log(Markdown("### Tool Call Part"))
                    console.log(Markdown(f"Tool call: {part.tool_name}"))
                    console.log(Markdown(f"Arguments: ```json {part.args}```"))
        elif isinstance(node, End):
            # End of the agent run
            console.log(Markdown("### End of Agent Run"))
    except Exception as e:
        console.log(Markdown(f"Error processing node: {e}"))
        console.print(
            f"{node.__class__.__name__}: {black.format_str(str(node), mode=black.Mode())}"
        )
        raise e
