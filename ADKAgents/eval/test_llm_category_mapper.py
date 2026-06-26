"""Unit tests for the llm_category_mapper module.

Run with:
    pytest eval/test_llm_category_mapper.py -v
"""

import os
import pytest
from bank_agent.shared_tools.llm_category_mapper import (
    categorise,
    classify_budget,
    CACHE_FILE,
    _description_cache,
    _category_to_budget,
)

def test_llm_categorise_known_and_unknown():
    # Clear the test cache entries to ensure LLM is actually hit or cache is validated.
    # Note: we can let it run to populate the cache.
    desc_groceries = "Sainsbury's Supermarket"
    category = categorise(desc_groceries)
    
    # Assert that the category contains groceries-related terminology or is Groceries
    assert "grocer" in category.lower() or "supermarket" in category.lower() or category == "Groceries"
    
    # Check that it got cached
    assert desc_groceries.lower() in _description_cache
    cached_cat, cached_budget = _description_cache[desc_groceries.lower()]
    assert cached_cat == category
    assert cached_budget == "Needs"

def test_llm_categorise_discretionary():
    desc_netflix = "Netflix Video Streaming"
    category = categorise(desc_netflix)
    
    assert "subscription" in category.lower() or "streaming" in category.lower() or "entertainment" in category.lower() or category == "Subscriptions"
    
    cached_cat, cached_budget = _description_cache[desc_netflix.lower()]
    assert cached_budget == "Wants"

def test_classify_budget_direct():
    # Test standard category mappings
    assert classify_budget("Rent") == "Needs"
    assert classify_budget("Groceries") == "Needs"
    assert classify_budget("Subscriptions") == "Wants"
    assert classify_budget("Incoming Salary") == "Income"
    
    # Test a newly seen dynamic category
    assert classify_budget("Fine Dining Restaurant") == "Wants"

def test_cache_persistence():
    # Verify that the cache file has been created on disk
    assert os.path.exists(CACHE_FILE)
    
    # Verify it is valid JSON
    import json
    with open(CACHE_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
        assert "descriptions" in data
        assert "categories" in data
