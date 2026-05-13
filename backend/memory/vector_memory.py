import os
from langchain_openai import OpenAIEmbeddings

from db import postgres as db

_embeddings = OpenAIEmbeddings(model="text-embedding-3-small")


async def save_memory(user_id: str, session_id: str, summary: str, project_id: str) -> None:
    vector = (await _embeddings.aembed_documents([summary]))[0]
    await db.insert_doc_chunk(
        user_id=user_id,
        project_id=project_id,
        source="memory",
        content=summary,
        embedding=vector,
    )


async def recall_memory(user_id: str, query: str, k: int = 3) -> list[str]:
    vector = await _embeddings.aembed_query(query)
    results = await db.similarity_search(user_id=user_id, query_embedding=vector, k=k)
    return [r["content"] for r in results]
