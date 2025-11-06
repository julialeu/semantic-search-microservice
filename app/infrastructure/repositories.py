import os
import sqlite3
import uuid
from datetime import datetime, timezone, timedelta
from typing import List, Tuple

import faiss
import numpy as np
import openai
from dotenv import load_dotenv

from app.domain.models import (
    Document,
    DocumentID,
    Embedding,
    IDocumentRepository,
    IEmbeddingService,
    User,
)


# --- IMPLEMENTACIÓN REAL DEL SERVICIO DE EMBEDDINGS ---
class OpenAIEmbeddingService(IEmbeddingService):
    """
    Implementación real que llama a la API de OpenAI para generar embeddings.
    """

    def __init__(self):
        load_dotenv()
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError(
                "La variable de entorno OPENAI_API_KEY no está configurada."
            )
        self.client = openai.OpenAI(api_key=api_key)
        self.model = "text-embedding-3-small"

    def create_embedding(self, text: str) -> Embedding:
        text = text.replace("\n", " ")
        response = self.client.embeddings.create(input=[text], model=self.model)
        return Embedding(response.data[0].embedding)


# --- IMPLEMENTACIÓN DEL REPOSITORIO DE DOCUMENTOS ---
class FAISSDocumentRepository(IDocumentRepository):
    """
    Repositorio que utiliza FAISS para la búsqueda vectorial y SQLite para los metadatos.
    """

    def __init__(
        self, index_path: str = "data/index.faiss", db_path: str = "data/metadata.db"
    ):
        self.index_path = index_path
        self.db_path = db_path
        self.dimension = 1536
        os.makedirs(os.path.dirname(self.index_path), exist_ok=True)
        self._initialize_db()
        self._load_or_create_index()

    def _initialize_db(self):
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        cursor = self.conn.cursor()
        cursor.execute(
            "CREATE TABLE IF NOT EXISTS documents (id TEXT PRIMARY KEY, content TEXT NOT NULL)"
        )
        self.conn.commit()

    def _load_or_create_index(self):
        if os.path.exists(self.index_path):
            self.index = faiss.read_index(self.index_path)
        else:
            self.index = faiss.IndexIDMap2(faiss.IndexFlatL2(self.dimension))

    def _save_index(self):
        faiss.write_index(self.index, self.index_path)

    def save(self, document: Document):
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT OR REPLACE INTO documents (id, content) VALUES (?, ?)",
            (document.id, document.content),
        )
        doc_int_id = cursor.lastrowid
        self.conn.commit()
        embedding_np = np.array([document.embedding]).astype("float32")
        self.index.add_with_ids(embedding_np, np.array([doc_int_id]))
        self._save_index()

    def delete(self, doc_id: DocumentID):
        cursor = self.conn.cursor()
        cursor.execute("SELECT rowid FROM documents WHERE id = ?", (doc_id,))
        result = cursor.fetchone()
        if result is None:
            return
        doc_int_id = result[0]
        self.index.remove_ids(np.array([doc_int_id]))
        cursor.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
        self.conn.commit()
        self._save_index()

    def find_similar(
        self, embedding: Embedding, top_k: int
    ) -> List[Tuple[Document, float]]:
        if self.index.ntotal == 0:
            return []
        query_vector = np.array([embedding]).astype("float32")
        distances, doc_int_ids = self.index.search(query_vector, top_k)
        results = []
        cursor = self.conn.cursor()
        for i, dist in zip(doc_int_ids[0], distances[0]):
            if i == -1:
                continue
            cursor.execute(
                "SELECT id, content FROM documents WHERE rowid = ?", (int(i),)
            )
            row = cursor.fetchone()
            if row:
                doc_uuid, content = row
                doc = Document(
                    content=content, embedding=[], doc_id=DocumentID(doc_uuid)
                )
                results.append((doc, float(dist)))
        return results


