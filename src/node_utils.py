"""Utilities for processing Pydantic AI nodes and displaying their content."""

import json
import black
from pydantic_ai import CallToolsNode, ModelRequestNode, UserPromptNode
from pydantic_ai.messages import (
    RetryPromptPart,
    TextPart,
    ToolReturnPart,
    ThinkingPart,
    ToolCallPart,
    UserPromptPart,
    SystemPromptPart,
)
from pydantic_graph import End
from .log_config import console, log_markdown


def print_node(node, indent: int) -> None:
    """Process different types of Pydantic AI nodes and display their content."""
    indent_str = "#" * indent
    try:
        if isinstance(node, ModelRequestNode):
            # Process model request nodes
            for part in node.request.parts:
                if isinstance(part, ToolReturnPart):
                    log_markdown(f"{indent_str} Tool Return Part: `{part.tool_name}`")

                    # Check if content is a dict and format it as JSON
                    if isinstance(part.content, dict):
                        formatted_json = json.dumps(part.content, indent=2)
                        log_markdown(f"```json\n{formatted_json}\n```")
                    else:
                        log_markdown(str(part.content))
                elif isinstance(part, UserPromptPart):
                    log_markdown(f"{indent_str} User Prompt Part")
                    log_markdown(str(part.content))
                elif isinstance(part, SystemPromptPart):
                    log_markdown(f"{indent_str} System Prompt Part")
                    log_markdown(part.content)
                elif isinstance(part, RetryPromptPart):
                    log_markdown(f"{indent_str} Retry Prompt Part")
                    if isinstance(part.content, str):
                        log_markdown(part.content)
                    else:
                        for error_detail in part.content:
                            log_markdown(f"{indent_str} Error Detail: {error_detail}")
                else:
                    raise ValueError(f"Unknown part type: {type(part)} in ModelRequestNode")
        elif isinstance(node, CallToolsNode):
            # Handle tool calls
            for tool_part in node.model_response.parts:
                if isinstance(tool_part, ThinkingPart):
                    log_markdown(f"{indent_str} Thinking Part")
                    log_markdown(tool_part.content)
                elif isinstance(tool_part, ToolCallPart):
                    log_markdown(f"{indent_str} Tool Call Part: `{tool_part.tool_name}`")
                    log_markdown(f"Arguments: \n```json\n{tool_part.args}\n```")
                elif isinstance(tool_part, TextPart):
                    log_markdown(f"{indent_str} Text Part")
                    log_markdown(tool_part.content)
                else:
                    raise ValueError(f"Unknown part type: {type(tool_part)} in CallToolsNode")
        elif isinstance(node, End):
            # End of the agent run
            log_markdown(f"{indent_str} End of Agent Run")
        elif isinstance(node, UserPromptNode):
            # User prompt node
            log_markdown(f"{indent_str} User Prompt Node")
            log_markdown(str(node.user_prompt))
            log_markdown(f"{indent_str} System prompts:")
            for prompt in node.system_prompts:
                log_markdown(prompt)
        else:
            # Unknown node type - print it directly
            log_markdown(f"### Unknown Node Type: {type(node).__name__}")
            console.print(
                f"{node.__class__.__name__}: {black.format_str(str(node), mode=black.Mode())}"
            )
    except Exception as e:
        log_markdown(f"Error processing node: {e}")
        console.print(
            f"{node.__class__.__name__}: {black.format_str(str(node), mode=black.Mode())}"
        )
        raise e
