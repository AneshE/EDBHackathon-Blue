"""Fetch transactions for a customer from BigQuery.

This tool is agent-agnostic — any agent that has access to the bank
BigQuery dataset can call it.
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta

from dotenv import load_dotenv
from google.cloud import bigquery

from ..observability.tool_tracer import traced_tool
from .bigquery_client import bq_client

load_dotenv()

BQ_DATASET = os.getenv("BQ_DATASET", "")


@traced_tool
def get_transactions(customer_id: str, months_back: int = 12) -> str:
    """Retrieve all transactions for a customer within a date window.

    Joins accounts → transactions so only the given customer's data is
    returned.  Results are ordered newest-first.

    Args:
        customer_id: The customer identifier (e.g. ``"C001"``).
        months_back: How many months of history to fetch (default 12).

    Returns:
        A plain-text table of transactions, or an error / empty message.
    """
    if not BQ_DATASET:
        return "ERROR: BQ_DATASET is not configured. Cannot fetch transactions."

    try:
        client = bq_client()

        cutoff = (datetime.utcnow() - timedelta(days=months_back * 30)).strftime("%Y-%m-%d")

        query = f"""
            SELECT
                t.date,
                t.description,
                t.amount,
                t.type,
                t.category,
                a.account_id,
                a.product_type
            FROM `{BQ_DATASET}.transactions` t
            JOIN `{BQ_DATASET}.accounts` a ON t.account_id = a.account_id
            WHERE a.customer_id = @customer_id
              AND t.date >= @cutoff
            ORDER BY t.date DESC
        """

        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("customer_id", "STRING", customer_id),
                bigquery.ScalarQueryParameter("cutoff", "STRING", cutoff),
            ]
        )

        result_df = client.query(query, job_config=job_config).to_dataframe()

        if result_df.empty:
            return f"No transactions found for customer {customer_id} in the last {months_back} months."

        return result_df.to_string(index=False)

    except Exception as e:
        return f"BigQuery Error: {str(e)}"
