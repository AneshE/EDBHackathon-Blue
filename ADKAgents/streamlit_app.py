"""
Streamlit Financial Advisor — 4-Step Wizard UI

A premium, dark-themed Streamlit app that walks the user through:
  1. 🔐 ID Verification
  2. 📊 Budget Blueprint
  3. 📺 Perk Optimization
  4. 📈 Wealth Growth Plan

Connects to the FastAPI backend (/api/verify, /api/advisor) or falls
back to hardcoded demo data when the backend is unreachable.

Usage:
    streamlit run streamlit_app.py
"""

import os
import re
import json
import datetime
import requests
import streamlit as st
import streamlit.components.v1 as st_components
import plotly.graph_objects as go
import plotly.express as px

# ── Configuration ─────────────────────────────────────────────────────────

API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8080")

STEP_LABELS = [
    "🔐 ID Verification",
    "📊 Budget Blueprint",
    "📺 Perk Optimization",
    "📈 Wealth Growth Plan",
]

# ── Demo/Fallback Data ────────────────────────────────────────────────────

DEMO_DATA = {
    "current_user_intent": "optimize_wealth",
    "ui_steps": [
        {
            "step_number": 1,
            "step_id": "budget_blueprint",
            "title": "📊 Your Budget Blueprint",
            "metric_summary": {"income": 3224.50, "spending": 98.79, "surplus": 3125.71},
            "table_data": [
                {"bucket": "Needs", "actual": 80.80, "percent": 2.5, "target": 50.0, "status": "🟢 Safe"},
                {"bucket": "Wants", "actual": 17.99, "percent": 0.6, "target": 30.0, "status": "🟢 Safe"},
                {"bucket": "Savings", "actual": 0.00, "percent": 0.0, "target": 20.0, "status": "⚡ Action Required"},
            ],
        },
        {
            "step_number": 2,
            "step_id": "perk_optimization",
            "title": "📺 Club Lloyds Perk Optimization",
            "leak_detected": "Subscription outflow of £17.99/mo identified.",
            "action_prompt": "Would you like to swap your out-of-pocket subscription for your included Club Lloyds free Lifestyle Benefit?",
            "options": ["Yes, optimize and save £17.99/mo", "No, keep current billing"],
            "monthly_savings": 17.99,
            "annual_savings": 215.88,
        },
        {
            "step_number": 3,
            "step_id": "wealth_growth_plan",
            "title": "📈 Your Growth Forecast",
            "short_term_projection": "By redirecting your £17.99/month subscription leak into savings, you will build £215.88 in 12 months.",
            "target_want_milestone": "This fully funds your short-term goal: a weekend trip to the Highlands.",
            "long_term_projection": "Automating your 20% target surplus (£644.90/mo) into a High-Yield account builds long-term wealth without altering your day-to-day lifestyle.",
            "monthly_savings_target": 644.90,
            "twelve_month_total": 7738.80,
        },
    ],
}

# ── Page Config ───────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Financial Advisor | Lloyds Banking Group",
    page_icon="🏦",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Custom CSS ────────────────────────────────────────────────────────────

