"""Integration tests for the spending analysis tools.

These tests mock the BigQuery client so they can run without GCP credentials.

Run with:
    pytest eval/test_spending_analysis.py -v
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest


# ── Sample transaction data ──────────────────────────────────────────────────

_SAMPLE_TRANSACTIONS = pd.DataFrame([
    {"date": "2026-06-01", "description": "Salary - Acme Corp",  "amount": 3200.00,  "type": "credit", "stored_category": "Incoming Salary"},
    {"date": "2026-06-05", "description": "Tesco Weekly Shop",   "amount": -52.30,   "type": "debit",  "stored_category": "Groceries"},
    {"date": "2026-06-08", "description": "Netflix Monthly",     "amount": -15.99,   "type": "debit",  "stored_category": "Subscriptions"},
    {"date": "2026-06-10", "description": "Council Tax",         "amount": -145.00,  "type": "debit",  "stored_category": "Tax"},
    {"date": "2026-06-14", "description": "TfL Oyster Top-Up",   "amount": -40.00,   "type": "debit",  "stored_category": "Travel"},
    {"date": "2026-06-20", "description": "Electricity Bill",    "amount": -82.50,   "type": "debit",  "stored_category": "Others"},
    {"date": "2026-06-01", "description": "Rent",                "amount": -950.00,  "type": "debit",  "stored_category": "Rent"},
])

_EMPTY_DF = pd.DataFrame()

_C004_HEAVY_SUBS = pd.DataFrame([
    {"date": "2026-06-01", "description": "Pension",             "amount": 1200.00,  "type": "credit", "stored_category": "Incoming Salary"},
    {"date": "2026-06-01", "description": "Deliveroo Plus",      "amount": -11.99,   "type": "debit",  "stored_category": "Subscriptions"},
    {"date": "2026-06-02", "description": "Disney+",             "amount": -10.99,   "type": "debit",  "stored_category": "Subscriptions"},
    {"date": "2026-06-03", "description": "Netflix",             "amount": -15.99,   "type": "debit",  "stored_category": "Subscriptions"},
    {"date": "2026-06-03", "description": "Spotify Premium",     "amount": -10.99,   "type": "debit",  "stored_category": "Subscriptions"},
    {"date": "2026-06-04", "description": "Amazon Prime",        "amount": -8.99,    "type": "debit",  "stored_category": "Subscriptions"},
    {"date": "2026-06-04", "description": "Apple Music",         "amount": -10.99,   "type": "debit",  "stored_category": "Subscriptions"},
    {"date": "2026-06-08", "description": "Deliveroo Order",     "amount": -33.50,   "type": "debit",  "stored_category": "Subscriptions"},
    {"date": "2026-06-15", "description": "Deliveroo Order",     "amount": -28.70,   "type": "debit",  "stored_category": "Subscriptions"},
    {"date": "2026-06-15", "description": "Gym Membership",      "amount": -35.00,   "type": "debit",  "stored_category": "Subscriptions"},
    {"date": "2026-06-09", "description": "Supermarket",         "amount": -67.30,   "type": "debit",  "stored_category": "Groceries"},
])


def _mock_bq_query(df: pd.DataFrame):
    """Return a mock BigQuery client whose .query().to_dataframe() returns *df*."""
    mock_client = MagicMock()
    mock_query_job = MagicMock()
    mock_query_job.to_dataframe.return_value = df
    mock_client.query.return_value = mock_query_job
    return mock_client


class TestAnalyseSpending:
    """Tests for the analyse_spending tool."""

    @patch("bank_agent.shared_tools.spending_analysis_tools.BQ_DATASET", "test_dataset")
    @patch("bank_agent.shared_tools.spending_analysis_tools.bq_client")
    def test_monthly_breakdown_includes_all_categories(self, mock_bq_client_fn):
        from bank_agent.shared_tools.spending_analysis_tools import analyse_spending

        mock_bq_client_fn.return_value = _mock_bq_query(_SAMPLE_TRANSACTIONS)

        result = analyse_spending(customer_id="C001", interval="monthly")

        assert "Groceries" in result
        assert "Tax" in result
        assert "Subscriptions" in result
        assert "Travel" in result
        assert "Rent" in result
        assert "Others" in result
        assert "Total Spending" in result

    @patch("bank_agent.shared_tools.spending_analysis_tools.BQ_DATASET", "test_dataset")
    @patch("bank_agent.shared_tools.spending_analysis_tools.bq_client")
    def test_income_section_present(self, mock_bq_client_fn):
        from bank_agent.shared_tools.spending_analysis_tools import analyse_spending

        mock_bq_client_fn.return_value = _mock_bq_query(_SAMPLE_TRANSACTIONS)

        result = analyse_spending(customer_id="C001", interval="monthly")

        assert "Total Income" in result
        assert "£3,200.00" in result

    @patch("bank_agent.shared_tools.spending_analysis_tools.BQ_DATASET", "test_dataset")
    @patch("bank_agent.shared_tools.spending_analysis_tools.bq_client")
    def test_empty_transactions(self, mock_bq_client_fn):
        from bank_agent.shared_tools.spending_analysis_tools import analyse_spending

        mock_bq_client_fn.return_value = _mock_bq_query(_EMPTY_DF)

        result = analyse_spending(customer_id="C999", interval="monthly")

        assert "No transactions found" in result

    @patch("bank_agent.shared_tools.spending_analysis_tools.BQ_DATASET", "test_dataset")
    @patch("bank_agent.shared_tools.spending_analysis_tools.bq_client")
    def test_subscription_overspending_warning(self, mock_bq_client_fn):
        from bank_agent.shared_tools.spending_analysis_tools import analyse_spending

        mock_bq_client_fn.return_value = _mock_bq_query(_C004_HEAVY_SUBS)

        result = analyse_spending(customer_id="C004", interval="monthly")

        # Subscriptions should dominate and trigger the warning
        assert "WARNING" in result
        assert "Subscriptions" in result

    @patch("bank_agent.shared_tools.spending_analysis_tools.BQ_DATASET", "test_dataset")
    @patch("bank_agent.shared_tools.spending_analysis_tools.bq_client")
    def test_net_cashflow_negative_warning(self, mock_bq_client_fn):
        from bank_agent.shared_tools.spending_analysis_tools import analyse_spending

        # Income 1200, spending ~234 in subs + 67.30 groceries = ~301 — actually positive
        # Let's modify to make spending exceed income
        heavy_spend = _C004_HEAVY_SUBS.copy()
        heavy_spend.loc[heavy_spend["type"] == "credit", "amount"] = 100.0  # tiny income

        mock_bq_client_fn.return_value = _mock_bq_query(heavy_spend)

        result = analyse_spending(customer_id="C004", interval="monthly")

        assert "Outgoings exceed income" in result

    def test_invalid_interval(self):
        from bank_agent.shared_tools.spending_analysis_tools import analyse_spending

        result = analyse_spending(customer_id="C001", interval="biweekly")

        assert "ERROR" in result
        assert "Unknown interval" in result

    @patch("bank_agent.shared_tools.spending_analysis_tools.BQ_DATASET", "")
    def test_no_dataset_configured(self):
        from bank_agent.shared_tools.spending_analysis_tools import analyse_spending

        result = analyse_spending(customer_id="C001", interval="monthly")

        assert "ERROR" in result
        assert "BQ_DATASET" in result


class TestGetTransactions:
    """Tests for the get_transactions tool."""

    @patch("bank_agent.shared_tools.transaction_tools.BQ_DATASET", "test_dataset")
    @patch("bank_agent.shared_tools.transaction_tools.bq_client")
    def test_returns_transaction_table(self, mock_bq_client_fn):
        from bank_agent.shared_tools.transaction_tools import get_transactions

        mock_bq_client_fn.return_value = _mock_bq_query(
            pd.DataFrame([
                {"date": "2026-06-01", "description": "Tesco", "amount": -50.0,
                 "type": "debit", "category": "Groceries", "account_id": "A001",
                 "product_type": "Current Account"},
            ])
        )

        result = get_transactions(customer_id="C001", months_back=6)

        assert "Tesco" in result
        assert "Groceries" in result

    @patch("bank_agent.shared_tools.transaction_tools.BQ_DATASET", "test_dataset")
    @patch("bank_agent.shared_tools.transaction_tools.bq_client")
    def test_empty_result(self, mock_bq_client_fn):
        from bank_agent.shared_tools.transaction_tools import get_transactions

        mock_bq_client_fn.return_value = _mock_bq_query(_EMPTY_DF)

        result = get_transactions(customer_id="C999", months_back=6)

        assert "No transactions found" in result

    @patch("bank_agent.shared_tools.transaction_tools.BQ_DATASET", "")
    def test_no_dataset_configured(self):
        from bank_agent.shared_tools.transaction_tools import get_transactions

        result = get_transactions(customer_id="C001")

        assert "ERROR" in result
        assert "BQ_DATASET" in result


class TestIntervalDays:
    """Verify that all supported intervals are correctly mapped."""

    def test_all_intervals_accepted(self):
        from bank_agent.shared_tools.spending_analysis_tools import _INTERVAL_DAYS

        assert "weekly" in _INTERVAL_DAYS
        assert "monthly" in _INTERVAL_DAYS
        assert "quarterly" in _INTERVAL_DAYS
        assert "half_yearly" in _INTERVAL_DAYS
        assert "annual" in _INTERVAL_DAYS

    def test_interval_day_counts(self):
        from bank_agent.shared_tools.spending_analysis_tools import _INTERVAL_DAYS

        assert _INTERVAL_DAYS["weekly"] == 7
        assert _INTERVAL_DAYS["monthly"] == 30
        assert _INTERVAL_DAYS["quarterly"] == 90
        assert _INTERVAL_DAYS["half_yearly"] == 182
        assert _INTERVAL_DAYS["annual"] == 365
