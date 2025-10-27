import os
from fastapi import FastAPI, HTTPException, status, Depends
from dotenv import load_dotenv
from typing import List

from app.application.use_cases import (
    IndexDocumentUseCase,
    SearchDocumentsUseCase,
    DeleteDocumentUseCase,
)
from app.infrastructure.repositories import (
    FAISSDocumentRepository,
    OpenAIEmbeddingService,
)
from app.domain.models import IDocumentRepository, IEmbeddingService

# --- Carga y Verificación de Configuración ---
load_dotenv()
if not os.getenv("OPENAI_API_KEY"):
    raise RuntimeError("La variable de entorno OPENAI_API_KEY no está configurada.")

app = FastAPI(
    title="Servicio de Búsqueda Semántica",
    description="API para indexar, buscar y eliminar documentos.",
    version="1.0.0",
)

allowed_origins = []

origins_str = os.getenv("CORS_ALLOWED_ORIGINS", "").strip()

if origins_str:
    allowed_origins = [origin.strip() for origin in origins_str.split(',')]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Proveedores de Dependencias ---
def get_doc_repo() -> IDocumentRepository:
    return FAISSDocumentRepository()


def get_embed_svc() -> IEmbeddingService:
    return OpenAIEmbeddingService()


# --- Modelos de Datos (DTOs) ---
from pydantic import BaseModel, Field


class IndexRequest(BaseModel):
    content: str = Field(..., min_length=1)


class IndexResponse(BaseModel):
    id: str
    status: str = "indexed"


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1)
    top_k: int = Field(3, gt=0, le=10)


class SearchResult(BaseModel):
    id: str
    content: str
    score: float


class SearchResponse(BaseModel):
    results: List[SearchResult]


# --- Endpoints con Inyección de Dependencias ---
@app.post(
    "/documents", response_model=IndexResponse, status_code=status.HTTP_201_CREATED
)
def index_document(
    request: IndexRequest,
    repo: IDocumentRepository = Depends(get_doc_repo),
    embed_svc: IEmbeddingService = Depends(get_embed_svc),
):
    """Indexa un nuevo documento."""
    try:
        use_case = IndexDocumentUseCase(repo=repo, embed_svc=embed_svc)
        document_id = use_case.execute(request.content)
        return IndexResponse(id=document_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/search", response_model=SearchResponse)
def search_documents(
    request: SearchRequest,
    repo: IDocumentRepository = Depends(get_doc_repo),
    embed_svc: IEmbeddingService = Depends(get_embed_svc),
):
    """Realiza una búsqueda semántica."""
    try:
        use_case = SearchDocumentsUseCase(repo=repo, embed_svc=embed_svc)
        results = use_case.execute(query=request.query, top_k=request.top_k)
        return SearchResponse(results=results)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(
    document_id: str, repo: IDocumentRepository = Depends(get_doc_repo)
):
    """Elimina un documento del índice por su ID."""
    try:
        use_case = DeleteDocumentUseCase(repo=repo)
        use_case.execute(document_id)
        return None
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
