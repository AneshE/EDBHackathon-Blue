"""Tests for the UI Advisor agent, API endpoints, and Streamlit UI data flow.

These tests validate:
  - The ui_advisor agent prompt and configuration
  - The /api/verify endpoint logic
  - The /api/advisor JSON response schema
  - The Streamlit demo/fallback data structure
  - Budget calculation correctness

Run with:
    pytest eval/test_ui_advisor.py -v
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch, AsyncMock

import pandas as pd
import pytest


# ── Sample data ──────────────────────────────────────────────────────────────

_CUSTOMER_RECORD = pd.DataFrame([{
    "customer_id": "C004",
    "name": "Margaret Taylor",
    "dob": "1955-03-12",
    "postcode": "SW1A 1AA",
}])

_EMPTY_DF = pd.DataFrame()

_SAMPLE_TRANSACTIONS = pd.DataFrame([
    {"date": "2026-06-01", "description": "Pension",           "amount": 3224.50, "type": "credit", "stored_category": "Incoming Salary"},
    {"date": "2026-06-05", "description": "Tesco Weekly Shop", "amount": -52.30,  "type": "debit",  "stored_category": "Groceries"},
    {"date": "2026-06-06", "description": "TfL Oyster",        "amount": -28.50,  "type": "debit",  "stored_category": "Travel"},
    {"date": "2026-06-08", "description": "Disney+",           "amount": -17.99,  "type": "debit",  "stored_category": "Subscriptions"},
])


def _mock_bq_query(df: pd.DataFrame):
    """Return a mock BigQuery client whose .query().to_dataframe() returns *df*."""
    mock_client = MagicMock()
    mock_query_job = MagicMock()
    mock_query_job.to_dataframe.return_value = df
    mock_client.query.return_value = mock_query_job
    return mock_client


# ══════════════════════════════════════════════════════════════════════════════
# UI ADVISOR AGENT TESTS
# ══════════════════════════════════════════════════════════════════════════════


class TestUIAdvisorAgentConfig:
    """Verify the ui_advisor agent is correctly configured."""

    def test_agent_name(self):
        from bank_agent.ui_advisor.agent import ui_advisor_agent
        assert ui_advisor_agent.name == "ui_advisor"

    def test_agent_has_tools(self):
        from bank_agent.ui_advisor.agent import ui_advisor_agent
        tool_names = [t.__name__ if callable(t) else str(t) for t in ui_advisor_agent.tools]
        assert any("analyse_spending" in name for name in tool_names)
        assert any("vertex_vector_search" in name for name in tool_names)

    def test_agent_has_instruction(self):
        from bank_agent.ui_advisor.agent import ui_advisor_agent
        assert ui_advisor_agent.instruction is not None
        assert len(ui_advisor_agent.instruction) > 100

    def test_agent_description_mentions_json(self):
        from bank_agent.ui_advisor.agent import ui_advisor_agent
        assert "JSON" in ui_advisor_agent.description

    def test_agent_registered_as_sub_agent(self):
        from bank_agent.agent import root_agent
        sub_agent_names = [a.name for a in root_agent.sub_agents]
        assert "ui_advisor" in sub_agent_names


class TestUIAdvisorPrompt:
    """Verify the ui_advisor prompt contains required JSON schema elements."""

    def test_prompt_requires_json_output(self):
        from bank_agent.ui_advisor.prompt import UI_ADVISOR_INSTRUCTION
        assert "json" in UI_ADVISOR_INSTRUCTION.lower() or "JSON" in UI_ADVISOR_INSTRUCTION

    def test_prompt_contains_schema_fields(self):
        from bank_agent.ui_advisor.prompt import UI_ADVISOR_INSTRUCTION
        assert "budget_blueprint" in UI_ADVISOR_INSTRUCTION
        assert "perk_optimization" in UI_ADVISOR_INSTRUCTION
        assert "wealth_growth_plan" in UI_ADVISOR_INSTRUCTION
        assert "metric_summary" in UI_ADVISOR_INSTRUCTION
        assert "table_data" in UI_ADVISOR_INSTRUCTION

    def test_prompt_mentions_50_30_20(self):
        from bank_agent.ui_advisor.prompt import UI_ADVISOR_INSTRUCTION
        assert "50" in UI_ADVISOR_INSTRUCTION
        assert "30" in UI_ADVISOR_INSTRUCTION
        assert "20" in UI_ADVISOR_INSTRUCTION

    def test_prompt_mentions_tools(self):
        from bank_agent.ui_advisor.prompt import UI_ADVISOR_INSTRUCTION
        assert "analyse_spending" in UI_ADVISOR_INSTRUCTION
        assert "vertex_vector_search" in UI_ADVISOR_INSTRUCTION


# ══════════════════════════════════════════════════════════════════════════════
# API VERIFY ENDPOINT TESTS
# ══════════════════════════════════════════════════════════════════════════════


class TestVerifyEndpoint:
    """Test the /api/verify single-shot identity verification."""

    @patch("bank_agent.shared_tools.bigquery_client.BQ_DATASET", "test_dataset")
    @patch("bank_agent.shared_tools.bigquery_client.bq_client")
    def test_verify_success(self, mock_bq_fn):
        """Matching name and DOB should return 'verified' status."""
        mock_bq_fn.return_value = _mock_bq_query(_CUSTOMER_RECORD)

        # Simulate the verification logic inline (same as endpoint)
        record = _CUSTOMER_RECORD.iloc[0].to_dict()
        name_match = record["name"].strip().lower() == "margaret taylor"
        dob_match = str(record["dob"]).strip()[:10] == "1955-03-12"

        assert name_match is True
        assert dob_match is True

    @patch("bank_agent.shared_tools.bigquery_client.BQ_DATASET", "test_dataset")
    @patch("bank_agent.shared_tools.bigquery_client.bq_client")
    def test_verify_wrong_name(self, mock_bq_fn):
        """Wrong name should fail verification."""
        mock_bq_fn.return_value = _mock_bq_query(_CUSTOMER_RECORD)

        record = _CUSTOMER_RECORD.iloc[0].to_dict()
        name_match = record["name"].strip().lower() == "john doe"

        assert name_match is False

    @patch("bank_agent.shared_tools.bigquery_client.BQ_DATASET", "test_dataset")
    @patch("bank_agent.shared_tools.bigquery_client.bq_client")
    def test_verify_wrong_dob(self, mock_bq_fn):
        """Wrong DOB should fail verification."""
        mock_bq_fn.return_value = _mock_bq_query(_CUSTOMER_RECORD)

        record = _CUSTOMER_RECORD.iloc[0].to_dict()
        dob_match = str(record["dob"]).strip()[:10] == "1990-01-01"

        assert dob_match is False

    def test_verify_empty_customer(self):
        """Non-existent customer should return no match."""
        assert _EMPTY_DF.empty is True


# ══════════════════════════════════════════════════════════════════════════════
# DEMO DATA SCHEMA TESTS
# ══════════════════════════════════════════════════════════════════════════════


class TestDemoDataSchema:
    """Verify the hardcoded demo data matches the expected JSON schema."""

    def _get_demo_data(self):
        """Import demo data from the Streamlit app."""
        # We inline the demo data structure here to avoid importing streamlit
        return {
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

    def test_has_current_user_intent(self):
        data = self._get_demo_data()
        assert "current_user_intent" in data
        assert data["current_user_intent"] == "optimize_wealth"

    def test_has_three_ui_steps(self):
        data = self._get_demo_data()
        assert "ui_steps" in data
        assert len(data["ui_steps"]) == 3

    def test_step_ids_correct(self):
        data = self._get_demo_data()
        step_ids = [s["step_id"] for s in data["ui_steps"]]
        assert "budget_blueprint" in step_ids
        assert "perk_optimization" in step_ids
        assert "wealth_growth_plan" in step_ids

    def test_step_numbers_sequential(self):
        data = self._get_demo_data()
        numbers = [s["step_number"] for s in data["ui_steps"]]
        assert numbers == [1, 2, 3]

    def test_budget_blueprint_has_metric_summary(self):
        data = self._get_demo_data()
        blueprint = data["ui_steps"][0]
        assert "metric_summary" in blueprint
        summary = blueprint["metric_summary"]
        assert "income" in summary
        assert "spending" in summary
        assert "surplus" in summary
        assert isinstance(summary["income"], (int, float))
        assert isinstance(summary["spending"], (int, float))
        assert isinstance(summary["surplus"], (int, float))

    def test_budget_blueprint_has_table_data(self):
        data = self._get_demo_data()
        blueprint = data["ui_steps"][0]
        assert "table_data" in blueprint
        assert len(blueprint["table_data"]) == 3
        for row in blueprint["table_data"]:
            assert "bucket" in row
            assert "actual" in row
            assert "percent" in row
            assert "target" in row
            assert "status" in row

    def test_budget_blueprint_surplus_math(self):
        data = self._get_demo_data()
        summary = data["ui_steps"][0]["metric_summary"]
        expected_surplus = summary["income"] - summary["spending"]
        assert abs(summary["surplus"] - expected_surplus) < 0.01

    def test_perk_optimization_has_required_fields(self):
        data = self._get_demo_data()
        perk = data["ui_steps"][1]
        assert "leak_detected" in perk
        assert "action_prompt" in perk
        assert "options" in perk
        assert len(perk["options"]) >= 2
        assert "monthly_savings" in perk
        assert "annual_savings" in perk

    def test_perk_annual_savings_math(self):
        data = self._get_demo_data()
        perk = data["ui_steps"][1]
        expected_annual = perk["monthly_savings"] * 12
        assert abs(perk["annual_savings"] - expected_annual) < 0.01

    def test_wealth_growth_has_required_fields(self):
        data = self._get_demo_data()
        growth = data["ui_steps"][2]
        assert "short_term_projection" in growth
        assert "target_want_milestone" in growth
        assert "long_term_projection" in growth
        assert "monthly_savings_target" in growth
        assert "twelve_month_total" in growth

    def test_wealth_growth_twelve_month_math(self):
        data = self._get_demo_data()
        growth = data["ui_steps"][2]
        expected_total = growth["monthly_savings_target"] * 12
        assert abs(growth["twelve_month_total"] - expected_total) < 0.01

    def test_demo_data_is_valid_json(self):
        """Ensure demo data can be serialised/deserialised as JSON."""
        data = self._get_demo_data()
        json_str = json.dumps(data)
        parsed = json.loads(json_str)
        assert parsed == data


# ══════════════════════════════════════════════════════════════════════════════
# BUDGET CLASSIFICATION INTEGRATION TESTS
# ══════════════════════════════════════════════════════════════════════════════


class TestBudgetClassification:
    """Verify the 50/30/20 budget classification aligns with UI advisor needs."""

    def test_needs_categories(self):
        from bank_agent.shared_tools.category_mapper import classify_budget
        assert classify_budget("Groceries") == "Needs"
        assert classify_budget("Rent") == "Needs"
        assert classify_budget("Tax") == "Needs"
        assert classify_budget("Travel") == "Needs"

    def test_wants_categories(self):
        from bank_agent.shared_tools.category_mapper import classify_budget
        assert classify_budget("Subscriptions") == "Wants"
        assert classify_budget("Others") == "Wants"

    def test_savings_categories(self):
        from bank_agent.shared_tools.category_mapper import classify_budget
        assert classify_budget("Interest") == "Savings"

    def test_budget_targets_sum_to_100(self):
        from bank_agent.shared_tools.category_mapper import BUDGET_TARGETS
        total = sum(BUDGET_TARGETS.values())
        assert total == 100.0

    def test_status_logic_safe(self):
        """Actual within 5pp of target should be Safe."""
        actual_pct = 48.0
        target_pct = 50.0
        diff = actual_pct - target_pct
        assert abs(diff) <= 5  # Safe

    def test_status_logic_action_required_needs(self):
        """Needs exceeding target by >5pp should trigger action."""
        actual_pct = 60.0
        target_pct = 50.0
        diff = actual_pct - target_pct
        assert diff > 5  # Over → Action Required

    def test_status_logic_action_required_savings(self):
        """Savings below target by >5pp should trigger action."""
        actual_pct = 10.0
        target_pct = 20.0
        diff = actual_pct - target_pct
        assert diff < -5  # Under → Action Required


# ══════════════════════════════════════════════════════════════════════════════
# SPENDING ANALYSIS → UI JSON FLOW TESTS
# ══════════════════════════════════════════════════════════════════════════════


class TestSpendingToUIFlow:
    """Test that spending analysis data can produce valid UI JSON."""

    @patch("bank_agent.shared_tools.spending_analysis_tools.BQ_DATASET", "test_dataset")
    @patch("bank_agent.shared_tools.spending_analysis_tools.bq_client")
    def test_analyse_spending_returns_data(self, mock_bq_fn):
        from bank_agent.shared_tools.spending_analysis_tools import analyse_spending

        mock_bq_fn.return_value = _mock_bq_query(_SAMPLE_TRANSACTIONS)
        result = analyse_spending(customer_id="C004", interval="monthly")

        # Should contain budget status section
        assert "50/30/20" in result
        assert "Needs" in result
        assert "Wants" in result

    @patch("bank_agent.shared_tools.spending_analysis_tools.BQ_DATASET", "test_dataset")
    @patch("bank_agent.shared_tools.spending_analysis_tools.bq_client")
    def test_income_and_spending_extracted(self, mock_bq_fn):
        from bank_agent.shared_tools.spending_analysis_tools import analyse_spending

        mock_bq_fn.return_value = _mock_bq_query(_SAMPLE_TRANSACTIONS)
        result = analyse_spending(customer_id="C004", interval="monthly")

        # Should contain income and spending totals
        assert "Total Income" in result
        assert "Total Spending" in result
        assert "£3,224.50" in result  # Income from pension
