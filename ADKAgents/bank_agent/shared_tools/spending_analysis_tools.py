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
from .category_mapper import BUDGET_TARGETS
from .llm_category_mapper import categorise, classify_budget

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
        
        # Calculate income and spending totals
        total_spent = 0.0
        total_income = 0.0
        if not debits.empty:
            debits["abs_amount"] = debits["amount"].abs()
            total_spent = debits["abs_amount"].sum()
        if not credits.empty:
            total_income = credits["amount"].sum()
        
        net_cashflow = total_income - total_spent
        
        # Friendly interval title
        AUDIT_TITLES = {
            "weekly": "Weekly Spending Audit",
            "monthly": "Monthly Spending Audit",
            "quarterly": "Quarterly Spending Audit",
            "half_yearly": "Half-Yearly Spending Audit",
            "annual": "Annual Spending Audit",
        }
        title = AUDIT_TITLES.get(interval_key, f"{interval_key.capitalize()} Spending Audit")
        
        lines.append(f"### 📊 {title}")
        lines.append(f"Total Income: **£{total_income:,.2f}** | Total Spending: **£{total_spent:,.2f}** | Net Cashflow: **£{net_cashflow:,.2f}**")
        lines.append("")

        CATEGORY_EMOJIS = {
            "Groceries": "🛒",
            "Incoming Salary": "💰",
            "Travel": "🚗",
            "Interest": "📈",
            "Subscriptions": "📺",
            "Rent": "🏠",
            "Tax": "💸",
            "Others": "🛍️",
        }

        if not debits.empty:
            category_totals = (
                debits.groupby("category")["abs_amount"]
                .agg(["sum", "count"])
                .sort_values("sum", ascending=False)
            )

            lines.append("| Category | Amount | Count | % of Total |")
            lines.append("| :--- | :--- | :--- | :--- |")

            for cat, row in category_totals.iterrows():
                pct = (row["sum"] / total_spent * 100) if total_spent else 0
                amt_str = f"£{row['sum']:,.2f}"
                pct_str = f"{pct:.1f}%"
                emoji = CATEGORY_EMOJIS.get(str(cat), "🛍️")
                lines.append(
                    f"| {emoji} **{cat}** | {amt_str} | {int(row['count'])} | {pct_str} |"
                )

            # ── Flag potential overspending ──
            sub_total = category_totals.loc["Subscriptions", "sum"] if "Subscriptions" in category_totals.index else 0
            if sub_total > 0:
                sub_pct = (sub_total / total_spent * 100)
                if sub_pct > 25:
                    lines.append("")
                    lines.append(
                        f"⚠️ **WARNING**: Subscriptions account for **{sub_pct:.1f}%** of total spending "
                        f"(**£{sub_total:,.2f}**). This is unusually high — consider reviewing active subscriptions."
                    )
        else:
            lines.append("No debit (spending) transactions found in this period.")

        if not credits.empty and not debits.empty:
            if net_cashflow < 0:
                lines.append("")
                lines.append(
                    f"⚠️ **WARNING**: Outgoings exceed income by **£{abs(net_cashflow):,.2f}** in this period."
                )

        # ── 50 / 30 / 20 Budget Ratio Analysis ──
        if not debits.empty and not credits.empty:
            # Classify each category into budget buckets
            debits["budget_bucket"] = debits["category"].apply(classify_budget)
            bucket_totals: dict[str, float] = {}
            for bucket in ("Needs", "Wants", "Savings"):
                bucket_df = debits[debits["budget_bucket"] == bucket]
                bucket_totals[bucket] = bucket_df["abs_amount"].sum() if not bucket_df.empty else 0.0

            lines.append("")
            lines.append("### ⚖️ 50/30/20 Budget Status")
            lines.append("")
            lines.append(
                f"This analysis uses your total income of **£{total_income:,.2f}** as the baseline "
                f"for the comparison (50% Needs, 30% Wants, 20% Savings)."
            )
            lines.append("")
            lines.append("| Bucket | Actual £ | Actual % | Target % | Status |")
            lines.append("| :--- | :--- | :--- | :--- | :--- |")

            for bucket in ("Needs", "Wants", "Savings"):
                amount = bucket_totals[bucket]
                actual_pct = (amount / total_income * 100) if total_income else 0
                target_pct = BUDGET_TARGETS[bucket]
                diff = actual_pct - target_pct

                if bucket == "Savings":
                    if abs(diff) <= 5:
                        status = "✅ On track"
                    elif diff < -5:
                        status = "⚠️ Under"
                    else:
                        status = "🟢 Above"
                else:
                    if abs(diff) <= 5:
                        status = "✅ On track"
                    elif diff > 5:
                        status = "⚠️ Over"
                    else:
                        status = "🟢 Under"

                amount_str = f"£{amount:,.2f}"
                actual_pct_str = f"{actual_pct:.1f}%"
                target_pct_str = f"{target_pct:.1f}%"
                lines.append(
                    f"| **{bucket}** | {amount_str} | {actual_pct_str} | {target_pct_str} | {status} |"
                )

            lines.append("")
            # Provide a summary verdict
            needs_pct = (bucket_totals['Needs'] / total_income * 100) if total_income else 0
            wants_pct = (bucket_totals['Wants'] / total_income * 100) if total_income else 0
            savings_pct = (bucket_totals['Savings'] / total_income * 100) if total_income else 0

            if needs_pct > 55:
                lines.append(
                    f"💡 **INSIGHT**: Your essential spending (Needs) is at **{needs_pct:.1f}%**, "
                    f"exceeding the recommended 50%. Consider reviewing fixed costs like rent or travel."
                )
            if wants_pct > 35:
                lines.append(
                    f"💡 **INSIGHT**: Your discretionary spending (Wants) is at **{wants_pct:.1f}%**, "
                    f"above the recommended 30%. Subscriptions and lifestyle spending may need trimming."
                )
            if savings_pct < 15:
                lines.append(
                    f"💡 **INSIGHT**: Your savings/investments allocation is only **{savings_pct:.1f}%**, "
                    f"below the recommended 20%. Try to increase savings contributions."
                )
            if needs_pct <= 55 and wants_pct <= 35 and savings_pct >= 15:
                lines.append(
                    "✅ **VERDICT**: Your budget is well-balanced and aligns with the 50/30/20 golden rule. Keep it up!"
                )

        return "\n".join(lines)

    except Exception as e:
        return f"BigQuery Error: {str(e)}"
