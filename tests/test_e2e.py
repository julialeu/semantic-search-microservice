from fastapi.testclient import TestClient
from app.interfaces.api import app
import os
import pytest

client = TestClient(app)

# Fixture para limpiar la base de datos y el índice antes y después de los tests
@pytest.fixture(scope="module", autouse=True)
def setup_teardown():
    # Setup: Limpiar antes de empezar
    if os.path.exists("index.faiss"): os.remove("index.faiss")
    if os.path.exists("metadata.db"): os.remove("metadata.db")
    
    yield # Aquí es donde se ejecutan los tests
    
    # Teardown: Limpiar después de terminar
    if os.path.exists("index.faiss"): os.remove("index.faiss")
    if os.path.exists("metadata.db"): os.remove("metadata.db")

def test_index_and_search_flow():
    # 1. Indexar algunos documentos
    docs_to_index = [
        "El cielo es azul.",
        "El sol es una estrella brillante.",
        "Los coches son un medio de transporte."
    ]
    
    indexed_ids = []
    for doc in docs_to_index:
        response = client.post("/documents", json={"content": doc})
        assert response.status_code == 201
        indexed_ids.append(response.json()["id"])

    # 2. Realizar una búsqueda semánticamente similar a uno de los documentos
    # (Como usamos embeddings FALSOS, la búsqueda será aleatoria, pero podemos
    # verificar la estructura de la respuesta)
    search_query = "Qué es una estrella?"
    response = client.post("/search", json={"query": search_query, "top_k": 2})
    
    # 3. Verificar la respuesta
    assert response.status_code == 200
    data = response.json()
    assert "results" in data
    assert len(data["results"]) == 2
    
    first_result = data["results"][0]
    assert "id" in first_result
    assert "content" in first_result
    assert "score" in first_result
    assert first_result["id"] in indexed_ids