from typing import List, Dict, Any
from app.domain.models import Document, IDocumentRepository, IEmbeddingService

class IndexDocumentUseCase:
    """
    Caso de uso para indexar un nuevo documento.
    """
    def __init__(self, repo: IDocumentRepository, embed_svc: IEmbeddingService):
        self.repo = repo
        self.embed_svc = embed_svc

    def execute(self, content: str) -> str:
        # 1. Crear el embedding a partir del texto
        embedding = self.embed_svc.create_embedding(content)
        
        # 2. Crear la entidad Document
        document = Document(content=content, embedding=embedding)
        
        # 3. Guardar el documento usando el repositorio
        self.repo.save(document)
        
        # 4. Devolver el ID del documento creado
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
            {
                "id": doc.id,
                "content": doc.content,
                "score": score
            }
            for doc, score in similar_docs
        ]
        
        return results