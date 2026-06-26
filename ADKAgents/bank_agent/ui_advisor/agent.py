"""UI Advisor sub-agent definition.

Registered as a sub-agent of the root ``bank_agent`` so the parent LLM
can delegate UI-data requests to it. Returns structured JSON for the
Streamlit 4-step wizard frontend.
"""

from google.adk.agents import Agent

from .prompt import UI_ADVISOR_INSTRUCTION
from ..shared_tools.spending_analysis_tools import analyse_spending
from ..tools.productsearch import vertex_vector_search

ui_advisor_agent = Agent(
    name="ui_advisor",
    model="gemini-2.5-flash",
    description=(
        "Analyses a customer's spending and returns structured JSON data "
        "for the 4-step financial advisor UI. Produces budget blueprint, "
        "perk optimization suggestions, and wealth growth projections in "
        "a machine-readable format instead of chat prose."
    ),
    instruction=UI_ADVISOR_INSTRUCTION,
    tools=[analyse_spending, vertex_vector_search],
)
