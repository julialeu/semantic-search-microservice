import os
import traceback
from typing import List
from datetime import datetime, timezone

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, Field, EmailStr

# --- Importaciones de la Lógica de la Aplicación ---
from app.application.use_cases import (
    DeleteDocumentUseCase,
    IndexDocumentUseCase,
    LoginUserUseCase,
    RegisterUserUseCase,
    SearchDocumentsUseCase,
)
from app.domain.models import IDocumentRepository, IEmbeddingService
from app.infrastructure.repositories import (
    FAISSDocumentRepository,
    OpenAIEmbeddingService,
    TokenRepository,
    UserRepository,
)
from app.infrastructure.security import decode_token

# --- Carga de Configuración ---
load_dotenv()
if not os.getenv("OPENAI_API_KEY"):
    raise RuntimeError("La variable de entorno OPENAI_API_KEY no está configurada.")

app = FastAPI(
    title="Servicio de Búsqueda Semántica",
    description="API para indexar, buscar y eliminar documentos.",
    version="1.0.0",
)

# --- Configuración de CORS ---
allowed_origins = []
origins_str = os.getenv("CORS_ALLOWED_ORIGINS", "").strip()
if origins_str:
    allowed_origins = [origin.strip() for origin in origins_str.split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Modelos de Datos (DTOs) para la API ---


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


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)
    name: str = Field(..., min_length=2)


class UserResponse(BaseModel):
    id: str
    email: EmailStr
    name: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserResponse


# --- Proveedores de Dependencias ---


def get_doc_repo() -> IDocumentRepository:
    return FAISSDocumentRepository()


def get_embed_svc() -> IEmbeddingService:
    return OpenAIEmbeddingService()


def get_user_repo() -> UserRepository:
    return UserRepository()


def get_token_repo() -> TokenRepository:
    return TokenRepository()


# --- Dependencias de Seguridad ---
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_current_user(token: str = Depends(oauth2_scheme)):
    payload = decode_token(token)
    if payload is None or payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido o expirado",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return payload


# --- ENDPOINTS ---


# --- Endpoints de Sistema ---
@app.get("/health", status_code=status.HTTP_200_OK, tags=["System"])
def health_check():
    return {"status": "healthy", "timestamp": datetime.now(timezone.utc).isoformat()}


# --- Endpoints de Autenticación ---
@app.post("/auth/register", status_code=status.HTTP_201_CREATED, tags=["Auth"])
def register(
    request: RegisterRequest, user_repo: UserRepository = Depends(get_user_repo)
):
    try:
        use_case = RegisterUserUseCase(user_repo)
        user = use_case.execute(request.email, request.password, request.name)
        return {"user_id": user.id, "message": "Usuario registrado exitosamente."}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@app.post("/auth/login", response_model=TokenResponse, tags=["Auth"])
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    user_repo: UserRepository = Depends(get_user_repo),
    token_repo: TokenRepository = Depends(get_token_repo),
):
    try:
        use_case = LoginUserUseCase(user_repo, token_repo)
        result = use_case.execute(form_data.username, form_data.password)
        return TokenResponse(
            access_token=result["access_token"],
            refresh_token=result["refresh_token"],
            user=UserResponse(
                id=result["user"].id,
                email=result["user"].email,
                name=result["user"].name,
            ),
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )


# --- Endpoints de Documentos (Protegidos) ---
@app.post(
    "/documents",
    response_model=IndexResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(get_current_user)],
    tags=["Documents"],
)
def index_document(
    request: IndexRequest,
    repo: IDocumentRepository = Depends(get_doc_repo),
    embed_svc: IEmbeddingService = Depends(get_embed_svc),
):
    try:
        use_case = IndexDocumentUseCase(repo=repo, embed_svc=embed_svc)
        document_id = use_case.execute(request.content)
        return IndexResponse(id=document_id)
    except Exception:
        # traceback.print_exc() # Mantenlo comentado o bórralo
        raise HTTPException(
            status_code=500, detail="Error interno al indexar el documento."
        )


@app.post(
    "/search",
    response_model=SearchResponse,
    dependencies=[Depends(get_current_user)],
    tags=["Documents"],
)
def search_documents(
    request: SearchRequest,
    repo: IDocumentRepository = Depends(get_doc_repo),
    embed_svc: IEmbeddingService = Depends(get_embed_svc),
):
    try:
        use_case = SearchDocumentsUseCase(repo=repo, embed_svc=embed_svc)
        results = use_case.execute(query=request.query, top_k=request.top_k)
        return SearchResponse(results=results)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete(
    "/documents/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(get_current_user)],
    tags=["Documents"],
)
def delete_document(
    document_id: str, repo: IDocumentRepository = Depends(get_doc_repo)
):
    try:
        use_case = DeleteDocumentUseCase(repo=repo)
        use_case.execute(document_id)
        return None
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
