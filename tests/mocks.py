# tests/mocks.py
import numpy as np
from app.domain.models import Embedding, IEmbeddingService


class MockEmbeddingService(IEmbeddingService):
    """
    Una implementación simulada del servicio de embeddings para usar en tests.
    No realiza llamadas de red y devuelve un vector predecible.
    """

    def create_embedding(self, text: str) -> Embedding:
        dim = 1536
        vec = np.full(dim, 0.1, dtype="float32")
        return Embedding(vec.tolist())


def override_get_current_user():
    """
    Una dependencia falsa que simula un usuario autenticado para los tests.
    Devuelve un diccionario simple que imita el payload de un token JWT decodificado.
    """
    return {"user_id": "test_user_id", "email": "test@example.com"}
