from __future__ import annotations

from typing import List, Union

from langchain_community.chat_message_histories import UpstashRedisChatMessageHistory
from langchain_core.messages import AnyMessage
from langgraph.graph import add_messages
from typing_extensions import Annotated, TypedDict


class GraphConfig(TypedDict):
    model: Union[str, None]  # Correct usage of Union
    """The model to use for the memory assistant."""
    thread_id: str
    """The thread ID of the conversation."""
    user_id: str
    """The ID of the user to remember in the conversation."""
    session_id: str
    """The ID of the session to remember in the conversation."""

# ----------------------------------------- State --------------------------------------------------


class GraphState(TypedDict):
    """
    Represents the state of our graph.

    Attributes:
        question: question
        generation: LLM generation
        web_search: whether to add search
        documents: list of documents
    """

    question: str
    generation: str
    agent_search: str
    context: str
    """The code in the context of client application."""
    thread_id: str
    user_id: str
    documents: List[str]
    topics: List[str]
    session_ID: str
    chat_history: str
    messages: Annotated[List[AnyMessage], add_messages]
    """The messages in the conversation."""
    core_memories: List[str]
    """The core memories associated with the user."""
    recall_memories: List[str]
    """The recall memories retrieved for the current context."""

__all__ = [
    "GraphState",
    "GraphConfig",
]
