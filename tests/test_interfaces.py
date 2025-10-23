# tests/test_interfaces.py
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


@pytest.fixture
def repo_con_archivos_temporales(tmp_path):
    # Preparamos las dependencias de prueba
    repo_temporal = FAISSDocumentRepository(
        index_path=os.path.join(tmp_path, "test_index.faiss"),
        db_path=os.path.join(tmp_path, "test_metadata.db"),
    )
    servicio_embedding_mock = MockEmbeddingService()

    # Sobrescribimos las dependencias en la app
    app.dependency_overrides[doc_repo] = lambda: repo_temporal
    app.dependency_overrides[embed_svc] = lambda: servicio_embedding_mock

    yield

    # Limpiamos los overrides después del test
    app.dependency_overrides = {}


def test_index_document_success(repo_con_archivos_temporales):
    response = client.post(
        "/documents", json={"content": "Este es un documento de prueba."}
    )
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["status"] == "indexed"


def test_index_document_empty_content():
    response = client.post("/documents", json={"content": ""})
    assert response.status_code == 422
