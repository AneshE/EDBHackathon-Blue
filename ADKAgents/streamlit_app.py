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
import json
import datetime
import requests
import streamlit as st
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
if "advisor_data" not in st.session_state:
    st.session_state.advisor_data = None
if "perk_choice" not in st.session_state:
    st.session_state.perk_choice = None
if "demo_mode" not in st.session_state:
    st.session_state.demo_mode = False


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

render_stepper(st.session_state.current_step)

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

    st.markdown('<div class="glass-card">', unsafe_allow_html=True)

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

    st.markdown("</div>", unsafe_allow_html=True)

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

                    # Now fetch advisor data
                    with st.spinner("Analysing your financial data..."):
                        st.session_state.advisor_data = call_advisor(
                            customer_id, full_name, dob_str
                        )

                    st.success(f"✅ {result.get('message', 'Identity verified!')}")
                    st.session_state.current_step = 1
                    st.rerun()
                else:
                    st.error(f"❌ {result.get('message', 'Verification failed.')}")


# ══════════════════════════════════════════════════════════════════════════
# STEP 2 — BUDGET BLUEPRINT
# ══════════════════════════════════════════════════════════════════════════

elif st.session_state.current_step == 1:
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
        if st.button("Continue to Perk Optimization →", use_container_width=True, key="btn_step2"):
            st.session_state.current_step = 2
            st.rerun()


# ══════════════════════════════════════════════════════════════════════════
# STEP 3 — PERK OPTIMIZATION
# ══════════════════════════════════════════════════════════════════════════

elif st.session_state.current_step == 2:
    perk = get_step_data("perk_optimization")
    if not perk:
        perk = DEMO_DATA["ui_steps"][1]

    st.markdown(
        f'<div class="section-title">{perk["title"]}</div>'
        f'<div class="section-subtitle">Smart actions to optimise your spending</div>',
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

    col_back, col_spacer, col_next = st.columns([1, 1, 1])
    with col_back:
        if st.button("← Back to Blueprint", use_container_width=True, key="btn_back_step2"):
            st.session_state.current_step = 1
            st.rerun()
    with col_next:
        if st.button("Continue to Growth Plan →", use_container_width=True, key="btn_step3"):
            st.session_state.perk_choice = choice
            st.session_state.current_step = 3
            st.rerun()


# ══════════════════════════════════════════════════════════════════════════
# STEP 4 — WEALTH GROWTH PLAN
# ══════════════════════════════════════════════════════════════════════════

elif st.session_state.current_step == 3:
    growth = get_step_data("wealth_growth_plan")
    if not growth:
        growth = DEMO_DATA["ui_steps"][2]

    st.markdown(
        f'<div class="section-title">{growth["title"]}</div>'
        f'<div class="section-subtitle">Your personalised wealth building roadmap</div>',
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
            <div style="display:flex;align-items:center;gap:0.75rem;margin-bottom:1rem;">
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

    col_back, col_spacer, col_restart = st.columns([1, 1, 1])
    with col_back:
        if st.button("← Back to Perks", use_container_width=True, key="btn_back_step3"):
            st.session_state.current_step = 2
            st.rerun()
    with col_restart:
        if st.button("🔄 Start Over", use_container_width=True, key="btn_restart"):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
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
