from google.adk.agents.llm_agent import Agent
from google.adk.models.lite_llm import LiteLlm

root_agent = Agent(
    name="HelloWorldAgent",
    model=LiteLlm(model="anthropic/claude-sonnet-4-5-20250929"),
    description="Hello World agent powered by Claude via Google ADK",
    instruction="You are a friendly assistant. Respond warmly and briefly.",
    tools=[],
)
