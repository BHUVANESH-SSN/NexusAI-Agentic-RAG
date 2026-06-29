from unittest.mock import MagicMock, patch


def _assert_contract(result: dict) -> None:
    assert isinstance(result, dict), "run() must return a dict"
    assert "answer" in result and isinstance(result["answer"], str)
    assert "source" in result and isinstance(result["source"], str)


def test_db_agent_error_returns_contract():
    with patch("agents.db_agent.create_sql_agent") as mock:
        mock.return_value.invoke.side_effect = RuntimeError("db down")
        from agents.db_agent import DBAgent
        with patch("agents.db_agent.ensure_db"), \
             patch("agents.db_agent.SQLDatabase.from_uri"):
            agent = DBAgent.__new__(DBAgent)
            agent.agent_executor = mock.return_value
            _assert_contract(agent.run("how many employees?"))


def test_tool_agent_error_returns_contract():
    with patch("agents.tool_agent.create_react_agent") as mock:
        mock.return_value.invoke.side_effect = RuntimeError("tool error")
        from agents.tool_agent import ToolAgent
        with patch("agents.tool_agent.get_llm_with_failover"):
            agent = ToolAgent.__new__(ToolAgent)
            agent.agent_executor = mock.return_value
            _assert_contract(agent.run("send an email"))


def test_retriever_agent_graph_error_returns_contract():
    from agents.retriever_agent import RetrieverAgent
    mock_retriever = MagicMock()
    with patch("agents.retriever_agent.get_llm_with_failover", return_value=MagicMock()):
        agent = RetrieverAgent.__new__(RetrieverAgent)
        agent.retriever = mock_retriever
        agent._graph = MagicMock()
        agent._graph.invoke.side_effect = RuntimeError("graph failed")
        _assert_contract(agent.run("what is the refund policy?"))
