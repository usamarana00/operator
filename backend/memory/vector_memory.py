from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma
from dotenv import load_dotenv

load_dotenv()

MEMORY_CHROMA_DIR = "backend/data/memory_chroma"


def _get_store(persist_dir: str = MEMORY_CHROMA_DIR) -> Chroma:
    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
    return Chroma(persist_directory=persist_dir, embedding_function=embeddings)


def save_memory(session_id: str, summary: str, persist_dir: str = MEMORY_CHROMA_DIR) -> None:
    store = _get_store(persist_dir)
    store.add_texts(
        texts=[summary],
        metadatas=[{"session_id": session_id}],
    )


def recall_memory(query: str, k: int = 3, persist_dir: str = MEMORY_CHROMA_DIR) -> list[str]:
    store = _get_store(persist_dir)
    results = store.similarity_search(query, k=k)
    return [r.page_content for r in results]
