import numpy as np
import faiss
import sqlite3
import os
from typing import List, Tuple
import openai
from dotenv import load_dotenv

from app.domain.models import (
    Document,
    DocumentID,
    Embedding,
    IDocumentRepository,
    IEmbeddingService,
)


# --- IMPLEMENTACIÓN REAL DEL SERVICIO DE EMBEDDINGS ---
class OpenAIEmbeddingService(IEmbeddingService):
    """
    Implementación real que llama a la API de OpenAI para generar embeddings.
    """

    def __init__(self):
        load_dotenv()  # Carga las variables del fichero .env
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError(
                "La variable de entorno OPENAI_API_KEY no está configurada."
            )
        self.client = openai.OpenAI(api_key=api_key)
        self.model = "text-embedding-3-small"  # Modelo eficiente y de bajo coste

    def create_embedding(self, text: str) -> Embedding:
        # Reemplazar saltos de línea para evitar problemas con algunos modelos
        text = text.replace("\n", " ")
        response = self.client.embeddings.create(input=[text], model=self.model)
        return Embedding(response.data[0].embedding)


# --- IMPLEMENTACIÓN DEL REPOSITORIO DE DOCUMENTOS ---
class FAISSDocumentRepository(IDocumentRepository):
    """
    Repositorio que utiliza FAISS para la búsqueda vectorial y SQLite para los metadatos.
    Soporta la adición, búsqueda y eliminación de documentos.
    """

    def __init__(
        self,
        index_path: str = "/app/data/index.faiss",
        db_path: str = "/app/data/metadata.db",
    ):
        self.index_path = index_path
        self.db_path = db_path
        self.dimension = 1536  # Dimensión de text-embedding-3-small

        os.makedirs(os.path.dirname(self.index_path), exist_ok=True)

        self._initialize_db()
        self._load_or_create_index()

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

    def _load_or_create_index(self):
        if os.path.exists(self.index_path):
            self.index = faiss.read_index(self.index_path)
        else:
            # IndexIDMap2 permite mapear un ID de 64 bits a un vector.
            self.index = faiss.IndexIDMap2(faiss.IndexFlatL2(self.dimension))

    def _save_index(self):
        faiss.write_index(self.index, self.index_path)

    def save(self, document: Document):
        # 1. Guardar metadatos en SQLite para obtener el rowid
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT OR REPLACE INTO documents (id, content) VALUES (?, ?)",
            (document.id, document.content),
        )
        # Obtenemos el rowid
        doc_int_id = cursor.lastrowid
        self.conn.commit()

        # 2. Añadir embedding a FAISS usando el rowid como ID
        embedding_np = np.array([document.embedding]).astype("float32")
        self.index.add_with_ids(embedding_np, np.array([doc_int_id]))

        # 3. Persistir el índice FAISS en disco
        self._save_index()

    def delete(self, doc_id: DocumentID):
        cursor = self.conn.cursor()

        # 1. Obtener el rowid de SQLite a partir del UUID
        cursor.execute("SELECT rowid FROM documents WHERE id = ?", (doc_id,))
        result = cursor.fetchone()

        if result is None:
            # TODO: lanzar un error si el documento no existe
            return

        doc_int_id = result[0]

        # 2. Eliminar de FAISS usando el rowid
        self.index.remove_ids(np.array([doc_int_id]))

        # 3. Eliminar de SQLite usando el UUID
        cursor.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
        self.conn.commit()

        # 4. Persistir cambios en el índice
        self._save_index()

    def find_similar(
        self, embedding: Embedding, top_k: int
    ) -> List[Tuple[Document, float]]:
        if self.index.ntotal == 0:
            return []

        query_vector = np.array([embedding]).astype("float32")

        # 1. Buscar en FAISS. Devuelve distancias y los rowids
        distances, doc_int_ids = self.index.search(query_vector, top_k)

        results = []
        cursor = self.conn.cursor()

        # 2. Usar los rowids para recuperar el contenido y el UUID de SQLite
        for i, dist in zip(doc_int_ids[0], distances[0]):
            if i == -1:
                continue

            cursor.execute(
                "SELECT id, content FROM documents WHERE rowid = ?", (int(i),)
            )
            row = cursor.fetchone()

            if row:
                doc_uuid, content = row
                # Reconstruimos el objeto Document para devolverlo
                doc = Document(
                    content=content, embedding=[], doc_id=DocumentID(doc_uuid)
                )
                results.append((doc, float(dist)))

        return results
