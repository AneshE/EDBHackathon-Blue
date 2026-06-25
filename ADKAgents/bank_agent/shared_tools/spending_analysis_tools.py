"""Categorised spending analysis across configurable time intervals.

Supports: weekly, monthly, quarterly, half_yearly, annual.
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta

from dotenv import load_dotenv
from google.cloud import bigquery

from ..observability.tool_tracer import traced_tool
from .bigquery_client import bq_client
from .category_mapper import categorise

load_dotenv()

BQ_DATASET = os.getenv("BQ_DATASET", "")

# Mapping from human-friendly interval name → number of days to look back.
_INTERVAL_DAYS: dict[str, int] = {
    "weekly": 7,
    "monthly": 30,
    "quarterly": 90,
    "half_yearly": 182,
    "annual": 365,
}


@traced_tool
def analyse_spending(customer_id: str, interval: str = "monthly") -> str:
    """Analyse a customer's spending habits grouped by category.

    Fetches all debit transactions for the requested interval, maps each
    to a category (Groceries, Subscriptions, Travel, etc.), and returns
    a human-readable summary with per-category totals and percentages.

    Args:
        customer_id: The customer identifier (e.g. ``"C004"``).
        interval: One of ``weekly``, ``monthly``, ``quarterly``,
                  ``half_yearly``, or ``annual``.

    Returns:
        A formatted spending breakdown string, or an error message.
    """
    interval_key = interval.strip().lower()
    if interval_key not in _INTERVAL_DAYS:
        return (
            f"ERROR: Unknown interval '{interval}'. "
            f"Choose from: {', '.join(_INTERVAL_DAYS)}."
        )

    if not BQ_DATASET:
        return "ERROR: BQ_DATASET is not configured. Cannot analyse spending."

    days = _INTERVAL_DAYS[interval_key]
    cutoff = (datetime.utcnow() - timedelta(days=days)).strftime("%Y-%m-%d")

    try:
        client = bq_client()

        query = f"""
            SELECT
                t.date,
                t.description,
                t.amount,
                t.type,
                t.category AS stored_category
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

        df = client.query(query, job_config=job_config).to_dataframe()

        if df.empty:
            return (
                f"No transactions found for customer {customer_id} "
                f"in the last {days} days ({interval_key})."
            )

        # ── Separate debits (spending) from credits (income) ──
        debits = df[df["type"] == "debit"].copy()
        credits = df[df["type"] == "credit"].copy()

        # ── Categorise ──
        # Prefer the stored category from BQ; fall back to keyword mapper.
        def _resolve_category(row):
            stored = row.get("stored_category")
            if stored and str(stored).strip() and str(stored).strip() != "None":
                return str(stored).strip()
            return categorise(row["description"])

        if not debits.empty:
            debits["category"] = debits.apply(_resolve_category, axis=1)

        if not credits.empty:
            credits["category"] = credits.apply(_resolve_category, axis=1)

        # ── Build spending summary ──
        lines: list[str] = []
        lines.append(f"═══ Spending Analysis for {customer_id} ({interval_key}) ═══")
        lines.append(f"Period: last {days} days (since {cutoff})")
        lines.append("")

        if not debits.empty:
            # amounts are stored as negative for debits — take absolute value
            debits["abs_amount"] = debits["amount"].abs()
            total_spent = debits["abs_amount"].sum()
            category_totals = (
                debits.groupby("category")["abs_amount"]
                .agg(["sum", "count"])
                .sort_values("sum", ascending=False)
            )

            lines.append(f"TOTAL SPENDING: £{total_spent:,.2f}")
            lines.append(f"TRANSACTIONS:   {len(debits)}")
            lines.append("")
            lines.append(f"{'Category':<20} {'Amount':>12} {'Count':>7} {'% of Total':>11}")
            lines.append("─" * 52)

            for cat, row in category_totals.iterrows():
                pct = (row["sum"] / total_spent * 100) if total_spent else 0
                lines.append(
                    f"{cat:<20} £{row['sum']:>10,.2f} {int(row['count']):>7} {pct:>10.1f}%"
                )

            # ── Flag potential overspending ──
            lines.append("")
            sub_total = category_totals.loc["Subscriptions", "sum"] if "Subscriptions" in category_totals.index else 0
            if sub_total > 0:
                sub_pct = (sub_total / total_spent * 100)
                if sub_pct > 25:
                    lines.append(
                        f"⚠️  WARNING: Subscriptions account for {sub_pct:.1f}% of total spending "
                        f"(£{sub_total:,.2f}). This is unusually high — consider reviewing active subscriptions."
                    )
        else:
            lines.append("No debit (spending) transactions found in this period.")

        # ── Income summary ──
        lines.append("")
        if not credits.empty:
            total_income = credits["amount"].sum()
            lines.append(f"TOTAL INCOME:   £{total_income:,.2f}")
            lines.append(f"INCOME ITEMS:   {len(credits)}")

            if not debits.empty:
                total_spent = debits["abs_amount"].sum()
                net = total_income - total_spent
                lines.append(f"NET CASHFLOW:   £{net:,.2f}")
                if net < 0:
                    lines.append(
                        f"⚠️  WARNING: Outgoings exceed income by £{abs(net):,.2f} in this period."
                    )
        else:
            lines.append("No credit (income) transactions found in this period.")

        return "\n".join(lines)

    except Exception as e:
        return f"BigQuery Error: {str(e)}"
