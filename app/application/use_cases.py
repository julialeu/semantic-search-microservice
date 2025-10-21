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