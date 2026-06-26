"""Map transaction descriptions to spending categories dynamically using Gemini LLM."""

import os
import json
import logging
from google.genai import Client
from google.genai import types

logger = logging.getLogger(__name__)

# Cache file in the same directory as this script.
CACHE_FILE = os.path.join(os.path.dirname(__file__), "llm_category_cache.json")

# In-memory caches.
_description_cache: dict[str, tuple[str, str]] = {}
_category_to_budget: dict[str, str] = {
    # Default/fallback classifications for common categories
    "Groceries": "Needs",
    "Rent": "Needs",
    "Tax": "Needs",
    "Travel": "Needs",
    "Subscriptions": "Wants",
    "Others": "Wants",
    "Interest": "Savings",
    "Incoming Salary": "Income",
}

def load_cache():
    """Load cached categorisations from disk."""
    global _description_cache, _category_to_budget
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                _description_cache = {k: tuple(v) for k, v in data.get("descriptions", {}).items()}
                _category_to_budget.update(data.get("categories", {}))
        except Exception as e:
            logger.warning(f"Failed to load category cache: {e}")

def save_cache():
    """Save cached categorisations to disk."""
    try:
        data = {
            "descriptions": _description_cache,
            "categories": _category_to_budget
        }
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        logger.warning(f"Failed to save category cache: {e}")

# Load cache on module load.
load_cache()

# Initialize GenAI Client.
def _get_client() -> Client:
    """Initialize Gemini GenAI client using Vertex AI or standard API key."""
    if os.getenv("GOOGLE_CLOUD_PROJECT"):
        return Client(
            vertexai=True,
            project=os.getenv("GOOGLE_CLOUD_PROJECT"),
            location=os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1"),
        )
    return Client()

# Global Client reference.
_client = None

def get_client() -> Client:
    """Get or initialize the Gemini client."""
    global _client
    if _client is None:
        _client = _get_client()
    return _client

def _classify_via_llm(description: str) -> tuple[str, str]:
    """Call Gemini to categorise and classify a description."""
    client = get_client()
    
    schema = {
        "type": "OBJECT",
        "properties": {
            "category": {
                "type": "STRING",
                "description": "A dynamic, descriptive category name (e.g., Groceries, Rent, Utilities, Subscriptions, Salary, Travel, Cafe, Shopping, Interest, etc.)"
            },
            "budget_classification": {
                "type": "STRING",
                "enum": ["Needs", "Wants", "Savings", "Income"],
                "description": "Needs (essential), Wants (discretionary), Savings (savings/interest), or Income (incoming money)"
            }
        },
        "required": ["category", "budget_classification"],
    }
    
    config = types.GenerateContentConfig(
        response_mime_type="application/json",
        response_schema=schema,
        temperature=0.1,
        system_instruction=(
            "You are a precise banking assistant. Analyze the transaction description and map it to: "
            "1. A dynamic category name (concise, Title Case, e.g. Groceries, Subscriptions, Public Transport, Salary, Interest, Gym Membership, Utilities, Taxes, Rent, Dining Out). "
            "2. A 50/30/20 budget classification. "
            "Rules for budget classification: "
            "- Needs: Essential living costs (rent/mortgage, utilities, taxes, groceries, public transport, fuel, medical/insurance). "
            "- Wants: Discretionary/lifestyle spending (dining out, cafes, shopping, entertainment, non-essential subscriptions like streaming or gym). "
            "- Savings: Savings contributions, investments, interest earned/paid, debt repayments. "
            "- Income: Incoming salary, wages, pension, freelance invoices, ISA/account inbound transfers."
        )
    )
    
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=f"Classify this transaction: '{description}'",
            config=config
        )
        data = json.loads(response.text)
        category = str(data.get("category", "Others")).strip()
        budget = str(data.get("budget_classification", "Wants")).strip()
        return category, budget
    except Exception as e:
        logger.error(f"LLM classification failed for '{description}': {e}")
        # Return sensible fallback if LLM call fails
        return "Others", "Wants"

def categorise(description: str) -> str:
    """Return the spending category for a transaction *description* dynamically."""
    if not description:
        return "Others"
    
    # Custom exact match check or case insensitive check in cache.
    desc_clean = description.strip()
    desc_key = desc_clean.lower()
    
    # We store the cache keys in lowercase for robustness.
    if desc_key in _description_cache:
        return _description_cache[desc_key][0]
    
    # Call Gemini to categorise and classify.
    category, budget = _classify_via_llm(desc_clean)
    
    # Cache results.
    _description_cache[desc_key] = (category, budget)
    _category_to_budget[category] = budget
    save_cache()
    
    return category

def classify_budget(category: str) -> str:
    """Map a spending *category* dynamically to a budget bucket (Needs / Wants / Savings / Income)."""
    if not category:
        return "Wants"
    
    if category in _category_to_budget:
        return _category_to_budget[category]
    
    # If the category is unknown, classify it via a small LLM call.
    client = get_client()
    schema = {
        "type": "OBJECT",
        "properties": {
            "budget_classification": {
                "type": "STRING",
                "enum": ["Needs", "Wants", "Savings", "Income"]
            }
        },
        "required": ["budget_classification"]
    }
    
    config = types.GenerateContentConfig(
        response_mime_type="application/json",
        response_schema=schema,
        temperature=0.1,
        system_instruction=(
            "Classify a transaction category into one of: "
            "Needs (essential), Wants (discretionary), Savings (savings/interest), or Income (incoming money)."
        )
    )
    
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=f"Classify this category: '{category}'",
            config=config
        )
        data = json.loads(response.text)
        budget = str(data.get("budget_classification", "Wants")).strip()
    except Exception as e:
        logger.error(f"LLM budget classification failed for '{category}': {e}")
        budget = "Wants"
        
    _category_to_budget[category] = budget
    save_cache()
    return budget