st.markdown(
    """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

    /* ── Global ─────────────────────────────────────────── */
    .stApp {
        background: linear-gradient(135deg, #0a0e1a 0%, #111827 40%, #0d1321 100%);
        font-family: 'Inter', sans-serif;
        color: #e2e8f0;
    }

    .block-container {
        padding-top: 2rem !important;
        max-width: 1100px;
    }

    /* ── Hide Streamlit defaults ────────────────────────── */
    #MainMenu, footer, header { visibility: hidden; }

    /* ── Stepper Navigation ─────────────────────────────── */
    .stepper-container {
        display: flex;
        justify-content: center;
        align-items: center;
        margin-bottom: 2.5rem;
        gap: 0;
    }

    .step-item {
        display: flex;
        align-items: center;
        gap: 0;
    }

    .step-circle {
        width: 48px;
        height: 48px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: 700;
        font-size: 1.1rem;
        transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
        position: relative;
        z-index: 2;
    }

    .step-circle.active {
        background: linear-gradient(135deg, #00854A, #00a85a);
        color: #fff;
        box-shadow: 0 0 24px rgba(0, 133, 74, 0.5), 0 0 48px rgba(0, 133, 74, 0.2);
        transform: scale(1.1);
    }

    .step-circle.completed {
        background: linear-gradient(135deg, #00854A, #006b3c);
        color: #fff;
        box-shadow: 0 0 12px rgba(0, 133, 74, 0.3);
    }

    .step-circle.inactive {
        background: rgba(255, 255, 255, 0.06);
        color: #64748b;
        border: 2px solid rgba(255, 255, 255, 0.08);
    }

    .step-label {
        font-size: 0.75rem;
        font-weight: 500;
        color: #94a3b8;
        text-align: center;
        margin-top: 0.5rem;
        max-width: 110px;
    }

    .step-label.active {
        color: #00854A;
        font-weight: 600;
    }

    .step-connector {
        width: 80px;
        height: 3px;
        background: rgba(255, 255, 255, 0.08);
        margin: 0 4px;
        position: relative;
        top: -12px;
    }

    .step-connector.completed {
        background: linear-gradient(90deg, #00854A, #00a85a);
        box-shadow: 0 0 8px rgba(0, 133, 74, 0.3);
    }

    /* ── Glass Card ─────────────────────────────────────── */
    .glass-card {
        background: rgba(255, 255, 255, 0.04);
        backdrop-filter: blur(24px);
        -webkit-backdrop-filter: blur(24px);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 20px;
        padding: 2rem;
        margin-bottom: 1.5rem;
        transition: all 0.3s ease;
    }

    .glass-card:hover {
        border-color: rgba(0, 133, 74, 0.3);
        box-shadow: 0 8px 32px rgba(0, 133, 74, 0.08);
    }

    .glass-card-accent {
        background: linear-gradient(135deg, rgba(0, 133, 74, 0.08), rgba(0, 168, 90, 0.04));
        border: 1px solid rgba(0, 133, 74, 0.2);
    }

    .glass-card-warn {
        background: linear-gradient(135deg, rgba(245, 158, 11, 0.08), rgba(217, 119, 6, 0.04));
        border: 1px solid rgba(245, 158, 11, 0.2);
    }

    /* ── Metric Cards ───────────────────────────────────── */
    .metric-card {
        background: rgba(255, 255, 255, 0.03);
        backdrop-filter: blur(16px);
        border: 1px solid rgba(255, 255, 255, 0.06);
        border-radius: 16px;
        padding: 1.25rem 1.5rem;
        text-align: center;
        transition: all 0.3s ease;
    }

    .metric-card:hover {
        transform: translateY(-2px);
        border-color: rgba(0, 133, 74, 0.3);
        box-shadow: 0 8px 24px rgba(0, 0, 0, 0.2);
    }

    .metric-value {
        font-size: 2rem;
        font-weight: 800;
        background: linear-gradient(135deg, #00854A, #00d674);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        line-height: 1.2;
    }

    .metric-label {
        font-size: 0.8rem;
        font-weight: 500;
        color: #94a3b8;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        margin-top: 0.3rem;
    }

    /* ── Section Title ──────────────────────────────────── */
    .section-title {
        font-size: 1.8rem;
        font-weight: 800;
        color: #f1f5f9;
        margin-bottom: 0.5rem;
        letter-spacing: -0.02em;
    }

    .section-subtitle {
        font-size: 1rem;
        color: #94a3b8;
        margin-bottom: 2rem;
        font-weight: 400;
    }

    /* ── Table ──────────────────────────────────────────── */
    .budget-table {
        width: 100%;
        border-collapse: separate;
        border-spacing: 0 8px;
    }

    .budget-table th {
        text-align: left;
        padding: 0.75rem 1rem;
        font-size: 0.75rem;
        font-weight: 600;
        color: #64748b;
        text-transform: uppercase;
        letter-spacing: 0.06em;
    }

    .budget-table td {
        padding: 1rem;
        background: rgba(255, 255, 255, 0.03);
        font-size: 0.95rem;
    }

    .budget-table tr td:first-child { border-radius: 12px 0 0 12px; }
    .budget-table tr td:last-child { border-radius: 0 12px 12px 0; }

    .status-safe {
        color: #00d674;
        font-weight: 600;
    }

    .status-action {
        color: #f59e0b;
        font-weight: 600;
    }

    /* ── Buttons ────────────────────────────────────────── */
    .stButton > button {
        background: linear-gradient(135deg, #00854A, #00a85a) !important;
        color: white !important;
        border: none !important;
        border-radius: 12px !important;
        padding: 0.75rem 2.5rem !important;
        font-weight: 600 !important;
        font-size: 1rem !important;
        font-family: 'Inter', sans-serif !important;
        transition: all 0.3s ease !important;
        box-shadow: 0 4px 16px rgba(0, 133, 74, 0.3) !important;
    }

    .stButton > button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 8px 24px rgba(0, 133, 74, 0.4) !important;
    }

    /* ── Inputs ─────────────────────────────────────────── */
    .stTextInput > div > div > input,
    .stDateInput > div > div > input {
        background: rgba(255, 255, 255, 0.05) !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        border-radius: 12px !important;
        color: #e2e8f0 !important;
        font-family: 'Inter', sans-serif !important;
        padding: 0.75rem 1rem !important;
    }

    .stTextInput > div > div > input:focus,
    .stDateInput > div > div > input:focus {
        border-color: #00854A !important;
        box-shadow: 0 0 0 2px rgba(0, 133, 74, 0.2) !important;
    }

    .stTextInput > label,
    .stDateInput > label {
        color: #cbd5e1 !important;
        font-weight: 500 !important;
        font-size: 0.9rem !important;
    }

    /* ── Alert / Leak Card ──────────────────────────────── */
    .leak-card {
        background: linear-gradient(135deg, rgba(239, 68, 68, 0.08), rgba(220, 38, 38, 0.04));
        border: 1px solid rgba(239, 68, 68, 0.2);
        border-radius: 16px;
        padding: 1.5rem;
        margin-bottom: 1rem;
    }

    .leak-icon { font-size: 2rem; margin-bottom: 0.5rem; }

    /* ── Projection Card ────────────────────────────────── */
    .projection-card {
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 16px;
        padding: 1.5rem;
        margin-bottom: 1rem;
        transition: all 0.3s ease;
    }

    .projection-card:hover {
        border-color: rgba(0, 133, 74, 0.3);
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.2);
    }

    /* ── Radio buttons ──────────────────────────────────── */
    .stRadio > div {
        background: rgba(255, 255, 255, 0.03);
        border-radius: 16px;
        padding: 1rem;
        border: 1px solid rgba(255, 255, 255, 0.06);
    }

    .stRadio > label {
        color: #cbd5e1 !important;
        font-weight: 500 !important;
    }

    /* ── Success / Error animations ─────────────────────── */
    @keyframes fadeInUp {
        from { opacity: 0; transform: translateY(20px); }
        to { opacity: 1; transform: translateY(0); }
    }

    .animate-in {
        animation: fadeInUp 0.6s cubic-bezier(0.4, 0, 0.2, 1) forwards;
    }

    /* ── Brand header ───────────────────────────────────── */
    .brand-header {
        text-align: center;
        margin-bottom: 2rem;
    }

    .brand-header h1 {
        font-size: 2.2rem;
        font-weight: 800;
        background: linear-gradient(135deg, #00854A, #00d674, #00854A);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        margin-bottom: 0.3rem;
        letter-spacing: -0.03em;
    }

    .brand-header p {
        color: #64748b;
        font-size: 0.95rem;
    }

    /* ── Savings Intent Banner ─────────────────────────── */
    @keyframes intentGlow {
        0%   { box-shadow: 0 0 24px rgba(0,133,74,0.35), 0 0 60px rgba(0,133,74,0.1); }
        50%  { box-shadow: 0 0 48px rgba(0,133,74,0.65), 0 0 100px rgba(6,182,212,0.2); }
        100% { box-shadow: 0 0 24px rgba(0,133,74,0.35), 0 0 60px rgba(0,133,74,0.1); }
    }
    @keyframes shimmer {
        0%   { background-position: -200% center; }
        100% { background-position: 200% center; }
    }
    .intent-banner {
        background: linear-gradient(135deg, rgba(0,133,74,0.12), rgba(6,182,212,0.08), rgba(0,133,74,0.06));
        border: 1px solid rgba(0,133,74,0.45);
        border-radius: 24px;
        padding: 2.5rem 2rem;
        text-align: center;
        animation: intentGlow 2.8s ease-in-out infinite;
        margin-bottom: 2rem;
        position: relative;
        overflow: hidden;
    }
    .intent-banner::before {
        content: '';
        position: absolute;
        top: 0; left: -100%; right: -100%; height: 1px;
        background: linear-gradient(90deg, transparent, rgba(0,212,116,0.6), transparent);
        animation: shimmer 3s linear infinite;
    }
    .intent-eyebrow {
        font-size: 0.75rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.15em;
        color: #00854A;
        margin-bottom: 0.75rem;
    }
    .intent-goal {
        font-size: 2.6rem;
        font-weight: 800;
        background: linear-gradient(135deg, #00d674 0%, #06b6d4 50%, #00854A 100%);
        background-size: 200% auto;
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        animation: shimmer 4s linear infinite;
        letter-spacing: -0.03em;
        line-height: 1.2;
        margin-bottom: 0.75rem;
    }
    .intent-sub {
        font-size: 1rem;
        color: #94a3b8;
        font-weight: 400;
    }
    .intent-savings-pill {
        display: inline-block;
        background: linear-gradient(135deg, rgba(0,133,74,0.2), rgba(0,168,90,0.1));
        border: 1px solid rgba(0,133,74,0.35);
        border-radius: 999px;
        padding: 0.4rem 1.2rem;
        font-size: 0.9rem;
        font-weight: 600;
        color: #00d674;
        margin-top: 1rem;
    }

    /* ── Chat bubbles ──────────────────────────────────── */
    .chat-user {
        background: linear-gradient(135deg, rgba(0,133,74,0.15), rgba(0,168,90,0.08));
        border: 1px solid rgba(0,133,74,0.25);
        border-radius: 18px 18px 4px 18px;
        padding: 0.75rem 1.1rem;
        margin: 0.5rem 0 0.5rem 15%;
        color: #e2e8f0;
        font-size: 0.95rem;
        line-height: 1.6;
    }
    .chat-assistant {
        background: rgba(255,255,255,0.04);
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 18px 18px 18px 4px;
        padding: 0.75rem 1.1rem;
        margin: 0.5rem 15% 0.5rem 0;
        color: #e2e8f0;
        font-size: 0.95rem;
        line-height: 1.6;
    }
    .chat-label { font-size:0.7rem; font-weight:600; text-transform:uppercase; letter-spacing:0.08em; margin-bottom:0.25rem; color:#64748b; }
    .chat-label-you { color: #00a85a; }

    /* ── Query context banner ───────────────────────────── */
    .query-context {
        background: linear-gradient(135deg, rgba(6,182,212,0.08), rgba(6,182,212,0.03));
        border: 1px solid rgba(6,182,212,0.25);
        border-radius: 14px;
        padding: 0.85rem 1.25rem;
        margin-bottom: 1.5rem;
        display: flex;
        align-items: flex-start;
        gap: 0.75rem;
    }
    .query-context-icon { font-size:1.3rem; flex-shrink:0; margin-top:0.1rem; }
    .query-context-label { font-size:0.7rem; font-weight:700; text-transform:uppercase; letter-spacing:0.1em; color:#06b6d4; margin-bottom:0.2rem; }
    .query-context-text { font-size:0.92rem; color:#e2e8f0; line-height:1.5; }

    /* ── Divider ────────────────────────────────────────── */
    .custom-divider {
        height: 1px;
        background: linear-gradient(90deg, transparent, rgba(0, 133, 74, 0.3), transparent);
        margin: 2rem 0;
    }
</style>
""",
    unsafe_allow_html=True,
)


