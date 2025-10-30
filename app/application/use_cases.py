from typing import List, Dict, Any
from datetime import datetime, timedelta, timezone
from app.domain.models import (
    Document,
    IDocumentRepository,
    IEmbeddingService,
    DocumentID,
    User,
)
from app.infrastructure.repositories import UserRepository, TokenRepository
from app.infrastructure.security import (
    get_password_hash,
    verify_password,
    create_access_token,
    create_refresh_token,
    REFRESH_TOKEN_EXPIRE_DAYS,
)


class IndexDocumentUseCase:
    """
    Caso de uso para indexar un nuevo documento.
    """

    def __init__(self, repo: IDocumentRepository, embed_svc: IEmbeddingService):
        self.repo = repo
        self.embed_svc = embed_svc

    def execute(self, content: str) -> str:
        # Crear el embedding a partir del texto
        embedding = self.embed_svc.create_embedding(content)

        # Crear la entidad Document
        document = Document(content=content, embedding=embedding)

        # Guardar el documento usando el repositorio
        self.repo.save(document)

        # Devolver el ID del documento creado
        return document.id


class SearchDocumentsUseCase:
    """
    Caso de uso para buscar documentos relevantes a una consulta.
    """

    def __init__(self, repo: IDocumentRepository, embed_svc: IEmbeddingService):
        self.repo = repo
        self.embed_svc = embed_svc

    def execute(self, query: str, top_k: int) -> List[Dict[str, Any]]:
        # 1. Crear el embedding para la consulta
        query_embedding = self.embed_svc.create_embedding(query)

        # 2. Encontrar documentos similares usando el repositorio
        similar_docs = self.repo.find_similar(query_embedding, top_k)

        # 3. Formatear la salida para la capa de la API
        results = [
            {"id": doc.id, "content": doc.content, "score": score}
            for doc, score in similar_docs
        ]

        return results


class DeleteDocumentUseCase:
    def __init__(self, repo: IDocumentRepository):
        self.repo = repo

    def execute(self, doc_id_str: str):
        doc_id = DocumentID(doc_id_str)
        self.repo.delete(doc_id)


class RegisterUserUseCase:
    """Caso de uso para registrar un nuevo usuario."""

    def __init__(self, user_repo: UserRepository):
        self.user_repo = user_repo

    def execute(self, email: str, password: str, name: str) -> User:
        # 1. Verificar si el usuario ya existe
        if self.user_repo.find_by_email(email):
            raise ValueError("El email ya está en uso.")

        # 2. Hashear la contraseña
        hashed_password = get_password_hash(password)

        # 3. Crear la entidad de dominio
        new_user = User(
            id=None, email=email, name=name, hashed_password=hashed_password
        )

        # 4. Guardar el nuevo usuario a través del repositorio
        return self.user_repo.save(new_user)


class LoginUserUseCase:
    """Caso de uso para el inicio de sesión de un usuario."""

    def __init__(self, user_repo: UserRepository, token_repo: TokenRepository):
        self.user_repo = user_repo
        self.token_repo = token_repo

    def execute(self, email: str, password: str) -> dict:
        # 1. Buscar al usuario por su email
        user = self.user_repo.find_by_email(email)
        if not user:
            raise ValueError("Credenciales inválidas.")

        # 2. Verificar la contraseña
        if not verify_password(password, user.hashed_password):
            raise ValueError("Credenciales inválidas.")

        # 3. Crear los tokens JWT
        token_data = {"user_id": user.id, "email": user.email}
        access_token = create_access_token(data=token_data)
        refresh_token = create_refresh_token(data=token_data)

        # 4. Guardar el refresh token en la base de datos
        expires_at = datetime.now(timezone.utc) + timedelta(
            days=REFRESH_TOKEN_EXPIRE_DAYS
        )
        self.token_repo.save_refresh_token(refresh_token, user.id, expires_at)

        # 5. Devolver los tokens y los datos básicos del usuario
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "user": user,
        }
