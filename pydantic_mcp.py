import asyncio
import os
from pydantic_ai import Agent
from pydantic_ai.mcp import MCPServerStdio
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openrouter import OpenRouterProvider
from dotenv import load_dotenv

load_dotenv()

server = MCPServerStdio("uvx", args=["mcp-server-calculator"])

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

model = OpenAIModel(
    "anthropic/claude-sonnet-4",
    provider=OpenRouterProvider(api_key=OPENROUTER_API_KEY),
)
agent = Agent(model, mcp_servers=[server])


async def main():
    async with agent.run_mcp_servers():
        result = await agent.run("How many days between 2000-01-01 and 2025-03-18?")
    print(result.output)
    # > There are 9,208 days between January 1, 2000, and March 18, 2025.


if __name__ == "__main__":
    asyncio.run(main())
