"""Shared tools — reusable across all agents in the project.

Exports:
    bq_client           — pre-configured BigQuery client factory
    safe_select         — read-only SQL guard + placeholder resolution
    categorise          — map a transaction description to a spending category
    get_transactions    — fetch transactions for a customer from BigQuery
    analyse_spending    — categorised spending breakdown by time interval
"""

from .bigquery_client import bq_client, safe_select
from .category_mapper import categorise, CATEGORIES
from .transaction_tools import get_transactions
from .spending_analysis_tools import analyse_spending

__all__ = [
    "bq_client",
    "safe_select",
    "categorise",
    "CATEGORIES",
    "get_transactions",
    "analyse_spending",
]
