"""Centralised BigQuery client and read-only query helper.

Every agent/tool that needs BigQuery should import from here instead of
creating its own ``bigquery.Client`` — this keeps project/dataset resolution,
safety checks, and placeholder substitution in one place.
"""

import os

from dotenv import load_dotenv
from google.cloud import bigquery

load_dotenv()

PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT", "")
BQ_DATASET = os.getenv("BQ_DATASET", "")
ECOMMERCE_DATASET = os.getenv("ECOMMERCE_DATASET", "ecommerce_data")

# Statements that must never reach BigQuery through agent tools.
_WRITE_KEYWORDS = frozenset(
    ["INSERT", "UPDATE", "DELETE", "DROP", "TRUNCATE", "MERGE",
     "CREATE", "ALTER", "GRANT", "REVOKE"]
)


def bq_client() -> bigquery.Client:
    """Return a BigQuery client bound to the configured project."""
    return bigquery.Client(project=PROJECT_ID if PROJECT_ID else None)


def safe_select(sql: str) -> str:
    """Validate that *sql* is a read-only SELECT, resolve placeholders,
    and return the resolved SQL string.

    Raises ``ValueError`` for write operations.
    """
    normalised = sql.strip().upper()
    for keyword in _WRITE_KEYWORDS:
        if normalised.startswith(keyword):
            raise ValueError(
                f"Write operations are not permitted. Only SELECT queries are allowed. "
                f"Rejected keyword: {keyword}"
            )

    resolved = (
        sql.replace("{dataset}", BQ_DATASET)
           .replace("{ecommerce_dataset}", ECOMMERCE_DATASET)
    )
    return resolved
