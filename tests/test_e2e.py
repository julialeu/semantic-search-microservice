import os
import pytest
from fastapi.testclient import TestClient

from app.interfaces.api import app, get_current_user, get_doc_repo, get_embed_svc
from app.infrastructure.repositories import FAISSDocumentRepository
from tests.mocks import MockEmbeddingService, override_get_current_user


@pytest.fixture(scope="module")
def client_e2e(tmp_path_factory):
    tmp_dir = tmp_path_factory.mktemp("e2e_data")
    repo_temporal = FAISSDocumentRepository(
        index_path=os.path.join(tmp_dir, "e2e_index.faiss"),
        db_path=os.path.join(tmp_dir, "e2e_metadata.db"),
    )
    servicio_embedding_mock = MockEmbeddingService()

    app.dependency_overrides[get_doc_repo] = lambda: repo_temporal
    app.dependency_overrides[get_embed_svc] = lambda: servicio_embedding_mock
    app.dependency_overrides[get_current_user] = override_get_current_user

    with TestClient(app) as client:
        yield client

    app.dependency_overrides = {}


def test_index_and_search_flow(client_e2e):
    docs_to_index = ["El cielo es azul.", "El sol es una estrella brillante."]
    for doc in docs_to_index:
        response = client_e2e.post("/documents", json={"content": doc})
        assert response.status_code == 201

    response = client_e2e.post(
        "/search", json={"query": "¿Qué es una estrella?", "top_k": 2}
    )
    assert response.status_code == 200
    data = response.json()
    assert "results" in data
