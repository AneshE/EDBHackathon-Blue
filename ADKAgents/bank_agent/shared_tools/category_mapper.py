"""Map transaction descriptions to spending categories.

Pure Python — no GCP dependency — so it is fast, deterministic, and
trivially unit-testable.

Categories
----------
    Groceries, Incoming Salary, Travel, Interest, Subscriptions,
    Rent, Tax, Others
"""

from __future__ import annotations

CATEGORIES = (
    "Groceries",
    "Incoming Salary",
    "Travel",
    "Interest",
    "Subscriptions",
    "Rent",
    "Tax",
    "Others",
)

# Mapping: lowercased keyword/phrase → category.
# Order matters — we scan sequentially and take the first match.
# Longer / more specific keywords should precede shorter ambiguous ones.
_KEYWORD_MAP: list[tuple[str, str]] = [
    # ── Groceries ──────────────────────────────────────────────
    ("tesco", "Groceries"),
    ("sainsbury", "Groceries"),
    ("aldi", "Groceries"),
    ("lidl", "Groceries"),
    ("waitrose", "Groceries"),
    ("asda", "Groceries"),
    ("morrisons", "Groceries"),
    ("co-op", "Groceries"),
    ("supermarket", "Groceries"),
    ("grocery", "Groceries"),
    ("marks & spencer food", "Groceries"),
    ("m&s food", "Groceries"),
    ("ocado", "Groceries"),

    # ── Incoming Salary ────────────────────────────────────────
    ("salary", "Incoming Salary"),
    ("payroll", "Incoming Salary"),
    ("freelance invoice", "Incoming Salary"),
    ("pension", "Incoming Salary"),
    ("wages", "Incoming Salary"),
    ("isa transfer", "Incoming Salary"),

    # ── Subscriptions (before Travel — "netflix" contains "tfl") ──
    ("netflix", "Subscriptions"),
    ("spotify", "Subscriptions"),
    ("disney+", "Subscriptions"),
    ("disney plus", "Subscriptions"),
    ("amazon prime", "Subscriptions"),
    ("apple music", "Subscriptions"),
    ("youtube premium", "Subscriptions"),
    ("deliveroo plus", "Subscriptions"),
    ("deliveroo", "Subscriptions"),
    ("gym membership", "Subscriptions"),
    ("streaming service", "Subscriptions"),
    ("apple tv", "Subscriptions"),
    ("now tv", "Subscriptions"),
    ("audible", "Subscriptions"),
    ("xbox game pass", "Subscriptions"),
    ("playstation plus", "Subscriptions"),
    ("adobe", "Subscriptions"),

    # ── Interest ───────────────────────────────────────────────
    ("interest payment", "Interest"),
    ("interest paid", "Interest"),
    ("savings interest", "Interest"),
    ("isa interest", "Interest"),
    ("interest earned", "Interest"),

    # ── Travel ─────────────────────────────────────────────────
    ("uber", "Travel"),
    ("tfl ", "Travel"),
    ("tfl oyster", "Travel"),
    ("oyster", "Travel"),
    ("national rail", "Travel"),
    ("trainline", "Travel"),
    ("british airways", "Travel"),
    ("easyjet", "Travel"),
    ("ryanair", "Travel"),
    ("holiday booking", "Travel"),
    ("hotel", "Travel"),
    ("booking.com", "Travel"),
    ("airbnb", "Travel"),
    ("petrol", "Travel"),
    ("shell fuel", "Travel"),
    ("bp fuel", "Travel"),

    # ── Rent ───────────────────────────────────────────────────
    ("mortgage payment", "Rent"),
    ("mortgage", "Rent"),
    ("rent", "Rent"),
    ("letting agent", "Rent"),
    ("housing association", "Rent"),

    # ── Tax ────────────────────────────────────────────────────
    ("council tax", "Tax"),
    ("hmrc", "Tax"),
    ("income tax", "Tax"),
    ("self assessment", "Tax"),
    ("vat payment", "Tax"),
    ("national insurance", "Tax"),
    ("tax refund", "Tax"),
]



# ── 50 / 30 / 20 Budget Classification ────────────────────────────────────
# Maps each spending category to one of the three budget buckets used in the
# popular "50/30/20" budgeting rule:
#   Needs (50%)  — essential living costs
#   Wants (30%)  — discretionary / lifestyle spending
#   Savings (20%) — savings, investments, debt repayment
#
# "Incoming Salary" is income, not spending, so it is excluded from the
# classification but is used as the denominator when calculating ratios.
BUDGET_CLASSIFICATION: dict[str, str] = {
    "Groceries": "Needs",
    "Rent": "Needs",
    "Tax": "Needs",
    "Travel": "Needs",
    "Subscriptions": "Wants",
    "Others": "Wants",
    "Interest": "Savings",
    "Incoming Salary": "Income",
}

BUDGET_TARGETS: dict[str, float] = {
    "Needs": 50.0,
    "Wants": 30.0,
    "Savings": 20.0,
}


def classify_budget(category: str) -> str:
    """Map a spending *category* to a budget bucket (Needs / Wants / Savings).

    >>> classify_budget("Groceries")
    'Needs'
    >>> classify_budget("Subscriptions")
    'Wants'
    >>> classify_budget("Interest")
    'Savings'
    """
    return BUDGET_CLASSIFICATION.get(category, "Wants")


def categorise(description: str) -> str:
    """Return the spending category for a transaction *description*.

    Falls back to ``"Others"`` when no keyword matches.

    >>> categorise("Tesco Express")
    'Groceries'
    >>> categorise("Netflix Monthly")
    'Subscriptions'
    >>> categorise("Random shop")
    'Others'
    """
    desc_lower = description.lower()
    for keyword, category in _KEYWORD_MAP:
        if keyword in desc_lower:
            return category
    return "Others"
