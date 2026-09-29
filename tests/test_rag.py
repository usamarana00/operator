import os
import sys
import asyncio
from unittest.mock import patch, AsyncMock, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from rag import retriever


def test_retrieve_returns_content_strings():
    fake_embeddings = MagicMock()
    fake_embeddings.aembed_query = AsyncMock(return_value=[0.0] * 1536)

    async def run():
        with patch("rag.retriever._embeddings", fake_embeddings), \
             patch("rag.retriever.db.similarity_search", new=AsyncMock(return_value=[
                 {"content": "chunk A", "source": "readme", "project_id": "p", "score": 0.9},
                 {"content": "chunk B", "source": "readme", "project_id": "p", "score": 0.8},
             ])):
            return await retriever.retrieve(user_id="u", query="deadlines", k=2)

    chunks = asyncio.run(run())
    assert chunks == ["chunk A", "chunk B"]
