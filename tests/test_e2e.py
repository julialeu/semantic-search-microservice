# tests/test_e2e.py

from fastapi.testclient import TestClient
from app.interfaces.api import app, doc_repo
from app.infrastructure.repositories import FAISSDocumentRepository
import os
import pytest

client = TestClient(app)


# Esta fixture se ejecuta una vez para todos los tests de este módulo
@pytest.fixture(scope="module", autouse=True)
def setup_teardown_module(tmp_path_factory):
    # Creamos una carpeta temporal para todo el módulo de tests
    tmp_dir = tmp_path_factory.mktemp("e2e_data")
    test_repo = FAISSDocumentRepository(
        index_path=os.path.join(tmp_dir, "e2e_index.faiss"),
        db_path=os.path.join(tmp_dir, "e2e_metadata.db"),
    )
    # Sobrescribimos la dependencia para todos los tests de este fichero
    app.dependency_overrides[doc_repo] = lambda: test_repo

    yield  # Aquí se ejecutan los tests

    # Limpieza después de que todos los tests hayan terminado
    app.dependency_overrides = {}


def test_index_and_search_flow():
    # 1. Indexar algunos documentos
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
    assert len(data["results"]) <= 2  # Puede devolver menos si no hay suficientes

    if len(data["results"]) > 0:
        first_result = data["results"][0]
        assert "id" in first_result
        assert "content" in first_result
        assert "score" in first_result
        assert first_result["id"] in indexed_ids