# ── Session State Init ────────────────────────────────────────────────────

if "current_step" not in st.session_state:
    st.session_state.current_step = 0
if "verified" not in st.session_state:
    st.session_state.verified = False
if "customer_id" not in st.session_state:
    st.session_state.customer_id = ""
if "full_name" not in st.session_state:
    st.session_state.full_name = ""
if "advisor_data" not in st.session_state:
    st.session_state.advisor_data = None
if "perk_choice" not in st.session_state:
    st.session_state.perk_choice = None
if "demo_mode" not in st.session_state:
    st.session_state.demo_mode = False
if "user_query" not in st.session_state:
    st.session_state.user_query = ""
if "chat_messages" not in st.session_state:
    st.session_state.chat_messages = []
if "chat_session_id" not in st.session_state:
    st.session_state.chat_session_id = ""
if "chat_suggested_step" not in st.session_state:
    st.session_state.chat_suggested_step = None
if "savings_intent" not in st.session_state:
    st.session_state.savings_intent = ""
if "savings_goal" not in st.session_state:
    st.session_state.savings_goal = None  # {amount, period_months, monthly_target, query}


# ── Helper Functions ──────────────────────────────────────────────────────


def render_stepper(current: int):
    """Render the horizontal step indicator."""
    html = '<div class="stepper-container">'
    for i, label in enumerate(STEP_LABELS):
        if i < current:
            circle_class = "completed"
            label_class = ""
        elif i == current:
            circle_class = "active"
            label_class = "active"
        else:
            circle_class = "inactive"
            label_class = ""

        icon = "✓" if i < current else str(i + 1)

        html += f"""
        <div style="display:flex;flex-direction:column;align-items:center;">
            <div class="step-circle {circle_class}">{icon}</div>
            <div class="step-label {label_class}">{label}</div>
        </div>
        """
        if i < len(STEP_LABELS) - 1:
            conn_class = "completed" if i < current else ""
            html += f'<div class="step-connector {conn_class}"></div>'

    html += "</div>"
    st.markdown(html, unsafe_allow_html=True)


def call_verify(customer_id: str, name: str, dob: str) -> dict:
    """Call the /api/verify endpoint or fall back to demo mode."""
    try:
        resp = requests.post(
            f"{API_BASE_URL}/api/verify",
            json={"customer_id": customer_id, "name": name, "dob": dob},
            timeout=15,
        )
        return resp.json()
    except requests.exceptions.ConnectionError:
        st.session_state.demo_mode = True
        return {
            "status": "verified",
            "customer_id": customer_id,
            "message": f"Identity confirmed for {customer_id} (demo mode — backend unreachable).",
        }


def call_chat(customer_id: str, message: str, session_id: str, history: list) -> dict:
    """Send a conversational message to the agent, including full history for context."""
    try:
        resp = requests.post(
            f"{API_BASE_URL}/api/chat",
            json={
                "customer_id": customer_id,
                "message": message,
                "session_id": session_id,
                "history": history,
            },
            timeout=60,
        )
        return resp.json()
    except requests.exceptions.ConnectionError:
        return {
            "message": "I'm having trouble connecting to the server right now. Try the quick options above.",
            "suggested_step": None,
            "session_id": session_id,
        }


def call_advisor(customer_id: str, name: str, dob: str) -> dict:
    """Call the /api/advisor endpoint or fall back to demo data."""
    try:
        resp = requests.post(
            f"{API_BASE_URL}/api/advisor",
            json={"customer_id": customer_id, "name": name, "dob": dob},
            timeout=60,
        )
        data = resp.json()
        # Check if we got valid ui_steps
        if "ui_steps" in data:
            return data
        return DEMO_DATA
    except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
        st.session_state.demo_mode = True
        return DEMO_DATA


_GOAL_KEYWORDS = {
    "holiday": ("🌍", "Fund Your Dream Holiday"),
    "vacation": ("✈️", "Fund Your Dream Vacation"),
    "house": ("🏠", "Save for Your First Home"),
    "home": ("🏠", "Save for Your Dream Home"),
    "car": ("🚗", "Save for a New Car"),
    "wedding": ("💍", "Save for Your Perfect Wedding"),
    "emergency": ("🛡️", "Build Your Emergency Fund"),
    "retirement": ("🌅", "Grow Your Retirement Pot"),
    "education": ("🎓", "Invest in Your Education"),
    "invest": ("📈", "Grow Your Investment Portfolio"),
    "savings": ("💰", "Maximise Your Savings"),
    "wealth": ("💎", "Build Long-Term Wealth"),
}


