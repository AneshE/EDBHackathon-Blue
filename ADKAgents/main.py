#def main():
#    print("Hello from adkagents!")


import os
import uvicorn
from google.adk.cli.fast_api import get_fast_api_app

# 1. Grab the dynamic port assigned by Google Cloud Run
port = int(os.environ.get("PORT", 8080))

# 2. Wrap your ADK agent in a production-ready FastAPI web server
AGENT_DIR = os.path.dirname(os.path.abspath(__file__))
app = get_fast_api_app(
    agents_dir=AGENT_DIR,
    allow_origins=["*"],
    web=True,
    trace_to_cloud=os.environ.get("TRACE_TO_CLOUD", "false").lower() == "true",
)


import json
import uuid

from fastapi import Body
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types as genai_types

from bank_agent.observability import store, CostGranularity
from bank_agent.agent import root_agent
from bank_agent.tools.customersearch import customer_id_search


# ── Pydantic models for API requests ──────────────────────────────────────

class VerifyRequest(BaseModel):
    customer_id: str
    name: str
    dob: str  # expected format: YYYY-MM-DD


class AdvisorRequest(BaseModel):
    customer_id: str
    name: str
    dob: str


# ── Shared ADK session infrastructure ─────────────────────────────────────

_session_service = InMemorySessionService()
_runner = Runner(
    agent=root_agent,
    app_name="bank_advisor_api",
    session_service=_session_service,
)


# ── API Endpoints ─────────────────────────────────────────────────────────

@app.post("/api/verify")
async def api_verify(req: VerifyRequest):
    """Single-shot identity verification for the Streamlit form.

    Accepts customer_id, name, and dob in one request, verifies against
    the database, and returns a success/failure response.
    """
    try:
        # Create a temporary ToolContext-like lookup
        from bank_agent.shared_tools.bigquery_client import bq_client, BQ_DATASET

        if BQ_DATASET:
            from google.cloud import bigquery as bq_module
            client = bq_client()
            query = f"""
                SELECT customer_id, name, dob, postcode
                FROM `{BQ_DATASET}.customers`
                WHERE customer_id = @customer_id
            """
            job_config = bq_module.QueryJobConfig(
                query_parameters=[
                    bq_module.ScalarQueryParameter("customer_id", "STRING", req.customer_id)
                ]
            )
            result_df = client.query(query, job_config=job_config).to_dataframe()

            if result_df.empty:
                return JSONResponse(
                    status_code=404,
                    content={"status": "error", "message": "Customer ID not found."},
                )

            record = result_df.iloc[0].to_dict()
            # Compare name (case-insensitive) and DOB
            name_match = record.get("name", "").strip().lower() == req.name.strip().lower()
            dob_match = str(record.get("dob", "")).strip()[:10] == req.dob.strip()[:10]

            if name_match and dob_match:
                return JSONResponse(content={
                    "status": "verified",
                    "customer_id": req.customer_id,
                    "message": f"Identity confirmed for {req.customer_id}.",
                })
            else:
                return JSONResponse(
                    status_code=401,
                    content={"status": "failed", "message": "Identity verification failed. Details do not match."},
                )
        else:
            # Fallback: no BigQuery — accept any input for demo mode
            return JSONResponse(content={
                "status": "verified",
                "customer_id": req.customer_id,
                "message": f"Identity confirmed for {req.customer_id} (demo mode).",
            })

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": f"Verification error: {str(e)}"},
        )


@app.post("/api/advisor")
async def api_advisor(req: AdvisorRequest):
    """Run the ui_advisor agent and return structured JSON for the Streamlit UI.

    Creates an ADK session with pre-verified identity state, sends a prompt
    to trigger the ui_advisor sub-agent, and extracts the JSON response.
    """
    try:
        session_id = str(uuid.uuid4())
        user_id = f"api_user_{req.customer_id}"

        session = await _session_service.create_session(
            app_name="bank_advisor_api",
            user_id=user_id,
            session_id=session_id,
            state={
                "identity_verified": True,
                "verified_customer_id": req.customer_id,
            },
        )

        # Craft a prompt that triggers the ui_advisor agent
        prompt = (
            f"I am verified customer {req.customer_id}. "
            f"Please analyse my spending and provide the structured JSON "
            f"financial advisor data for the UI dashboard — including my "
            f"budget blueprint, perk optimization opportunities, and wealth "
            f"growth projections."
        )

        user_message = genai_types.Content(
            role="user",
            parts=[genai_types.Part(text=prompt)],
        )

        # Collect agent responses
        response_text = ""
        async for event in _runner.run_async(
            user_id=user_id,
            session_id=session_id,
            new_message=user_message,
        ):
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if part.text:
                        response_text += part.text

        # Try to parse the JSON from the response
        # The agent might wrap it in markdown code blocks
        json_str = response_text.strip()
        if json_str.startswith("```"):
            # Strip markdown code fences
            lines = json_str.split("\n")
            lines = [l for l in lines if not l.strip().startswith("```")]
            json_str = "\n".join(lines)

        try:
            parsed = json.loads(json_str)
            return JSONResponse(content=parsed)
        except json.JSONDecodeError:
            # Return raw text if JSON parsing fails
            return JSONResponse(content={
                "status": "raw_response",
                "raw_text": response_text,
                "message": "Agent response was not valid JSON. Raw text returned.",
            })

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": f"Advisor error: {str(e)}"},
        )


@app.get("/obs", response_class=HTMLResponse)
async def obs_dashboard():
    """Serves the frontend dashboard for agent observability."""
    html_path = os.path.join(AGENT_DIR, "bank_agent", "observability", "dashboard.html")
    if os.path.exists(html_path):
        with open(html_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse(content="Dashboard file not found.", status_code=404)


@app.get("/obs/summary")
async def obs_summary(granularity: str | None = None):
    """Aggregated stats: sessions, total tokens, cost, avg latency.

    Optional ``?granularity=session|turn|cumulative`` query param overrides
    the default (env ``COST_GRANULARITY``).
    """
    gran = None
    if granularity:
        try:
            gran = CostGranularity(granularity.strip().lower())
        except ValueError:
            pass
    return store.get_summary(granularity=gran)


@app.get("/obs/traces")
async def obs_traces(limit: int = 100):
    """Individual LLM call records (newest first).

    Optional ``?limit=N`` query param controls the number of records returned
    (default 100).
    """
    return store.get_traces(limit=limit)


@app.get("/obs/tools")
async def obs_tools():
    """Per-tool call counts, success rates, and duration percentiles."""
    return store.get_tool_stats()


@app.post("/obs/reset")
async def obs_reset():
    """Clear all recorded observability data."""
    store.reset()
    return {"status": "ok", "message": "Observability data cleared"}


if __name__ == "__main__":
    # 3. Start the server!
    uvicorn.run(app, host="0.0.0.0", port=port)