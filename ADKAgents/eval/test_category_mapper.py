"""Unit tests for the category_mapper module.

Run with:
    pytest eval/test_category_mapper.py -v
"""

import pytest

from bank_agent.shared_tools.category_mapper import categorise, CATEGORIES


class TestCategorise:
    """Test that known descriptions map to the correct category."""

    # ── Groceries ──────────────────────────────────────────────
    @pytest.mark.parametrize("desc", [
        "Tesco Weekly Shop",
        "Sainsbury's Christmas Shop",
        "Aldi",
        "Lidl",
        "Waitrose",
        "Asda Superstore",
        "Morrisons",
        "Co-op Local",
        "Supermarket",
        "Ocado Delivery",
    ])
    def test_groceries(self, desc: str):
        assert categorise(desc) == "Groceries"

    # ── Incoming Salary ────────────────────────────────────────
    @pytest.mark.parametrize("desc", [
        "Salary - Acme Corp",
        "Payroll - City Council",
        "Freelance Invoice",
        "Pension",
        "Wages - Weekly",
        "ISA Transfer",
    ])
    def test_incoming_salary(self, desc: str):
        assert categorise(desc) == "Incoming Salary"

    # ── Travel ─────────────────────────────────────────────────
    @pytest.mark.parametrize("desc", [
        "Uber",
        "TfL Oyster Top-Up",
        "National Rail",
        "Trainline",
        "British Airways",
        "EasyJet Flight",
        "Ryanair",
        "Holiday Booking",
        "Booking.com Hotel",
        "Airbnb Stay",
        "Petrol",
        "Shell Fuel",
        "BP Fuel",
    ])
    def test_travel(self, desc: str):
        assert categorise(desc) == "Travel"

    # ── Interest ───────────────────────────────────────────────
    @pytest.mark.parametrize("desc", [
        "Interest Payment",
        "Savings Interest",
        "ISA Interest",
        "Interest Earned",
    ])
    def test_interest(self, desc: str):
        assert categorise(desc) == "Interest"

    # ── Subscriptions ──────────────────────────────────────────
    @pytest.mark.parametrize("desc", [
        "Netflix Monthly",
        "Spotify Premium",
        "Disney+",
        "Disney Plus",
        "Amazon Prime",
        "Apple Music",
        "YouTube Premium",
        "Deliveroo Plus",
        "Deliveroo Order",
        "Gym Membership",
        "Streaming Service",
        "Apple TV+",
        "Now TV",
        "Audible Monthly",
        "Xbox Game Pass",
        "PlayStation Plus",
        "Adobe Creative Cloud",
    ])
    def test_subscriptions(self, desc: str):
        assert categorise(desc) == "Subscriptions"

    # ── Rent ───────────────────────────────────────────────────
    @pytest.mark.parametrize("desc", [
        "Rent",
        "Mortgage Payment",
        "Mortgage",
        "Letting Agent Fee",
        "Housing Association",
    ])
    def test_rent(self, desc: str):
        assert categorise(desc) == "Rent"

    # ── Tax ────────────────────────────────────────────────────
    @pytest.mark.parametrize("desc", [
        "Council Tax",
        "HMRC Self Assessment",
        "Income Tax",
        "VAT Payment",
        "National Insurance",
    ])
    def test_tax(self, desc: str):
        assert categorise(desc) == "Tax"

    # ── Others (fallback) ─────────────────────────────────────
    @pytest.mark.parametrize("desc", [
        "Coffee Shop",
        "Online Retailer",
        "Electricity Bill",
        "Mobile Phone Bill",
        "Water Bill",
        "Random Purchase",
        "Unknown Merchant",
    ])
    def test_others(self, desc: str):
        assert categorise(desc) == "Others"

    # ── Edge cases ─────────────────────────────────────────────
    def test_empty_string(self):
        assert categorise("") == "Others"

    def test_case_insensitive(self):
        assert categorise("TESCO WEEKLY SHOP") == "Groceries"
        assert categorise("netflix monthly") == "Subscriptions"
        assert categorise("COUNCIL TAX") == "Tax"

    def test_partial_match(self):
        """Keywords embedded in longer descriptions should still match."""
        assert categorise("Payment to Tesco Express Store #1234") == "Groceries"
        assert categorise("Direct Debit - Netflix UK Ltd") == "Subscriptions"

    def test_categories_tuple_complete(self):
        """All 8 categories should be present in the CATEGORIES tuple."""
        expected = {
            "Groceries", "Incoming Salary", "Travel", "Interest",
            "Subscriptions", "Rent", "Tax", "Others",
        }
        assert set(CATEGORIES) == expected
