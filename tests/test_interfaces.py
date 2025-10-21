from fastapi.testclient import TestClient
from app.interfaces.api import app, doc_repo
from app.infrastructure.repositories import FAISSDocumentRepository
import os
import pytest

client = TestClient(app)


# --- ESTA ES LA FORMA CORRECTA ---
# Creamos una 'fixture' que prepara el entorno para los tests que la necesiten.
@pytest.fixture
def repo_con_archivos_temporales(tmp_path):
    # 1. Preparación: Creamos un repositorio que usa la carpeta temporal.
    repo_temporal = FAISSDocumentRepository(
        index_path=os.path.join(tmp_path, "test_index.faiss"),
        db_path=os.path.join(tmp_path, "test_metadata.db"),
    )
    # 2. Le decimos a la app que use este repositorio temporal.
    app.dependency_overrides[doc_repo] = lambda: repo_temporal

    # 3. Dejamos que el test se ejecute.
    yield

    # 4. Limpieza: Quitamos la configuración temporal después del test.
    app.dependency_overrides = {}


# --- TESTS CORREGIDOS ---
# Este test necesita la base de datos, así que pide la fixture por su nombre.
def test_index_document_success(repo_con_archivos_temporales):
    response = client.post(
        "/documents", json={"content": "Este es un documento de prueba."}
    )
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["status"] == "indexed"


# Este test falla en la validación, no llega a la base de datos,
# así que no necesita la fixture.
def test_index_document_empty_content():
    response = client.post("/documents", json={"content": ""})
    assert response.status_code == 422
