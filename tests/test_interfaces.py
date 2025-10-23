from fastapi.testclient import TestClient

# Importamos las funciones proveedoras, no las instancias
from app.interfaces.api import app, get_doc_repo, get_embed_svc
from app.infrastructure.repositories import FAISSDocumentRepository
from tests.mocks import MockEmbeddingService
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

    # Sobrescribimos las funciones proveedoras
    app.dependency_overrides[get_doc_repo] = lambda: repo_temporal
    app.dependency_overrides[get_embed_svc] = lambda: servicio_embedding_mock

    yield

    app.dependency_overrides = {}


def test_index_document_success(repo_con_archivos_temporales):
    response = client.post(
        "/documents", json={"content": "Este es un documento de prueba."}
    )
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert "status" == "indexed"


def test_index_document_empty_content():
    response = client.post("/documents", json={"content": ""})
    assert response.status_code == 422
