from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_text_splitters import CharacterTextSplitter
import os

class FitnessVectorRAG:
    def __init__(self, api_key: str):
        self.embeddings = OpenAIEmbeddings(openai_api_key=api_key)
        self.vector_db = None

    def initialize_with_texts(self, texts: list):
        """Create a FAISS index from a list of research snippets."""
        text_splitter = CharacterTextSplitter(chunk_size=500, chunk_overlap=50)
        docs = text_splitter.create_documents(texts)
        self.vector_db = FAISS.from_documents(docs, self.embeddings)

    def search(self, query: str, k: int = 3):
        """Search for relevant research snippets."""
        if not self.vector_db:
            return "Vector DB not initialized."
        results = self.vector_db.similarity_search(query, k=k)
        return [res.page_content for res in results]
