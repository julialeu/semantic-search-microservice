import os
import pytest
from fastapi.testclient import TestClient

from app.interfaces.api import app, get_current_user, get_doc_repo, get_embed_svc
from app.infrastructure.repositories import FAISSDocumentRepository
from tests.mocks import MockEmbeddingService, override_get_current_user


@pytest.fixture
def client_interfaces(tmp_path):
    repo_temporal = FAISSDocumentRepository(
        index_path=os.path.join(tmp_path, "test_index.faiss"),
        db_path=os.path.join(tmp_path, "test_metadata.db"),
    )
    servicio_embedding_mock = MockEmbeddingService()

    app.dependency_overrides[get_doc_repo] = lambda: repo_temporal
    app.dependency_overrides[get_embed_svc] = lambda: servicio_embedding_mock
    app.dependency_overrides[get_current_user] = override_get_current_user

    with TestClient(app) as client:
        yield client

    app.dependency_overrides = {}


def test_index_document_success(client_interfaces):
    response = client_interfaces.post(
        "/documents", json={"content": "Este es un documento de prueba."}
    )
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["status"] == "indexed"


def test_index_document_empty_content(client_interfaces):
    response = client_interfaces.post("/documents", json={"content": ""})
    assert response.status_code == 422


def test_health_check(client_interfaces):
    response = client_interfaces.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