class UserRepository:
    """
    Repositorio para gestionar los datos de los usuarios en la base de datos.
    """

    def __init__(self, db_path: str = "data/users.db"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._initialize_db()

    def _initialize_db(self):
        cursor = self.conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                email TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                hashed_password TEXT NOT NULL,
                is_verified BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP
            )"""
        )
        self.conn.commit()

    def save(self, user: User) -> User:
        cursor = self.conn.cursor()
        user.id = str(uuid.uuid4())
        user.created_at = datetime.now(timezone.utc)
        cursor.execute(
            "INSERT INTO users (id, email, name, hashed_password, is_verified, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (
                user.id,
                user.email,
                user.name,
                user.hashed_password,
                user.is_verified,
                user.created_at,
            ),
        )
        self.conn.commit()
        return user

    def find_by_email(self, email: str) -> User | None:
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT id, email, name, hashed_password, is_verified FROM users WHERE email = ?",
            (email,),
        )
        row = cursor.fetchone()
        if row:
            return User(
                id=row[0],
                email=row[1],
                name=row[2],
                hashed_password=row[3],
                is_verified=bool(row[4]),
            )
        return None

    def find_by_id(self, user_id: str) -> User | None:
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT id, email, name, hashed_password, is_verified FROM users WHERE id = ?",
            (user_id,),
        )
        row = cursor.fetchone()
        if row:
            return User(
                id=row[0],
                email=row[1],
                name=row[2],
                hashed_password=row[3],
                is_verified=bool(row[4]),
            )
        return None


class TokenRepository:
    """
    Repositorio para gestionar los tokens (refresh, verificación, etc.) en la base de datos.
    """

    def __init__(self, db_path: str = "data/tokens.db"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._initialize_db()

    def _initialize_db(self):
        cursor = self.conn.cursor()

        # --- Tabla de Refresh Tokens  ---
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS refresh_tokens (
                token TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                expires_at TIMESTAMP NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_revoked BOOLEAN DEFAULT FALSE,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )"""
        )

        # --- NUEVA TABLA: Email Verification Tokens ---
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS email_verification_tokens (
                token TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                expires_at TIMESTAMP NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )"""
        )

        # --- NUEVA TABLA: Password Reset Tokens ---
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS password_reset_tokens (
                token TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                expires_at TIMESTAMP NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_used BOOLEAN DEFAULT FALSE,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )"""
        )

        self.conn.commit()

    def save_refresh_token(
        self, refresh_token: str, user_id: str, expires_at: datetime
    ):
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT INTO refresh_tokens (token, user_id, expires_at) VALUES (?, ?, ?)",
            (refresh_token, user_id, expires_at),
        )
        self.conn.commit()

    def save_email_verification_token(self, token: str, user_id: str) -> None:
        expires_at = datetime.now(timezone.utc) + timedelta(
            hours=24
        )  # 24 horas de validez
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT INTO email_verification_tokens (token, user_id, expires_at) VALUES (?, ?, ?)",
            (token, user_id, expires_at),
        )
        self.conn.commit()

    def find_email_verification_token(self, token: str) -> dict | None:
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT user_id, expires_at FROM email_verification_tokens WHERE token = ?",
            (token,),
        )
        row = cursor.fetchone()
        if row:
            return {"user_id": row[0], "expires_at": datetime.fromisoformat(row[1])}
        return None

    def delete_email_verification_token(self, token: str) -> None:
        cursor = self.conn.cursor()
        cursor.execute(
            "DELETE FROM email_verification_tokens WHERE token = ?", (token,)
        )
        self.conn.commit()

    def save_password_reset_token(self, token: str, user_id: str) -> None:
        expires_at = datetime.now(timezone.utc) + timedelta(
            hours=1
        )  # 1 hora de validez
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT INTO password_reset_tokens (token, user_id, expires_at) VALUES (?, ?, ?)",
            (token, user_id, expires_at),
        )
        self.conn.commit()

    def find_password_reset_token(self, token: str) -> dict | None:
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT user_id, expires_at, is_used FROM password_reset_tokens WHERE token = ?",
            (token,),
        )
        row = cursor.fetchone()
        if row:
            return {
                "user_id": row[0],
                "expires_at": datetime.fromisoformat(row[1]),
                "is_used": bool(row[2]),
            }
        return None

    def mark_password_reset_token_as_used(self, token: str) -> None:
        cursor = self.conn.cursor()
        cursor.execute(
            "UPDATE password_reset_tokens SET is_used = TRUE WHERE token = ?", (token,)
        )
        self.conn.commit()
