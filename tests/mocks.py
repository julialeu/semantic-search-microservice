# tests/mocks.py
import numpy as np
from app.domain.models import Embedding, IEmbeddingService


class MockEmbeddingService(IEmbeddingService):
    """
    Una implementación simulada del servicio de embeddings para usar en tests.
    No realiza llamadas de red y devuelve un vector predecible.
    """

    def create_embedding(self, text: str) -> Embedding:
        # Devuelve un vector de 1536 dimensiones lleno de 0.1s
        # Es predecible y no necesita aleatoriedad.
        dim = 1536
        vec = np.full(dim, 0.1, dtype="float32")
        return Embedding(vec.tolist())
