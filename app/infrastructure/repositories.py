import numpy as np
import faiss
import sqlite3
import os
from typing import List, Tuple

from app.domain.models import (
    Document,
    DocumentID,
    Embedding,
    IDocumentRepository,
    IEmbeddingService,
)


# --- Implementación del servicio de Embeddings (simulado) ---
class MockEmbeddingService(IEmbeddingService):
    """
    Una implementación simulada para no depender de la API de OpenAI
    en esta primera fase. Genera vectores aleatorios.
    """

    def create_embedding(self, text: str) -> Embedding:
        # Dimensión de los embeddings de OpenAI (text-embedding-ada-002)
        dim = 1536
        # Simula un embedding normalizado (norma L2 = 1)
        vec = np.random.rand(dim).astype("float32")
        vec /= np.linalg.norm(vec)
        return Embedding(vec.tolist())


# --- Implementación del Repositorio de Documentos ---
class FAISSDocumentRepository(IDocumentRepository):
    def __init__(self, index_path="index.faiss", db_path="metadata.db"):
        self.index_path = index_path
        self.db_path = db_path
        self.dimension = 1536  # Dimensión de los embeddings

        self._initialize_db()
        self._load_index()

    def _initialize_db(self):
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        cursor = self.conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS documents (
                id TEXT PRIMARY KEY,
                content TEXT NOT NULL
            )
        """
        )
        self.conn.commit()

    def _load_index(self):
        if os.path.exists(self.index_path):
            self.index = faiss.read_index(self.index_path)
            # Mapeo de la posición en FAISS (0, 1, 2...) al DocumentID (UUID)
            cursor = self.conn.cursor()
            rows = cursor.execute("SELECT id FROM documents ORDER BY rowid").fetchall()
            self.id_map = [DocumentID(row[0]) for row in rows]
        else:
            self.index = faiss.IndexFlatL2(self.dimension)
            self.id_map = []

    def _save_index(self):
        faiss.write_index(self.index, self.index_path)

    def save(self, document: Document):
        # 1. Guardar metadatos en SQLite
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT OR REPLACE INTO documents (id, content) VALUES (?, ?)",
            (document.id, document.content),
        )
        self.conn.commit()

        # 2. Añadir embedding a FAISS
        embedding_np = np.array([document.embedding]).astype("float32")
        self.index.add(embedding_np)
        self.id_map.append(document.id)

        # 3. Persistir el índice FAISS en disco
        self._save_index()

    def find_by_id(self, doc_id: DocumentID) -> Document:
        # Implementación pendiente para la próxima iteración
        pass

    def find_similar(
        self, embedding: Embedding, top_k: int
    ) -> List[Tuple[Document, float]]:
        if self.index.ntotal == 0:
            return []  # No hay nada indexado

        query_vector = np.array([embedding]).astype("float32")

        # 1. Buscar en FAISS
        # D devuelve las distancias (L2), I devuelve los índices (posiciones)
        distances, indices = self.index.search(query_vector, top_k)

        results = []

        # 2. Recuperar contenido de SQLite
        cursor = self.conn.cursor()
        for i, dist in zip(indices[0], distances[0]):
            if i == -1:  # FAISS puede devolver -1 si hay menos de k resultados
                continue

            doc_id = self.id_map[i]
            cursor.execute("SELECT content FROM documents WHERE id = ?", (doc_id,))
            row = cursor.fetchone()

            if row:
                # Reconstruimos una instancia de Document para devolverla
                # El embedding no es necesario para la respuesta, así que podemos omitirlo
                doc = Document(content=row[0], embedding=[], doc_id=doc_id)
                results.append((doc, float(dist)))

        return results
