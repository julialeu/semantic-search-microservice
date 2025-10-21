import uuid
from typing import List, NewType

# --- Value Objects ---
DocumentID = NewType('DocumentID', str)
Embedding = NewType('Embedding', List[float])

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
        
class IEmbeddingService:
    def create_embedding(self, text: str) -> Embedding:
        raise NotImplementedError