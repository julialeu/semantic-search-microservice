from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
import traceback

from app.application.use_cases import IndexDocumentUseCase, SearchDocumentsUseCase
from app.infrastructure.repositories import (
    FAISSDocumentRepository,
    MockEmbeddingService,
)
from typing import List

# --- Inicialización de la App y Dependencias ---
app = FastAPI(
    title="Semantic Search Service",
    description="API for indexing and searching documents using embeddings.",
    version="0.1.0",
)

# Instanciamos nuestras implementaciones concretas.
# Esto se podría mejorar con un contenedor de inyección de dependencias.
doc_repo = FAISSDocumentRepository()
embed_svc = MockEmbeddingService()
index_use_case = IndexDocumentUseCase(repo=doc_repo, embed_svc=embed_svc)
search_use_case = SearchDocumentsUseCase(repo=doc_repo, embed_svc=embed_svc)


# --- Modelos de Datos (DTOs) ---
class IndexRequest(BaseModel):
    content: str = Field(
        ..., min_length=1, description="El texto del documento a indexar."
    )


class IndexResponse(BaseModel):
    id: str
    status: str = "indexed"


class SearchRequest(BaseModel):
    query: str = Field(
        ..., min_length=1, description="Texto de la consulta para la búsqueda."
    )
    top_k: int = Field(3, gt=0, le=10, description="Número de resultados a devolver.")


class SearchResult(BaseModel):
    id: str
    content: str
    score: float


class SearchResponse(BaseModel):
    results: List[SearchResult]


# --- Endpoints ---
@app.post("/documents", response_model=IndexResponse, status_code=201)
def index_document(request: IndexRequest):
    """
    Indexa un nuevo documento.
    Recibe un texto, genera su embedding y lo almacena en la base de datos vectorial.
    """
    try:
        document_id = index_use_case.execute(request.content)
        return IndexResponse(id=document_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        # --- print(f"!!! Error inesperado en el endpoint /documents: {e}") ---
        traceback.print_exc()

        raise HTTPException(status_code=500, detail="Error interno del servidor.")


@app.post("/search", response_model=SearchResponse)
def search_documents(request: SearchRequest):
    """
    Realiza una búsqueda semántica.
    Recibe una consulta, genera su embedding y devuelve los documentos más similares.
    """
    try:
        results = search_use_case.execute(query=request.query, top_k=request.top_k)
        return SearchResponse(results=results)
    except Exception as e:
        # Loggear el error en un sistema real
        raise HTTPException(status_code=500, detail="Error interno del servidor.")


# Comando para ejecutar: uvicorn app.interfaces.api:app --reload
# Un pequeño cambio para forzar la actualización de la CI
