import os
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_core.vectorstores import VectorStoreRetriever
from dotenv import load_dotenv

load_dotenv()

CHROMA_DIR = "backend/data/chroma_db"


def build_retriever(
    chunks: list[Document],
    persist_dir: str = CHROMA_DIR,
    k: int = 4,
) -> VectorStoreRetriever:
    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
    vectorstore = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory=persist_dir,
    )
    return vectorstore.as_retriever(search_kwargs={"k": k})


def load_retriever(persist_dir: str = CHROMA_DIR, k: int = 4) -> VectorStoreRetriever:
    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
    vectorstore = Chroma(
        persist_directory=persist_dir,
        embedding_function=embeddings,
    )
    return vectorstore.as_retriever(search_kwargs={"k": k})
