import os
from langchain_openai import OpenAIEmbeddings
from langchain_core.documents import Document

from db import postgres as db

_embeddings = OpenAIEmbeddings(model="text-embedding-3-small")


async def index_documents(
    user_id: str,
    project_id: str,
    chunks: list[Document],
    source: str = "readme",
) -> None:
    texts = [c.page_content for c in chunks]
    vectors = await _embeddings.aembed_documents(texts)
    for text, vector in zip(texts, vectors):
        await db.insert_doc_chunk(
            user_id=user_id,
            project_id=project_id,
            source=source,
            content=text,
            embedding=vector,
        )


async def retrieve(
    user_id: str,
    query: str,
    k: int = 4,
    project_id: str | None = None,
) -> list[str]:
    vector = await _embeddings.aembed_query(query)
    results = await db.similarity_search(
        user_id=user_id,
        query_embedding=vector,
        k=k,
        project_id=project_id,
    )
    return [r["content"] for r in results]
