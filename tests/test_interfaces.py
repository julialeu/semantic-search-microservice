# tests/test_interfaces.py

from fastapi.testclient import TestClient
from app.interfaces.api import app, doc_repo
from app.infrastructure.repositories import FAISSDocumentRepository
import os

# Usamos el cliente de FastAPI
client = TestClient(app)

# Esta fixture se ejecuta para cada test en este fichero
def setup_function(tmp_path):
    # Creamos un repositorio que usa la carpeta temporal del test
    test_repo = FAISSDocumentRepository(
        index_path=os.path.join(tmp_path, "test_index.faiss"),
        db_path=os.path.join(tmp_path, "test_metadata.db")
    )
    # Le decimos a FastAPI que, durante este test, use nuestro repo temporal
    app.dependency_overrides[doc_repo] = lambda: test_repo

def teardown_function():
    # Limpiamos el override para no afectar a otros tests
    app.dependency_overrides = {}

def test_index_document_success(tmp_path):
    # Inyectamos setup_function que configura el repo temporal
    setup_function(tmp_path)
    response = client.post("/documents", json={"content": "Este es un documento de prueba."})
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["status"] == "indexed"
    teardown_function()

def test_index_document_empty_content():
    response = client.post("/documents", json={"content": ""})
    assert response.status_code == 422