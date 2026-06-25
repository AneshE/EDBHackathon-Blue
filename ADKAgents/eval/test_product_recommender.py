"""Unit tests for the product recommender sub-agent."""

from __future__ import annotations


class TestProductRecommenderDefinition:
    """Verify the agent is correctly configured."""

    def test_agent_loads(self):
        """The product_recommender_agent should import without errors."""
        from bank_agent.product_recommender.agent import product_recommender_agent
        assert product_recommender_agent is not None

    def test_agent_name(self):
        from bank_agent.product_recommender.agent import product_recommender_agent
        assert product_recommender_agent.name == "product_recommender"

    def test_agent_has_tools(self):
        from bank_agent.product_recommender.agent import product_recommender_agent
        tool_names = [t.__name__ for t in product_recommender_agent.tools]
        assert "analyse_spending" in tool_names
        assert "vertex_vector_search" in tool_names


class TestRootAgentSubAgentRegistration:
    """Verify the root agent has the product recommender registered."""

    def test_root_agent_has_product_recommender(self):
        from bank_agent.agent import root_agent
        sub_names = [a.name for a in root_agent.sub_agents]
        assert "product_recommender" in sub_names


class TestPromptContent:
    """Verify prompt quality and completeness."""

    def test_product_recommender_prompt_mentions_requirements(self):
        from bank_agent.product_recommender.prompt import PRODUCT_RECOMMENDER_INSTRUCTION
        assert "analyse_spending" in PRODUCT_RECOMMENDER_INSTRUCTION
        assert "vertex_vector_search" in PRODUCT_RECOMMENDER_INSTRUCTION
        assert "20%" in PRODUCT_RECOMMENDER_INSTRUCTION

    def test_root_prompt_mentions_delegation(self):
        from bank_agent.prompt import AGENT_INSTRUCTION
        assert "product_recommender" in AGENT_INSTRUCTION
        assert "reallocate" in AGENT_INSTRUCTION
