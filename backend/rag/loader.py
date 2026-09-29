import os
from langchain_community.document_loaders import TextLoader, DirectoryLoader
from langchain_core.documents import Document


def load_documents(data_dir: str) -> list[Document]:
    docs: list[Document] = []

    projects_dir = os.path.join(data_dir, "projects")
    if os.path.exists(projects_dir):
        loader = DirectoryLoader(projects_dir, glob="**/*.md", loader_cls=TextLoader)
        docs.extend(loader.load())

    clients_dir = os.path.join(data_dir, "clients")
    if os.path.exists(clients_dir):
        loader = DirectoryLoader(clients_dir, glob="**/*.txt", loader_cls=TextLoader)
        docs.extend(loader.load())

    return docs
