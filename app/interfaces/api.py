import os
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from typing import List, Any

from app.application.use_cases import (
    IndexDocumentUseCase,
    SearchDocumentsUseCase,
    DeleteDocumentUseCase,
)
from app.infrastructure.repositories import (
    FAISSDocumentRepository,
    OpenAIEmbeddingService,
)

# Carga las variables de entorno desde el fichero .env al iniciar la aplicación.
load_dotenv()

# --- Verificación de configuración ---
# Es una buena práctica verificar que las claves necesarias existen al arrancar.
if not os.getenv("OPENAI_API_KEY"):
    raise RuntimeError(
        "La variable de entorno OPENAI_API_KEY no está configurada. "
        "Por favor, crea un fichero .env y añade tu clave."
    )

# --- Inicialización de la App y Dependencias ---
app = FastAPI(
    title="Servicio de Búsqueda Semántica",
    description="API para indexar, buscar y eliminar documentos usando embeddings.",
    version="1.0.0",
)

# Instanciamos nuestras implementaciones concretas.
doc_repo = FAISSDocumentRepository()
embed_svc = OpenAIEmbeddingService()  # <- Usamos la implementación real.

# Inyectamos las dependencias en nuestros casos de uso.
index_use_case = IndexDocumentUseCase(repo=doc_repo, embed_svc=embed_svc)
search_use_case = SearchDocumentsUseCase(repo=doc_repo, embed_svc=embed_svc)
delete_use_case = DeleteDocumentUseCase(repo=doc_repo)


# --- Modelos de Datos (DTOs) para la API ---
class IndexRequest(BaseModel):
    content: str = Field(..., min_length=1, description="El texto a indexar.")


class IndexResponse(BaseModel):
    id: str
    status: str = "indexed"


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, description="Texto de la consulta.")
    top_k: int = Field(3, gt=0, le=10, description="Número de resultados a devolver.")


class SearchResult(BaseModel):
    id: str
    content: str
    score: float


class SearchResponse(BaseModel):
    results: List[SearchResult]


# --- Endpoints de la API ---
@app.post("/documents", response_model=IndexResponse, status_code=status.HTTP_201_CREATED)
def index_document(request: IndexRequest):
    """Indexa un nuevo documento."""
    try:
        document_id = index_use_case.execute(request.content)
        return IndexResponse(id=document_id)
    except Exception as e:
        # En un sistema real, aquí se registraría el error detallado (logging).
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno del servidor: {e}",
        )


@app.post("/search", response_model=SearchResponse)
def search_documents(request: SearchRequest):
    """Realiza una búsqueda semántica."""
    try:
        results = search_use_case.execute(query=request.query, top_k=request.top_k)
        return SearchResponse(results=results)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno del servidor: {e}",
        )


@app.delete("/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(document_id: str):
    """Elimina un documento del índice por su ID."""
    try:
        delete_use_case.execute(document_id)
        # Una respuesta 204 no debe tener cuerpo.
        return None
    except Exception as e:
        # Opcional: Aquí se podría manejar un error de "Documento no encontrado"
        # y devolver un 404, pero un 500 es aceptable para errores inesperados.
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno del servidor: {e}",
        )