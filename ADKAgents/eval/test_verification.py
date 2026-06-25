"""Tests for the customer verification logic."""

from unittest.mock import MagicMock
from google.adk.agents.callback_context import CallbackContext
from google.adk.tools.tool_context import ToolContext
from bank_agent.callbacks import require_verified_identity
from bank_agent.agent import mark_verified, mark_failed

def test_require_verified_identity_unverified():
    ctx = MagicMock(spec=CallbackContext)
    ctx.state = {}
    response = require_verified_identity(ctx)
    assert response is not None
    assert "failed" in response.content.parts[0].text.lower()

def test_require_verified_identity_verified():
    ctx = MagicMock(spec=CallbackContext)
    ctx.state = {"identity_verified": True}
    response = require_verified_identity(ctx)
    assert response is None

def test_mark_verified():
    ctx = MagicMock(spec=ToolContext)
    ctx.state = {}
    result = mark_verified("C001", ctx)
    assert ctx.state.get("identity_verified") is True
    assert ctx.state.get("verified_customer_id") == "C001"
    assert result["status"] == "verified"

def test_mark_failed():
    ctx = MagicMock(spec=ToolContext)
    ctx.state = {"identity_verified": True}
    result = mark_failed(ctx)
    assert ctx.state.get("identity_verified") is False
    assert result["status"] == "failed"
