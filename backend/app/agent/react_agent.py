from __future__ import annotations

import logging
from typing import Any, AsyncIterator, Dict, List, Optional

from langchain.agents import AgentExecutor, create_react_agent
from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI

from app.agent.tools import ALL_TOOLS
from app.config import settings

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are SONIQWERK, an AI assistant that controls Ableton Live via a WebSocket bridge.
You support Ableton Live 11 and Live 12. Use the available tools to inspect and manipulate the Live session.

Always start by calling get_session_info to understand the current state.
Be precise with track indices (0-based). When setting parameters, verify the range first.

You have access to these tools:
{tools}

Use the following format:
Question: the input question you must answer
Thought: you should always think about what to do
Action: the action to take, should be one of [{tool_names}]
Action Input: the input to the action
Observation: the result of the action
... (this Thought/Action/Action Input/Observation can repeat N times)
Thought: I now know the final answer
Final Answer: the final answer to the original input question

Begin!

Question: {input}
Thought:{agent_scratchpad}"""


def create_agent() -> AgentExecutor:
    """Create and return a LangChain ReAct AgentExecutor."""
    llm = ChatOpenAI(
        model=getattr(settings, "openai_model", "gpt-4o"),
        api_key=settings.openai_api_key,
        temperature=0,
        streaming=True,
    )
    prompt = PromptTemplate.from_template(SYSTEM_PROMPT)
    agent = create_react_agent(llm=llm, tools=ALL_TOOLS, prompt=prompt)
    return AgentExecutor(
        agent=agent,
        tools=ALL_TOOLS,
        max_iterations=10,
        return_intermediate_steps=True,
        handle_parsing_errors=True,
    )


async def stream_agent(
    query: str,
    chat_history: Optional[List[Dict[str, Any]]] = None,
) -> AsyncIterator[Dict[str, Any]]:
    """Stream agent events as structured dicts."""
    executor = create_agent()
    inputs = {"input": query}

    async for event in executor.astream_events(inputs, version="v2"):
        event_type = event.get("event", "")
        data = event.get("data", {})

        if event_type == "on_chat_model_stream":
            chunk = data.get("chunk")
            if chunk and hasattr(chunk, "content") and chunk.content:
                yield {"type": "text", "content": chunk.content}

        elif event_type == "on_tool_end":
            output = data.get("output", {})
            yield {"type": "tool_result", "content": output}

        elif event_type == "on_chain_end":
            output = data.get("output", {})
            if isinstance(output, dict) and "output" in output:
                yield {"type": "done", "content": output["output"]}
