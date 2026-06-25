import os

from dotenv import load_dotenv

from ..observability.tool_tracer import traced_tool
from ..shared_tools.bigquery_client import bq_client, safe_select, BQ_DATASET, ECOMMERCE_DATASET

load_dotenv()


@traced_tool
def run_bigquery_query(sql: str) -> str:
    """Executes a read-only SQL query against BigQuery and returns the results.

    Use this tool for analytics or reporting questions. You can query any 
    project and dataset your service account has access to by using fully 
    qualified table names (e.g., `project.dataset.table`) in the SQL.
    
    Placeholders in the SQL are substituted automatically:
      - `{dataset}` → BQ_DATASET (bank dataset)
      - `{ecommerce_dataset}` → ECOMMERCE_DATASET

    Args:
        sql: A valid GoogleSQL SELECT statement.

    Returns:
        A plain-text table of results, or an error message if the query fails.
    """
    try:
        resolved_sql = safe_select(sql)
    except ValueError as e:
        return f"ERROR: {e}"

    try:
        client = bq_client()
        print(f"Running BigQuery query:\n{resolved_sql}")
        result_df = client.query(resolved_sql).to_dataframe()

        if result_df.empty:
            return "Query returned no results."

        return result_df.to_string(index=False)

    except Exception as e:
        return f"BigQuery Error: {str(e)}"
