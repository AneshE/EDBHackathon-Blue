import os
from functools import cached_property

from dotenv import load_dotenv
from google.adk.agents import Agent
from google.adk.models.google_llm import Gemini
from google.genai import Client

from .callbacks import require_verified_identity
from .observability import (
    after_model_callback,
    before_model_callback,
    setup_observability,
)
from .prompt import AGENT_INSTRUCTION
from .tools.bigquery_tool import run_bigquery_query
from .tools.customersearch import customer_database_search, customer_id_search
from .tools.productsearch import vertex_vector_search
from .tools.ecommerce_tools import lookup_user_orders, check_product_stock, sales_reporting_query
from .spending_analyst.agent import spending_analyst_agent
from google.adk.tools.tool_context import ToolContext

load_dotenv()


class VertexGemini(Gemini):
    """Gemini model that unconditionally uses Vertex AI (ADC) instead of an API key."""

    @cached_property
    def api_client(self) -> Client:
        return Client(
            vertexai=True,
            project=os.getenv("GOOGLE_CLOUD_PROJECT"),
            location=os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1"),
        )


# Initialise OpenTelemetry exporters and the metrics store.
setup_observability()

def mark_verified(customer_id: str, tool_context: ToolContext) -> dict:
    """Call this tool when the customer's identity has been successfully verified."""
    tool_context.state["identity_verified"] = True
    tool_context.state["verified_customer_id"] = customer_id
    return {"status": "verified", "message": f"Identity confirmed for {customer_id}"}


def mark_failed(tool_context: ToolContext) -> dict:
    """Call this tool when the customer's identity verification has failed."""
    tool_context.state["identity_verified"] = False
    return {"status": "failed"}

verification_agent = Agent(
    name="verification_agent",
    model=VertexGemini(model="gemini-2.5-flash"),
    description="Verifies customer identity before passing to the rest of the pipeline.",
    instruction="""
    You are the Bank's identity verification agent.

    PHASE 1: IDENTITY VERIFICATION
    - Ask for Customer ID. Call 'customer_id_search' with it.
    - Ask for Name and (DOB or Postcode).
    - If the user's input matches the tool output, call 'mark_verified' and inform the user they are verified. Transfer back to 'bank_agent' for progressing the conversation
    - If verification fails, call 'mark_failed' and inform the user. Do not proceed further.

    CRITICAL: Never share the DOB or Postcode from the database tool with the user.
    NEVER tell them the exact reason why we couldn't get their information.
    """,
    tools=[customer_id_search, mark_verified, mark_failed]
)

spending_analyst_agent.before_agent_callback = require_verified_identity

root_agent = Agent(
    name="bank_agent",
    model=VertexGemini(model="gemini-2.5-flash"),
    description="A helpful banking assistant.",
    instruction=AGENT_INSTRUCTION,
    tools=[mark_verified, mark_failed, customer_database_search, vertex_vector_search, run_bigquery_query],
    sub_agents=[verification_agent, spending_analyst_agent],
    before_model_callback=before_model_callback,
    after_model_callback=after_model_callback,
)
