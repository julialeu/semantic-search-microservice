# tests/test_e2e.py
from fastapi.testclient import TestClient
from app.interfaces.api import (
    app,
    doc_repo,
    embed_svc,
)  # Importamos los objetos a mockear
from app.infrastructure.repositories import FAISSDocumentRepository
from tests.mocks import MockEmbeddingService  # Importamos nuestro mock
import os
import pytest

client = TestClient(app)


@pytest.fixture(scope="module", autouse=True)
def setup_teardown_module(tmp_path_factory):
    tmp_dir = tmp_path_factory.mktemp("e2e_data")
    repo_temporal = FAISSDocumentRepository(
        index_path=os.path.join(tmp_dir, "e2e_index.faiss"),
        db_path=os.path.join(tmp_dir, "e2e_metadata.db"),
    )
    servicio_embedding_mock = MockEmbeddingService()

    # Sobrescribimos las dependencias para todos los tests de este fichero
    app.dependency_overrides[doc_repo] = lambda: repo_temporal
    app.dependency_overrides[embed_svc] = lambda: servicio_embedding_mock

    yield

    # Limpieza después de que todos los tests hayan terminado
    app.dependency_overrides = {}


def test_index_and_search_flow():
    # 1. Indexar documentos
    docs_to_index = ["El cielo es azul.", "El sol es una estrella brillante."]
    indexed_ids = []
    for doc in docs_to_index:
        response = client.post("/documents", json={"content": doc})
        assert response.status_code == 201
        indexed_ids.append(response.json()["id"])

    # 2. Realizar una búsqueda
    search_query = "¿Qué es una estrella?"
    response = client.post("/search", json={"query": search_query, "top_k": 2})

    # 3. Verificar la respuesta
    assert response.status_code == 200
    data = response.json()
    assert "results" in data
