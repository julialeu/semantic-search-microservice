from fastapi.testclient import TestClient
from app.interfaces.api import app
import os

client = TestClient(app)


def setup_function():
    # Asegurarnos de que no existen ficheros de un test anterior
    if os.path.exists("index.faiss"):
        os.remove("index.faiss")
    if os.path.exists("metadata.db"):
        os.remove("metadata.db")


def test_index_document_success():
    response = client.post(
        "/documents", json={"content": "Este es un documento de prueba."}
    )
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["status"] == "indexed"
    assert os.path.exists("index.faiss")  # Verifica que el índice se guardó
    assert os.path.exists("metadata.db")  # Verifica que la DB se creó


def test_index_document_empty_content():
    response = client.post("/documents", json={"content": ""})
    assert response.status_code == 422  # FastAPI/Pydantic validation error


def teardown_function():
    # Limpiar ficheros después del test
    if os.path.exists("index.faiss"):
        os.remove("index.faiss")
    if os.path.exists("metadata.db"):
        os.remove("metadata.db")
