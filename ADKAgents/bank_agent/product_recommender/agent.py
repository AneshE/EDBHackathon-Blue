"""Product Recommender sub-agent definition.

Registered as a sub-agent of the root ``bank_agent`` so the parent LLM
can delegate product recommendation queries to it.
"""

from google.adk.agents import Agent

from .prompt import PRODUCT_RECOMMENDER_INSTRUCTION
from ..shared_tools.spending_analysis_tools import analyse_spending
from ..tools.productsearch import vertex_vector_search

product_recommender_agent = Agent(
    name="product_recommender",
    model="gemini-2.5-flash",
    description=(
        "Analyzes a customer's spending habits and searches for relevant bank "
        "products or perks to recommend a concrete reallocation path to hit "
        "a 20% savings/investment target. It generates specific short-term "
        "and long-term financial projections."
    ),
    instruction=PRODUCT_RECOMMENDER_INSTRUCTION,
    tools=[analyse_spending, vertex_vector_search],
)