_MONTH_MAP = {
    "jan": 1, "january": 1, "feb": 2, "february": 2, "mar": 3, "march": 3,
    "apr": 4, "april": 4, "may": 5, "jun": 6, "june": 6, "jul": 7, "july": 7,
    "aug": 8, "august": 8, "sep": 9, "sept": 9, "september": 9,
    "oct": 10, "october": 10, "nov": 11, "november": 11, "dec": 12, "december": 12,
}
_MONTH_PATTERN = "|".join(sorted(_MONTH_MAP, key=len, reverse=True))


def _months_until(target_month: int) -> int:
    today = datetime.date.today()
    diff = (target_month - today.month) % 12
    return max(1, diff)


def parse_savings_goal(text: str) -> dict | None:
    """Extract savings intent from natural language.

    Amount is optional — 'save by December' is valid (amount=None).
    Handles month names, abbreviations, and numeric periods.
    """
    save_trigger = re.search(
        r'\b(save|saving|put away|set aside|target|accumulate|how much can i save|how much will i save)\b',
        text, re.IGNORECASE,
    )
    if not save_trigger:
        return None

    # Period detection: try month name first, then numeric period
    period_months = None
    period_label = None

    by_month = re.search(
        r'\bby\s+(?:end\s+of\s+|the\s+end\s+of\s+|next\s+)?(' + _MONTH_PATTERN + r')(?:\s+\d{4})?\b',
        text, re.IGNORECASE,
    )
    if by_month:
        m_name = by_month.group(1).lower()
        target = _MONTH_MAP[m_name]
        period_months = _months_until(target)
        period_label = by_month.group(1).capitalize()
    else:
        period_match = re.search(r'(\d+)\s*(month|week|year)s?', text, re.IGNORECASE)
        if period_match:
            n = int(period_match.group(1))
            unit = period_match.group(2).lower()
            if unit == "week":
                period_months = max(1, round(n / 4.33))
                period_label = f"{n} weeks"
            elif unit == "year":
                period_months = n * 12
                period_label = f"{n} year{'s' if n != 1 else ''}"
            else:
                period_months = n
                period_label = f"{n} month{'s' if n != 1 else ''}"

    # Need at least a period to be meaningful
    if period_months is None:
        return None

    # Amount is optional
    amount_match = re.search(r'[£$]\s*(\d[\d,]*(?:\.\d+)?)', text, re.IGNORECASE)
    amount = float(amount_match.group(1).replace(",", "")) if amount_match else None
    monthly_target = round(amount / period_months, 2) if amount else None

    return {
        "amount": amount,
        "period_months": period_months,
        "period_label": period_label,
        "monthly_target": monthly_target,
        "query": text,
    }


_PAGE_KEYWORDS = {
    "perk": ["perk", "subscription", "benefit", "club", "product", "recommend", "saving"],
    "wealth": ["wealth", "saving", "invest", "forecast", "growth", "goal", "plan", "future"],
}


def get_relevant_user_query(page: str) -> str:
    """Return the most recent user message relevant to the given page, or empty string."""
    keywords = _PAGE_KEYWORDS.get(page, [])
    for msg in reversed(st.session_state.chat_messages):
        if msg["role"] == "user":
            text = msg["content"].lower()
            if any(kw in text for kw in keywords):
                return msg["content"]
    # Fall back to any user message
    for msg in reversed(st.session_state.chat_messages):
        if msg["role"] == "user":
            return msg["content"]
    return ""


def extract_savings_intent() -> tuple[str, str]:
    """Return (emoji, label) for the customer's savings goal from their chat history."""
    all_text = " ".join(
        msg["content"] for msg in st.session_state.chat_messages if msg["role"] == "user"
    ) + " " + st.session_state.user_query
    all_text = all_text.lower()
    for keyword, (emoji, label) in _GOAL_KEYWORDS.items():
        if keyword in all_text:
            return emoji, label
    return "💰", "Grow Your Wealth"


def get_step_data(step_id: str) -> dict | None:
    """Extract a specific step from the advisor data."""
    if not st.session_state.advisor_data:
        return None
    for step in st.session_state.advisor_data.get("ui_steps", []):
        if step.get("step_id") == step_id:
            return step
    return None


# ── Brand Header ──────────────────────────────────────────────────────────

