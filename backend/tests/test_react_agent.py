import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.mark.asyncio
async def test_create_agent_returns_executor():
    mock_llm = MagicMock()
    with patch("app.agent.react_agent.ChatOpenAI", return_value=mock_llm) as mock_cls:
        from app.agent.react_agent import create_agent
        executor = create_agent()
    assert executor is not None
    assert executor.max_iterations == 25
    assert executor.return_intermediate_steps is True
    mock_cls.assert_called_once()


@pytest.mark.asyncio
async def test_stream_agent_yields_chunks():
    mock_event_text = {"event": "on_chat_model_stream", "data": {"chunk": MagicMock(content="Hello")}}
    mock_event_tool = {"event": "on_tool_end", "data": {"output": {"tracks": []}}}

    async def fake_astream_events(*args, **kwargs):
        yield mock_event_text
        yield mock_event_tool

    mock_executor = MagicMock()
    mock_executor.astream_events = fake_astream_events

    with patch("app.agent.react_agent.create_agent", return_value=mock_executor):
        from app.agent.react_agent import stream_agent
        chunks = []
        async for chunk in stream_agent("test query"):
            chunks.append(chunk)

    assert any(c.get("type") == "text" for c in chunks)
    assert any(c.get("type") == "tool_result" for c in chunks)


@pytest.mark.asyncio
async def test_stream_agent_handles_done_event():
    mock_event_done = {"event": "on_chain_end", "data": {"output": {"output": "final answer"}}}

    async def fake_astream_events(*args, **kwargs):
        yield mock_event_done

    mock_executor = MagicMock()
    mock_executor.astream_events = fake_astream_events

    with patch("app.agent.react_agent.create_agent", return_value=mock_executor):
        from app.agent.react_agent import stream_agent
        chunks = [c async for c in stream_agent("test")]

    assert any(c.get("type") == "done" for c in chunks)
