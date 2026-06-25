"""Spending analyst sub-agent definition.

Registered as a sub-agent of the root ``bank_agent`` so the parent LLM
can delegate spending-related queries to it automatically.
"""

from google.adk.agents import Agent

from .prompt import SPENDING_ANALYST_INSTRUCTION
from ..shared_tools.transaction_tools import get_transactions
from ..shared_tools.spending_analysis_tools import analyse_spending

spending_analyst_agent = Agent(
    name="spending_analyst",
    model="gemini-2.5-flash",
    description=(
        "Analyses a customer's spending habits by fetching their transactions "
        "from BigQuery, categorising them (Groceries, Subscriptions, Travel, "
        "Rent, Tax, Interest, Incoming Salary, Others), and presenting "
        "breakdowns across weekly, monthly, quarterly, half-yearly, and "
        "annual intervals. Detects overspending and duplicate subscriptions."
    ),
    instruction=SPENDING_ANALYST_INSTRUCTION,
    tools=[get_transactions, analyse_spending],
)