st.markdown(
    """
    <div class="brand-header">
        <h1>🏦 Financial Advisor</h1>
        <p>Your personalised wealth optimisation journey</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ── Stepper ───────────────────────────────────────────────────────────────


# ── Demo Mode Banner ─────────────────────────────────────────────────────

if st.session_state.demo_mode:
    st.markdown(
        """
        <div style="text-align:center;padding:0.6rem 1rem;
                    background:rgba(245,158,11,0.1);
                    border:1px solid rgba(245,158,11,0.3);
                    border-radius:10px;margin-bottom:1.5rem;
                    font-size:0.85rem;color:#f59e0b;">
            ⚡ Demo Mode — Using sample data (backend unreachable)
        </div>
        """,
        unsafe_allow_html=True,
    )


# ══════════════════════════════════════════════════════════════════════════
# STEP 1 — ID VERIFICATION
# ══════════════════════════════════════════════════════════════════════════

if st.session_state.current_step == 0:
    st.markdown(
        '<div class="section-title">🔐 Identity Verification</div>'
        '<div class="section-subtitle">Please provide your details to get started</div>',
        unsafe_allow_html=True,
    )

    col1, col2 = st.columns(2)
    with col1:
        customer_id = st.text_input(
            "Customer ID",
            placeholder="e.g. C004",
            key="input_customer_id",
        )
        full_name = st.text_input(
            "Full Name",
            placeholder="e.g. Margaret Taylor",
            key="input_name",
        )
    with col2:
        dob = st.date_input(
            "Date of Birth",
            value=None,
            key="input_dob",
            min_value=datetime.date(1900, 1, 1),
            max_value=datetime.date.today(),
        )

    _, center, _ = st.columns([1, 1, 1])
    with center:
        if st.button("🔒 Verify Identity", use_container_width=True, key="btn_verify"):
            if not customer_id or not full_name or not dob:
                st.error("Please fill in all fields.")
            else:
                with st.spinner("Verifying your identity..."):
                    dob_str = dob.strftime("%Y-%m-%d") if dob else ""
                    result = call_verify(customer_id, full_name, dob_str)

                if result.get("status") == "verified":
                    st.session_state.verified = True
                    st.session_state.customer_id = customer_id
                    st.session_state.full_name = full_name

                    # Pre-load advisor data while user decides what they want
                    with st.spinner("Verifying identity..."):
                        st.session_state.advisor_data = call_advisor(
                            customer_id, full_name, dob_str
                        )

                    st.session_state.current_step = 1
                    st.rerun()
                else:
                    st.error(f"❌ {result.get('message', 'Verification failed.')}")


# ══════════════════════════════════════════════════════════════════════════
# STEP 1 — HOW CAN WE HELP? (chat interface)
# ══════════════════════════════════════════════════════════════════════════

elif st.session_state.current_step == 1:
    first_name = st.session_state.full_name.split()[0] if st.session_state.full_name else "there"

    st.markdown(
        f"""
        <div class="brand-header" style="margin-top:1rem;margin-bottom:1.5rem;">
            <h1 style="font-size:1.9rem;">👋 Welcome, {first_name}!</h1>
            <p style="font-size:1rem;color:#94a3b8;">Identity verified. Ask me anything about your finances.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Quick-navigate buttons (explicit intent — go straight to that page)
    q_col1, q_col2 = st.columns(2)
    with q_col1:
        if st.button("📊 My Budget", use_container_width=True, key="q_spending"):
            st.session_state.current_step = 2
            st.rerun()
    with q_col2:
        if st.button("🎁 Available Perks", use_container_width=True, key="q_perks"):
            st.session_state.current_step = 3
            st.rerun()

    st.markdown('<div class="custom-divider"></div>', unsafe_allow_html=True)

    # Seed greeting if chat is empty
    if not st.session_state.chat_messages:
        st.session_state.chat_messages = [
            {
                "role": "assistant",
                "content": f"Hi {first_name}! I'm your financial advisor. You can ask me about your spending habits, available perks and benefits, or how to grow your savings. What would you like to know?",
            }
        ]

    # Chat messages — plain rendering, no scroll container
    for msg in st.session_state.chat_messages:
        if msg["role"] == "user":
            st.markdown(
                f'<div class="chat-label chat-label-you">You</div>'
                f'<div class="chat-user">{msg["content"]}</div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f'<div class="chat-label">Assistant</div>'
                f'<div class="chat-assistant">{msg["content"]}</div>',
                unsafe_allow_html=True,
            )

    # Chat input
    with st.form(key="chat_form", clear_on_submit=True):
        chat_col, send_col = st.columns([5, 1])
        with chat_col:
            user_input = st.text_input(
                "Message",
                placeholder="Ask me anything about your finances...",
                label_visibility="collapsed",
                key="chat_input",
            )
        with send_col:
            send = st.form_submit_button("Send", use_container_width=True)

    if send and user_input.strip():
        q = user_input.strip()
        q_lower = q.lower()

        # 1. Check for specific savings goal (e.g. "save £600 in 2 months") → Perk page
        _goal = parse_savings_goal(q)
        if _goal:
            st.session_state.savings_goal = _goal
            st.session_state.chat_messages.append({"role": "user", "content": q})
            st.session_state.current_step = 3
            st.rerun()

        # 2. Navigate only on explicit page requests — general questions stay in chat
        _nav_phrases = {
            "budget_blueprint": [
                "show my budget", "show budget", "my budget", "budget breakdown",
                "budget blueprint", "open budget", "go to budget", "budget page",
                "show spending breakdown", "spending breakdown",
            ],
            "perk_optimization": [
                "show perks", "show my perks", "available perks", "perk optimization",
                "perk optimisation", "club perks", "open perks", "go to perks",
                "show benefits", "my perks",
            ],
            "wealth_growth_plan": [
                "wealth plan", "growth plan", "show wealth plan", "wealth forecast",
                "growth forecast", "show wealth", "open wealth", "go to wealth",
            ],
        }
        _step_to_index = {"budget_blueprint": 2, "perk_optimization": 3, "wealth_growth_plan": 4}

        direct_nav = None
        for step_key, phrases in _nav_phrases.items():
            if any(phrase in q_lower for phrase in phrases):
                direct_nav = step_key
                break

        if direct_nav:
            # Navigate straight to the page without an LLM call
            st.session_state.chat_messages.append({"role": "user", "content": q})
            st.session_state.current_step = _step_to_index[direct_nav]
            st.rerun()
        else:
            # General question — answer in chat
            st.session_state.chat_messages.append({"role": "user", "content": q})
            with st.spinner("Thinking..."):
                result = call_chat(
                    st.session_state.customer_id,
                    q,
                    st.session_state.chat_session_id,
                    st.session_state.chat_messages,
                )
            agent_reply = result.get("message", "Sorry, I couldn't process that.")
            st.session_state.chat_session_id = result.get("session_id", st.session_state.chat_session_id)
            st.session_state.chat_messages.append({"role": "assistant", "content": agent_reply})
            st.session_state.chat_suggested_step = None
            st.rerun()


# ══════════════════════════════════════════════════════════════════════════
# STEP 2 — BUDGET BLUEPRINT
# ══════════════════════════════════════════════════════════════════════════

elif st.session_state.current_step == 2:
    blueprint = get_step_data("budget_blueprint")
    if not blueprint:
        blueprint = DEMO_DATA["ui_steps"][0]
        st.session_state.demo_mode = True

    st.markdown(
        f'<div class="section-title">{blueprint["title"]}</div>'
        f'<div class="section-subtitle">How your spending stacks up against the 50/30/20 golden rule</div>',
        unsafe_allow_html=True,
    )

    # ── Metric Cards ──
    metrics = blueprint.get("metric_summary", {})
    c1, c2, c3 = st.columns(3)

    for col, (label, key, color) in zip(
        [c1, c2, c3],
        [
            ("Monthly Income", "income", "#00d674"),
            ("Total Spending", "spending", "#f59e0b"),
            ("Surplus", "surplus", "#06b6d4"),
        ],
    ):
        with col:
            val = metrics.get(key, 0)
            st.markdown(
                f"""
                <div class="metric-card">
                    <div class="metric-value" style="background:linear-gradient(135deg,{color},{color}cc);
                        -webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;">
                        £{val:,.2f}
                    </div>
                    <div class="metric-label">{label}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.markdown('<div class="custom-divider"></div>', unsafe_allow_html=True)

    # ── Charts ──
    chart_col, table_col = st.columns([1, 1])

    table_data = blueprint.get("table_data", [])

    with chart_col:
        # Donut chart: Actual vs Target
        buckets = [row["bucket"] for row in table_data]
        actuals = [row["actual"] for row in table_data]
        targets = [row["target"] for row in table_data]
        percents = [row["percent"] for row in table_data]

        colors_actual = ["#06b6d4", "#8b5cf6", "#00854A"]
        colors_target = ["#06b6d4", "#8b5cf6", "#00854A"]

        fig = go.Figure()

        # Outer ring: Target
        fig.add_trace(
            go.Pie(
                labels=[f"{b} (Target)" for b in buckets],
                values=targets,
                hole=0.55,
                marker=dict(colors=colors_target, line=dict(color="#0a0e1a", width=3)),
                textinfo="label+percent",
                textfont=dict(size=11, color="#94a3b8"),
                domain=dict(x=[0, 0.48]),
                name="Target",
            )
        )

        # Inner ring: Actual
        actual_vals = [max(a, 0.1) for a in actuals]  # Prevent zero-size slices
        fig.add_trace(
            go.Pie(
                labels=[f"{b} (Actual)" for b in buckets],
                values=actual_vals,
                hole=0.55,
                marker=dict(
                    colors=colors_actual,
                    line=dict(color="#0a0e1a", width=3),
                ),
                textinfo="label+percent",
                textfont=dict(size=11, color="#e2e8f0"),
                domain=dict(x=[0.52, 1]),
                name="Actual",
            )
        )

        fig.update_layout(
            title=dict(
                text="Target Split          vs          Actual Split",
                font=dict(size=14, color="#94a3b8", family="Inter"),
                x=0.5,
            ),
            showlegend=False,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(t=60, b=20, l=20, r=20),
            height=350,
            annotations=[
                dict(
                    text="Target",
                    x=0.19,
                    y=0.5,
                    font=dict(size=14, color="#94a3b8", family="Inter"),
                    showarrow=False,
                ),
                dict(
                    text="Actual",
                    x=0.81,
                    y=0.5,
                    font=dict(size=14, color="#e2e8f0", family="Inter"),
                    showarrow=False,
                ),
            ],
        )
        st.plotly_chart(fig, use_container_width=True, key="budget_donut")

    with table_col:
        st.markdown(
            '<div style="margin-top:1rem;"></div>',
            unsafe_allow_html=True,
        )
        # Budget table
        table_html = (
            "<table class=\"budget-table\">"
            "<thead>"
            "<tr>"
            "<th>Bucket</th>"
            "<th>Actual £</th>"
            "<th>Actual %</th>"
            "<th>Target %</th>"
            "<th>Status</th>"
            "</tr>"
            "</thead>"
            "<tbody>"
        )
        for row in table_data:
            status_class = "status-safe" if "Safe" in row["status"] else "status-action"
            table_html += (
                "<tr>"
                f"<td style=\"font-weight:600;\">{row['bucket']}</td>"
                f"<td>£{row['actual']:,.2f}</td>"
                f"<td>{row['percent']:.1f}%</td>"
                f"<td>{row['target']:.0f}%</td>"
                f"<td class=\"{status_class}\">{row['status']}</td>"
                "</tr>"
            )
        table_html += "</tbody></table>"
        st.markdown(
            f'<div class="glass-card">{table_html}</div>',
            unsafe_allow_html=True,
        )

        # Bar chart: Actual vs Target comparison
        fig_bar = go.Figure()
        fig_bar.add_trace(
            go.Bar(
                name="Actual %",
                x=buckets,
                y=percents,
                marker_color=["#06b6d4", "#8b5cf6", "#00854A"],
                text=[f"{p:.1f}%" for p in percents],
                textposition="outside",
                textfont=dict(color="#e2e8f0", size=12),
            )
        )
        fig_bar.add_trace(
            go.Bar(
                name="Target %",
                x=buckets,
                y=targets,
                marker_color=["rgba(6,182,212,0.3)", "rgba(139,92,246,0.3)", "rgba(0,133,74,0.3)"],
                text=[f"{t:.0f}%" for t in targets],
                textposition="outside",
                textfont=dict(color="#94a3b8", size=12),
            )
        )
        fig_bar.update_layout(
            barmode="group",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#94a3b8", family="Inter"),
            showlegend=True,
            legend=dict(
                orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
                font=dict(color="#94a3b8"),
            ),
            xaxis=dict(showgrid=False),
            yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.05)", title="Percentage"),
            margin=dict(t=30, b=20, l=40, r=20),
            height=200,
        )
        st.plotly_chart(fig_bar, use_container_width=True, key="budget_bars")

    st.markdown('<div class="custom-divider"></div>', unsafe_allow_html=True)

    _, center, _ = st.columns([1, 1, 1])
    with center:
        if st.button("← Back to Chat", use_container_width=True, key="btn_step2"):
            st.session_state.current_step = 1
            st.rerun()


# ══════════════════════════════════════════════════════════════════════════
# STEP 3 — PERK OPTIMIZATION
# ══════════════════════════════════════════════════════════════════════════

elif st.session_state.current_step == 3:
    perk = get_step_data("perk_optimization")
    if not perk:
        perk = DEMO_DATA["ui_steps"][1]

    st.markdown(
        f'<div class="section-title">{perk["title"]}</div>'
        f'<div class="section-subtitle">Smart actions to optimise your spending</div>',
        unsafe_allow_html=True,
    )

    # ── Query Context Banner ──
    _perk_query = get_relevant_user_query("perk")
    if _perk_query:
        st.markdown(
            f"""
            <div class="query-context">
                <div class="query-context-icon">💬</div>
                <div>
                    <div class="query-context-label">Based on your query</div>
                    <div class="query-context-text">"{_perk_query}"</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # ── Savings Goal Banner (if customer stated a specific goal) ──
    _goal = st.session_state.savings_goal
    if _goal:
        _period_label = _goal.get("period_label", "your target period")
        _perk_monthly_contrib = perk.get("monthly_savings", 0)

        if _goal.get("amount"):
            _total = _goal["amount"]
            _monthly = _goal["monthly_target"]
            _perk_pct = min(100, round((_perk_monthly_contrib / _monthly) * 100)) if _monthly else 0
            _remaining = max(0, _monthly - _perk_monthly_contrib)
            _goal_line = f"🎯 Save £{_total:,.2f} by {_period_label}"
            _sub_line = f"Monthly target: <strong style='color:#00d674;'>£{_monthly:,.2f}/month</strong>"
            _pills = (
                f'<div class="intent-savings-pill">✂️ Perk savings: £{_perk_monthly_contrib:,.2f}/mo ({_perk_pct}%)</div>'
                f'<div class="intent-savings-pill" style="border-color:rgba(6,182,212,0.35);color:#06b6d4;">'
                f'🎯 Still needed: £{_remaining:,.2f}/mo</div>'
            )
        else:
            _goal_line = f"🎯 Save as much as possible by {_period_label}"
            _sub_line = f"Perk savings of <strong style='color:#00d674;'>£{_perk_monthly_contrib:,.2f}/month</strong> are a great start"
            _pills = f'<div class="intent-savings-pill">✂️ Potential monthly saving: £{_perk_monthly_contrib:,.2f}</div>'

        st.markdown(
            f"""
            <div class="intent-banner" style="margin-bottom:1.5rem;">
                <div class="intent-eyebrow">Your Savings Goal</div>
                <div class="intent-goal">{_goal_line}</div>
                <div class="intent-sub">{_sub_line}</div>
                <div style="margin-top:1.25rem;display:flex;justify-content:center;gap:1.5rem;flex-wrap:wrap;">
                    {_pills}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # ── Leak Detection Alert ──
    st.markdown(
        f"""
        <div class="leak-card animate-in">
            <div class="leak-icon">🔍</div>
            <div style="font-size:1.1rem;font-weight:600;color:#fca5a5;margin-bottom:0.5rem;">
                Spending Leak Detected
            </div>
            <div style="color:#e2e8f0;font-size:0.95rem;">
                {perk.get("leak_detected", "")}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── Savings Highlight ──
    monthly = perk.get("monthly_savings", 0)
    annual = perk.get("annual_savings", 0)

    s1, s2 = st.columns(2)
    with s1:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-value">£{monthly:,.2f}</div>
                <div class="metric-label">Potential Monthly Savings</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with s2:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-value" style="background:linear-gradient(135deg,#06b6d4,#06b6d4cc);
                    -webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;">
                    £{annual:,.2f}
                </div>
                <div class="metric-label">Annual Impact</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown('<div class="custom-divider"></div>', unsafe_allow_html=True)

    # ── Action Prompt ──
    st.markdown(
        f"""
        <div class="glass-card glass-card-accent">
            <div style="font-size:1.1rem;font-weight:600;color:#e2e8f0;margin-bottom:1rem;">
                💡 {perk.get("action_prompt", "")}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    options = perk.get("options", ["Yes", "No"])
    choice = st.radio(
        "Select your preference:",
        options=options,
        index=None,
        key="radio_perk",
    )

    st.markdown('<div class="custom-divider"></div>', unsafe_allow_html=True)

    col_back, col_next = st.columns(2)
    with col_back:
        if st.button("← Back to Chat", use_container_width=True, key="btn_back_step2"):
            st.session_state.current_step = 1
            st.rerun()
    with col_next:
        if st.button("View Wealth Plan →", use_container_width=True, key="btn_to_wealth"):
            st.session_state.perk_choice = choice
            st.session_state.current_step = 4
            st.rerun()


# ══════════════════════════════════════════════════════════════════════════
# STEP 4 — WEALTH GROWTH PLAN
# ══════════════════════════════════════════════════════════════════════════

elif st.session_state.current_step == 4:
    growth = get_step_data("wealth_growth_plan")
    if not growth:
        growth = DEMO_DATA["ui_steps"][2]

    st.markdown(
        f'<div class="section-title">{growth["title"]}</div>'
        f'<div class="section-subtitle">Your personalised wealth building roadmap</div>',
        unsafe_allow_html=True,
    )

    # ── Savings Intent Hero ──
    _intent_emoji, _intent_label = extract_savings_intent()
    _perk_data = get_step_data("perk_optimization")
    _perk_monthly = _perk_data.get("monthly_savings", 0) if _perk_data else 0
    _optimized = st.session_state.perk_choice and "Yes" in str(st.session_state.perk_choice)
    _monthly_target = growth.get("monthly_savings_target", 644.90)
    _effective_monthly = _monthly_target + (_perk_monthly if _optimized else 0)
    _annual_total = _effective_monthly * 12

    _pill_text = (
        f"£{_effective_monthly:,.2f}/mo · £{_annual_total:,.2f} by year-end"
        + (" · Perk savings applied ✓" if _optimized else "")
    )

    st.markdown(
        f"""
        <div class="intent-banner">
            <div class="intent-eyebrow">Your Savings Goal</div>
            <div class="intent-goal">{_intent_emoji} {_intent_label}</div>
            <div class="intent-sub">Here's exactly how we'll get you there</div>
            <div class="intent-savings-pill">{_pill_text}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── Short-term Projection ──
    st.markdown(
        f"""
        <div class="glass-card glass-card-accent animate-in">
            <div style="display:flex;align-items:center;gap:0.75rem;margin-bottom:1rem;">
                <span style="font-size:2rem;">🎯</span>
                <div>
                    <div style="font-size:1.1rem;font-weight:700;color:#e2e8f0;">Short-Term Projection</div>
                    <div style="font-size:0.85rem;color:#94a3b8;">12-month outlook</div>
                </div>
            </div>
            <div style="color:#e2e8f0;font-size:0.95rem;line-height:1.7;">
                {growth.get("short_term_projection", "")}
            </div>
            <div style="margin-top:1rem;padding:0.75rem 1rem;background:rgba(0,133,74,0.1);
                        border-radius:10px;border:1px solid rgba(0,133,74,0.2);">
                <span style="color:#00d674;font-weight:600;">🏆 Milestone:</span>
                <span style="color:#e2e8f0;"> {growth.get("target_want_milestone", "")}</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── Growth Chart ──
    monthly_target = growth.get("monthly_savings_target", 644.90)
    twelve_total = growth.get("twelve_month_total", 7738.80)

    # Build projection data
    months = list(range(0, 13))
    month_labels = [
        "Now", "Month 1", "Month 2", "Month 3", "Month 4", "Month 5",
        "Month 6", "Month 7", "Month 8", "Month 9", "Month 10",
        "Month 11", "Month 12",
    ]
    savings_projection = [monthly_target * m for m in months]

    # Also show perk-based savings if they opted in
    perk_data = get_step_data("perk_optimization")
    perk_monthly = perk_data.get("monthly_savings", 0) if perk_data else 0
    optimized = st.session_state.perk_choice and "Yes" in str(st.session_state.perk_choice)
    perk_projection = [(monthly_target + perk_monthly) * m for m in months] if optimized else None

    fig_growth = go.Figure()

    fig_growth.add_trace(
        go.Scatter(
            x=month_labels,
            y=savings_projection,
            mode="lines+markers",
            name="Base Savings",
            line=dict(color="#00854A", width=3, shape="spline"),
            marker=dict(size=6, color="#00854A"),
            fill="tonexty" if perk_projection else "tozeroy",
            fillcolor="rgba(0,133,74,0.1)",
        )
    )

    if perk_projection:
        fig_growth.add_trace(
            go.Scatter(
                x=month_labels,
                y=perk_projection,
                mode="lines+markers",
                name="Optimized (with perk savings)",
                line=dict(color="#06b6d4", width=3, shape="spline", dash="dot"),
                marker=dict(size=6, color="#06b6d4"),
                fill="tozeroy",
                fillcolor="rgba(6,182,212,0.05)",
            )
        )

    fig_growth.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#94a3b8", family="Inter"),
        xaxis=dict(
            showgrid=False,
            tickangle=-45,
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor="rgba(255,255,255,0.05)",
            title="Projected Savings (£)",
            tickprefix="£",
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            font=dict(color="#94a3b8"),
        ),
        margin=dict(t=30, b=60, l=60, r=20),
        height=380,
    )
    st.plotly_chart(fig_growth, use_container_width=True, key="growth_chart")

    # ── Metrics ──
    m1, m2 = st.columns(2)
    with m1:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-value">£{monthly_target:,.2f}</div>
                <div class="metric-label">Monthly Savings Target</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with m2:
        display_total = twelve_total
        if optimized and perk_monthly:
            display_total = (monthly_target + perk_monthly) * 12
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-value" style="background:linear-gradient(135deg,#06b6d4,#06b6d4cc);
                    -webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;">
                    £{display_total:,.2f}
                </div>
                <div class="metric-label">12-Month Projected Total</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown('<div class="custom-divider"></div>', unsafe_allow_html=True)

    # ── Long-term Projection ──
    st.markdown(
        f"""
        <div class="glass-card animate-in">
            <div style="display:flex;align-items:center;gap:0.75rem;margin-bottom:0.75rem;">
                <span style="font-size:2rem;">🚀</span>
                <div>
                    <div style="font-size:1.1rem;font-weight:700;color:#e2e8f0;">Long-Term Wealth Building</div>
                    <div style="font-size:0.85rem;color:#94a3b8;">Building lasting financial security</div>
                </div>
            </div>
            <div style="color:#e2e8f0;font-size:0.95rem;line-height:1.7;">
                {growth.get("long_term_projection", "")}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── Long-Term Compound Growth Chart ──
    _lt_monthly = monthly_target + (perk_monthly if optimized else 0)
    _years = list(range(0, 31))

    def _compound_value(monthly: float, annual_rate: float, years: int) -> float:
        if annual_rate == 0:
            return monthly * years * 12
        r = annual_rate / 12
        n = years * 12
        return monthly * ((1 + r) ** n - 1) / r

    _conservative = [_compound_value(_lt_monthly, 0.02, y) for y in _years]
    _moderate     = [_compound_value(_lt_monthly, 0.05, y) for y in _years]
    _growth       = [_compound_value(_lt_monthly, 0.08, y) for y in _years]

    fig_lt = go.Figure()

    fig_lt.add_trace(go.Scatter(
        x=_years, y=_conservative,
        mode="lines", name="Conservative (2%)",
        line=dict(color="#94a3b8", width=2, dash="dot"),
        fill="tozeroy", fillcolor="rgba(148,163,184,0.04)",
    ))
    fig_lt.add_trace(go.Scatter(
        x=_years, y=_moderate,
        mode="lines", name="Balanced (5%)",
        line=dict(color="#00854A", width=3, shape="spline"),
        fill="tozeroy", fillcolor="rgba(0,133,74,0.07)",
    ))
    fig_lt.add_trace(go.Scatter(
        x=_years, y=_growth,
        mode="lines", name="Growth (8%)",
        line=dict(color="#f59e0b", width=2.5, shape="spline"),
        fill="tozeroy", fillcolor="rgba(245,158,11,0.05)",
    ))

    # Milestone annotations at 10 and 20 years
    for _yr, _color in [(10, "#00854A"), (20, "#f59e0b")]:
        fig_lt.add_vline(
            x=_yr,
            line_width=1,
            line_dash="dash",
            line_color="rgba(255,255,255,0.15)",
            annotation_text=f"Year {_yr}",
            annotation_position="top",
            annotation_font_color="#94a3b8",
            annotation_font_size=11,
        )

    fig_lt.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#94a3b8", family="Inter"),
        xaxis=dict(
            showgrid=False,
            title="Years",
            tickmode="array",
            tickvals=[0, 5, 10, 15, 20, 25, 30],
            ticktext=["Now", "5yr", "10yr", "15yr", "20yr", "25yr", "30yr"],
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor="rgba(255,255,255,0.05)",
            title="Projected Wealth (£)",
            tickprefix="£",
            tickformat=",.0f",
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            font=dict(color="#94a3b8"),
        ),
        margin=dict(t=40, b=50, l=70, r=20),
        height=360,
        hovermode="x unified",
    )
    st.plotly_chart(fig_lt, use_container_width=True, key="longterm_chart")

    # Summary milestone metrics
    _c10, _c20, _c30 = st.columns(3)
    for _col, _yr, _val, _label, _color in [
        (_c10, 10, _moderate[10], "10-Year (Balanced)", "#00854A"),
        (_c20, 20, _moderate[20], "20-Year (Balanced)", "#06b6d4"),
        (_c30, 30, _growth[30],   "30-Year (Growth)",   "#f59e0b"),
    ]:
        with _col:
            st.markdown(
                f"""
                <div class="metric-card" style="text-align:center;">
                    <div class="metric-value" style="font-size:1.3rem;background:linear-gradient(135deg,{_color},{_color}bb);
                        -webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;">
                        £{_val:,.0f}
                    </div>
                    <div class="metric-label">{_label}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    # ── User's perk choice summary ──
    if st.session_state.perk_choice:
        choice_text = st.session_state.perk_choice
        if "Yes" in choice_text:
            st.markdown(
                f"""
                <div class="glass-card glass-card-accent" style="text-align:center;">
                    <span style="font-size:2rem;">✅</span>
                    <div style="font-size:1rem;font-weight:600;color:#00d674;margin-top:0.5rem;">
                        Perk Optimisation Applied
                    </div>
                    <div style="color:#94a3b8;font-size:0.9rem;margin-top:0.3rem;">
                        Your subscription savings have been factored into the growth forecast above.
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f"""
                <div class="glass-card" style="text-align:center;">
                    <span style="font-size:2rem;">ℹ️</span>
                    <div style="font-size:1rem;font-weight:600;color:#f59e0b;margin-top:0.5rem;">
                        Perk Optimisation Skipped
                    </div>
                    <div style="color:#94a3b8;font-size:0.9rem;margin-top:0.3rem;">
                        You can revisit this decision anytime from your banking dashboard.
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.markdown('<div class="custom-divider"></div>', unsafe_allow_html=True)

    _, center, _ = st.columns([1, 1, 1])
    with center:
        if st.button("← Back to Chat", use_container_width=True, key="btn_back_step3"):
            st.session_state.current_step = 1
            st.rerun()


# ── Footer ────────────────────────────────────────────────────────────────

st.markdown(
    """
    <div style="text-align:center;margin-top:3rem;padding:1.5rem;
                color:#475569;font-size:0.8rem;
                border-top:1px solid rgba(255,255,255,0.05);">
        🏦 Financial Advisor · Lloyds Banking Group · Hackathon 2026<br/>
        <span style="font-size:0.7rem;">
            All projections are illustrative and do not constitute financial advice.
        </span>
    </div>
    """,
    unsafe_allow_html=True,
)
