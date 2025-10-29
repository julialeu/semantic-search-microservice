import os
import pytest
from datetime import datetime, timezone

from app.infrastructure.security import (
    get_password_hash,
    verify_password,
    create_access_token,
    decode_token,
)
from app.infrastructure.repositories import UserRepository
from app.domain.models import User

# --- 1. Unit Tests para security.py ---

def test_password_hashing_and_verification():
    """
    Verifica que una contraseña se hashea correctamente y que la verificación funciona.
    """
    password = "mySuperSecurePassword123"
    hashed_password = get_password_hash(password)

    # El hash no debe ser igual a la contraseña original
    assert hashed_password != password
    # La verificación con la contraseña correcta debe ser True
    assert verify_password(password, hashed_password) is True
    # La verificación con una contraseña incorrecta debe ser False
    assert verify_password("wrongPassword", hashed_password) is False

def test_jwt_token_creation_and_decoding():
    """
    Verifica que se puede crear un token JWT y decodificarlo para obtener los datos originales.
    """
    user_data = {"user_id": "test_user_123", "email": "test@example.com"}
    token = create_access_token(data=user_data)

    decoded_payload = decode_token(token)

    assert decoded_payload is not None
    assert decoded_payload["user_id"] == user_data["user_id"]
    assert decoded_payload["email"] == user_data["email"]
    assert "exp" in decoded_payload  # El token debe tener una fecha de expiración
    assert "type" in decoded_payload and decoded_payload["type"] == "access"

def test_decode_invalid_token_returns_none():
    """
    Verifica que decodificar un token inválido o malformado devuelve None.
    """
    invalid_token = "this.is.not.a.valid.token"
    assert decode_token(invalid_token) is None


# --- 2. Integration Tests para UserRepository ---

def test_user_repository_save_and_find_by_email(tmp_path):
    """
    Verifica que se puede guardar un usuario y luego encontrarlo por su email.
    `tmp_path` es una fixture de pytest que crea un directorio temporal para la prueba.
    """
    # Usamos una base de datos temporal para no afectar la real
    db_path = tmp_path / "test_users.db"
    repo = UserRepository(db_path=str(db_path))

    # Creamos un usuario de prueba
    new_user = User(
        id=None, # El ID se genera al guardar
        email="test.user@example.com",
        name="Test User",
        hashed_password=get_password_hash("password123"),
        is_verified=False
    )

    # Guardamos el usuario
    saved_user = repo.save(new_user)

    # Verificamos que se le asignó un ID y una fecha de creación
    assert saved_user.id is not None
    assert saved_user.created_at is not None

    # Buscamos el usuario por su email
    found_user = repo.find_by_email("test.user@example.com")

    assert found_user is not None
    assert found_user.id == saved_user.id
    assert found_user.email == "test.user@example.com"
    assert found_user.name == "Test User"

def test_find_non_existent_user_returns_none(tmp_path):
    """
    Verifica que buscar un usuario que no existe devuelve None.
    """
    db_path = tmp_path / "test_users.db"
    repo = UserRepository(db_path=str(db_path))

    found_user = repo.find_by_email("non.existent@example.com")
    assert found_user is None