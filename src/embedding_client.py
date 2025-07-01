from abc import ABC, abstractmethod
from typing import List
import openai
import os
from dotenv import load_dotenv
import logging

load_dotenv()
logger = logging.getLogger(__name__)

class EmbeddingClient(ABC):
    @abstractmethod
    async def embed(self, text: str) -> List[float]:
        raise NotImplementedError

class OpenAIEmbeddingClient(EmbeddingClient):
    def __init__(self, api_key: str = None, model: str = "text-embedding-ada-002"):
        self.client = openai.AsyncOpenAI(
            api_key=api_key or os.getenv("OPENAI_API_KEY")
        )
        self.model = model
    
    async def embed(self, text: str) -> List[float]:
        try:
            response = await self.client.embeddings.create(
                input=text,
                model=self.model
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            raise

class HuggingFaceEmbeddingClient(EmbeddingClient):
    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        try:
            from sentence_transformers import SentenceTransformer
            self.model = SentenceTransformer(model_name)
        except ImportError:
            raise ImportError("sentence-transformers package is required for HuggingFace embeddings")
    
    async def embed(self, text: str) -> List[float]:
        try:
            embedding = self.model.encode(text)
            return embedding.tolist()
        except Exception as e:
            logger.error(f"Error generating HuggingFace embedding: {e}")
            raise

def create_embedding_client(provider: str = "openai") -> EmbeddingClient:
    if provider.lower() == "openai":
        return OpenAIEmbeddingClient()
    elif provider.lower() == "huggingface":
        return HuggingFaceEmbeddingClient()
    else:
        raise ValueError(f"Unsupported embedding provider: {provider}")