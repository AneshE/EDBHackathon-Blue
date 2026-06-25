"""End-to-end agent evaluation tests for the spending analyst.

These tests exercise the spending analyst agent with natural language
queries and verify the responses contain expected content.

IMPORTANT: These tests require:
  - GCP credentials (Application Default Credentials)
  - BQ_DATASET to be set and populated with seed data

Run with:
    pytest eval/test_spending_agent.py -v -s

Skip these tests when running offline:
    pytest eval/test_spending_agent.py -v -k "not e2e"
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# ── Test case loader ─────────────────────────────────────────────────────────

TEST_CASES_PATH = Path(__file__).parent / "test_cases.json"


def _load_test_cases() -> list[dict]:
    with open(TEST_CASES_PATH) as f:
        return json.load(f)


# ── Offline unit tests (no GCP required) ─────────────────────────────────────

class TestSpendingAnalystAgentDefinition:
    """Verify the agent is correctly configured (no GCP calls)."""

    def test_agent_loads(self):
        """The spending_analyst_agent should import without errors."""
        from bank_agent.spending_analyst.agent import spending_analyst_agent
        assert spending_analyst_agent is not None

    def test_agent_name(self):
        from bank_agent.spending_analyst.agent import spending_analyst_agent
        assert spending_analyst_agent.name == "spending_analyst"

    def test_agent_has_tools(self):
        from bank_agent.spending_analyst.agent import spending_analyst_agent
        tool_names = [t.__name__ for t in spending_analyst_agent.tools]
        assert "get_transactions" in tool_names
        assert "analyse_spending" in tool_names

    def test_agent_description_mentions_categories(self):
        from bank_agent.spending_analyst.agent import spending_analyst_agent
        desc = spending_analyst_agent.description
        for cat in ["Groceries", "Subscriptions", "Travel", "Rent", "Tax"]:
            assert cat in desc, f"Category '{cat}' missing from agent description"

    def test_agent_description_mentions_intervals(self):
        from bank_agent.spending_analyst.agent import spending_analyst_agent
        desc = spending_analyst_agent.description
        for interval in ["weekly", "monthly", "quarterly", "half-yearly", "annual"]:
            assert interval in desc, f"Interval '{interval}' missing from description"


class TestRootAgentSubAgentRegistration:
    """Verify the root agent has the spending analyst registered."""

    def test_root_agent_has_spending_analyst(self):
        from bank_agent.agent import root_agent
        sub_names = [a.name for a in root_agent.sub_agents]
        assert "spending_analyst" in sub_names


class TestPromptContent:
    """Verify prompt quality and completeness."""

    def test_spending_analyst_prompt_mentions_categories(self):
        from bank_agent.spending_analyst.prompt import SPENDING_ANALYST_INSTRUCTION
        for keyword in ["subscriptions", "spending"]:
            assert keyword in SPENDING_ANALYST_INSTRUCTION

    def test_spending_analyst_prompt_mentions_intervals(self):
        from bank_agent.spending_analyst.prompt import SPENDING_ANALYST_INSTRUCTION
        for keyword in ["weekly", "monthly", "quarterly", "half_yearly", "annual"]:
            assert keyword in SPENDING_ANALYST_INSTRUCTION

    def test_root_prompt_mentions_delegation(self):
        from bank_agent.prompt import AGENT_INSTRUCTION
        assert "spending_analyst" in AGENT_INSTRUCTION
        assert "spending habits" in AGENT_INSTRUCTION


class TestTestCasesFile:
    """Validate the test_cases.json file format."""

    def test_file_exists(self):
        assert TEST_CASES_PATH.exists()

    def test_all_cases_have_required_fields(self):
        cases = _load_test_cases()
        assert len(cases) >= 5, "Need at least 5 test cases"
        for case in cases:
            assert "name" in case, f"Missing 'name' in test case"
            assert "query" in case, f"Missing 'query' in {case.get('name', '?')}"
            assert "expected_keywords" in case, f"Missing 'expected_keywords' in {case.get('name', '?')}"
            assert len(case["expected_keywords"]) > 0, f"Empty expected_keywords in {case.get('name', '?')}"

    def test_c004_subscription_case_exists(self):
        cases = _load_test_cases()
        c004_cases = [c for c in cases if "C004" in c["query"]]
        assert len(c004_cases) >= 1, "Need at least one test case for C004 subscriptions"

    def test_multiple_intervals_covered(self):
        cases = _load_test_cases()
        intervals_mentioned = set()
        for case in cases:
            for kw in case.get("expected_keywords", []):
                kw_lower = kw.lower()
                if kw_lower in ("weekly", "monthly", "quarterly", "half_yearly", "annual"):
                    intervals_mentioned.add(kw_lower)
        assert len(intervals_mentioned) >= 3, (
            f"Test cases should cover at least 3 intervals, found: {intervals_mentioned}"
        )
