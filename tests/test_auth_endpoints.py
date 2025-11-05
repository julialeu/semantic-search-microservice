import pytest
from fastapi.testclient import TestClient
from app.interfaces.api import app, get_user_repo, get_token_repo
from app.infrastructure.repositories import UserRepository, TokenRepository


@pytest.fixture
def client_auth(tmp_path):
    """Fixture que crea repositorios temporales y un cliente de prueba."""
    user_repo_temp = UserRepository(db_path=tmp_path / "test_users.db")
    token_repo_temp = TokenRepository(db_path=tmp_path / "test_tokens.db")

    app.dependency_overrides[get_user_repo] = lambda: user_repo_temp
    app.dependency_overrides[get_token_repo] = lambda: token_repo_temp

    with TestClient(app) as client:
        yield client

    app.dependency_overrides = {}


# --- Pruebas de Registro ---
def test_register_user_success(client_auth):
    """Un usuario puede registrarse con datos válidos."""
    response = client_auth.post(
        "/auth/register",
        json={
            "email": "test@example.com",
            "password": "a-strong-password",
            "name": "Test User",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert "user_id" in data
    assert data["message"] == "Usuario registrado exitosamente."


def test_register_existing_user_fails(client_auth):
    """No se puede registrar un usuario con un email que ya existe."""
    # Primer registro
    client_auth.post(
        "/auth/register",
        json={
            "email": "test@example.com",
            "password": "a-strong-password",
            "name": "Test User",
        },
    )

    # Segundo intento con el mismo email
    response = client_auth.post(
        "/auth/register",
        json={
            "email": "test@example.com",
            "password": "another-password",
            "name": "Another User",
        },
    )
    assert response.status_code == 400
    assert "El email ya está en uso" in response.json()["detail"]


# --- Pruebas de Login ---
def test_login_success(client_auth):
    """Un usuario registrado puede iniciar sesión con credenciales correctas."""
    # 1. Registrar usuario
    client_auth.post(
        "/auth/register",
        json={
            "email": "login@example.com",
            "password": "password123",
            "name": "Login User",
        },
    )

    # 2. Iniciar sesión
    response = client_auth.post(
        "/auth/login",
        data={"username": "login@example.com", "password": "password123"},
    )

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == "login@example.com"


def test_login_wrong_password_fails(client_auth):
    """El login falla si la contraseña es incorrecta."""
    client_auth.post(
        "/auth/register",
        json={
            "email": "login@example.com",
            "password": "password123",
            "name": "Login User",
        },
    )
    response = client_auth.post(
        "/auth/login",
        data={"username": "login@example.com", "password": "wrong-password"},
    )
    assert response.status_code == 401
    assert "Credenciales inválidas" in response.json()["detail"]
