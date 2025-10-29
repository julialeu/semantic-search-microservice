import uuid
from typing import List, NewType, Tuple
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

# --- Value Objects ---
DocumentID = NewType("DocumentID", str)
Embedding = NewType("Embedding", List[float])


# --- Entidad y Aggregate Root ---
class Document:
    """
    La entidad principal de nuestro dominio. Representa un texto
    con su correspondiente representación vectorial (embedding).
    """

    def __init__(self, content: str, embedding: Embedding, doc_id: DocumentID = None):
        if not content:
            raise ValueError("El contenido del documento no puede estar vacío.")

        self.id: DocumentID = doc_id or DocumentID(str(uuid.uuid4()))
        self.content: str = content
        self.embedding: Embedding = embedding


# --- Interfaces de Repositorio ---
class IDocumentRepository:
    def save(self, document: Document):
        raise NotImplementedError

    def find_by_id(self, doc_id: DocumentID) -> Document:
        raise NotImplementedError

    def find_similar(
        self, embedding: Embedding, top_k: int
    ) -> List[Tuple[Document, float]]:
        """
        Encuentra los 'top_k' documentos más similares a un embedding.
        Devuelve una lista de tuplas, donde cada tupla contiene
        el Documento y su puntuación de similitud (distancia).
        """
        raise NotImplementedError

    def delete(self, doc_id: DocumentID):
        """Elimina un documento del índice y del almacén de metadatos."""
        raise NotImplementedError

# --- Interfaces de Servicios ---
class IEmbeddingService:
    def create_embedding(self, text: str) -> Embedding:
        raise NotImplementedError

# --- ENTIDADES DE AUTENTICACIÓN ---

@dataclass
class User:
    """Entidad que representa a un usuario del sistema."""
    id: str
    email: str
    name: str
    hashed_password: str
    is_verified: bool = False
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

@dataclass
class Token:
    """Clase base para tokens."""
    token: str
    user_id: str
    expires_at: datetime
    created_at: Optional[datetime] = None

@dataclass
class RefreshToken(Token):
    """Entidad que representa un Refresh Token para renovar la sesión."""
    is_revoked: bool = False

@dataclass
class EmailVerificationToken(Token):
    """Token de un solo uso para verificar el email de un usuario."""
    pass

@dataclass
class PasswordResetToken(Token):
    """Token de un solo uso para restablecer la contraseña."""
    is_used: bool = False        
