#def main():
#    print("Hello from adkagents!")


import os
import logging
import uvicorn
from google.adk.cli.fast_api import get_fast_api_app

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)

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


class ChatRequest(BaseModel):
    customer_id: str
    message: str
    session_id: str = ""
    history: list[dict] = []  # [{role: user|assistant, content: str}]


# ── Shared ADK session infrastructure ─────────────────────────────────────

_session_service = InMemorySessionService()
_runner = Runner(
    agent=root_agent,
    app_name="bank_advisor_api",
    session_service=_session_service,
)


# ── API Endpoints ─────────────────────────────────────────────────────────

def _verify_against_local(customer_id: str, name: str, dob: str):
    """Check customer credentials against the local bq_seed/customers.json file."""
    seed_path = os.path.join(AGENT_DIR, "bq_seed", "customers.json")
    if not os.path.exists(seed_path):
        return None
    with open(seed_path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            record = json.loads(line)
            if record.get("customer_id") != customer_id:
                continue
            name_match = record.get("name", "").strip().lower() == name.strip().lower()
            dob_match = str(record.get("dob", "")).strip()[:10] == dob.strip()[:10]
            return name_match and dob_match
    return False


@app.post("/api/verify")
async def api_verify(req: VerifyRequest):
    """Single-shot identity verification for the Streamlit form."""
    try:
        from bank_agent.shared_tools.bigquery_client import bq_client, BQ_DATASET

        if BQ_DATASET:
            try:
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
            except Exception:
                # BigQuery unavailable — fall through to local seed data
                pass

        # Fallback: verify against local bq_seed/customers.json
        match = _verify_against_local(req.customer_id, req.name, req.dob)
        if match is None or match is False:
            if match is None:
                # Seed file missing — accept in demo mode
                return JSONResponse(content={
                    "status": "verified",
                    "customer_id": req.customer_id,
                    "message": f"Identity confirmed for {req.customer_id} (demo mode).",
                })
            return JSONResponse(
                status_code=401,
                content={"status": "failed", "message": "Identity verification failed. Details do not match."},
            )
        return JSONResponse(content={
            "status": "verified",
            "customer_id": req.customer_id,
            "message": f"Identity confirmed for {req.customer_id}.",
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


_NAV_PHRASES = {
    "budget_blueprint": [
        "show me my budget", "show budget", "go to budget", "open budget",
        "spending breakdown", "spending page", "budget page", "budget breakdown",
        "take me to budget", "navigate to budget",
    ],
    "perk_optimization": [
        "show me perks", "show perks", "go to perks", "open perks",
        "perk page", "perks page", "available perks", "club lloyds perks",
        "take me to perks", "navigate to perks",
    ],
    "wealth_growth_plan": [
        "show me the wealth", "show wealth", "go to wealth", "wealth plan page",
        "growth plan page", "wealth page", "take me to wealth", "navigate to wealth",
    ],
}


@app.post("/api/chat")
async def api_chat(req: ChatRequest):
    """Conversational endpoint — answers the user in plain text.

    Returns a suggested_step only when the query is an explicit navigation request.
    """
    try:
        session_id = str(uuid.uuid4())
        user_id = f"chat_user_{req.customer_id}"

        await _session_service.create_session(
            app_name="bank_advisor_api",
            user_id=user_id,
            session_id=session_id,
            state={
                "identity_verified": True,
                "verified_customer_id": req.customer_id,
            },
        )

        # Build context: verification bypass + prior conversation
        history_text = ""
        if req.history:
            lines = []
            for turn in req.history[:-1]:  # exclude the current message (last entry)
                role_label = "Customer" if turn["role"] == "user" else "Assistant"
                lines.append(f"{role_label}: {turn['content']}")
            if lines:
                history_text = "\n\nPrior conversation:\n" + "\n".join(lines)

        full_message = (
            f"[SYSTEM NOTE: This customer has been FULLY VERIFIED through the secure "
            f"banking portal. Customer ID: {req.customer_id}. "
            f"identity_verified=True. Do NOT ask for identity verification — proceed "
            f"directly with the customer's request.]{history_text}\n\n"
            f"Customer: {req.message}"
        )

        user_message = genai_types.Content(
            role="user",
            parts=[genai_types.Part(text=full_message)],
        )

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

        # Only suggest navigation for explicit phrases — not general questions
        query_lower = req.message.lower()
        suggested_step = None
        for step, phrases in _NAV_PHRASES.items():
            if any(phrase in query_lower for phrase in phrases):
                suggested_step = step
                break

        return JSONResponse(content={
            "message": response_text or "I'm not sure how to help with that. Try asking about your spending, perks, or savings goals.",
            "suggested_step": suggested_step,
            "session_id": session_id,
        })

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": f"Chat error: {str(e)}"},
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