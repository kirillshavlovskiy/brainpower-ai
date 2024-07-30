from __future__ import annotations

from functools import lru_cache

import langsmith
from langchain_core.runnables import RunnableConfig
from langchain_fireworks import FireworksEmbeddings
from pinecone import Pinecone

from . import _schemas as schemas
from . import _settings as settings

_DEFAULT_DELAY = 60  # seconds


def get_index():
    pc = Pinecone(api_key=settings.SETTINGS.pinecone_api_key)
    return pc.Index(settings.SETTINGS.pinecone_index_name)

from ._schemas import GraphState, GraphConfig


@langsmith.traceable
def ensure_configurable(config: RunnableConfig):
    """Merge the user-provided config with default values."""
    configurable = config.get("configurable", {})
    return {
        **configurable,
        **GraphConfig(
            delay=configurable.get("delay", _DEFAULT_DELAY),
            model=configurable.get("model", settings.SETTINGS.model),
            thread_id=configurable["thread_id"],
            user_id=configurable["user_id"],
        ),
    }


@lru_cache
def get_embeddings():
    return FireworksEmbeddings(model="nomic-ai/nomic-embed-text-v1.5")


__all__ = ["ensure_configurable"]
