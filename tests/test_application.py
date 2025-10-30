import pytest
from app.application.use_cases import RegisterUserUseCase, LoginUserUseCase
from app.infrastructure.repositories import UserRepository, TokenRepository
from app.domain.models import User

# --- Pruebas para RegisterUserUseCase ---


def test_register_user_success(tmp_path):
    """Verifica que un usuario puede registrarse correctamente."""
    user_repo = UserRepository(db_path=tmp_path / "test.db")
    use_case = RegisterUserUseCase(user_repo=user_repo)

    user = use_case.execute("test@example.com", "password123", "Test User")

    assert user.id is not None
    assert user.email == "test@example.com"
    assert user.name == "Test User"


def test_register_user_with_existing_email_fails(tmp_path):
    """Verifica que no se puede registrar un usuario con un email que ya existe."""
    user_repo = UserRepository(db_path=tmp_path / "test.db")
    use_case = RegisterUserUseCase(user_repo=user_repo)

    # Registramos el primer usuario
    use_case.execute("test@example.com", "password123", "Test User")

    # Intentamos registrar de nuevo con el mismo email
    with pytest.raises(ValueError, match="El email ya está en uso."):
        use_case.execute("test@example.com", "password456", "Another User")


# --- Pruebas para LoginUserUseCase ---


def test_login_user_success(tmp_path):
    """Verifica que un usuario registrado puede iniciar sesión."""
    user_repo = UserRepository(db_path=tmp_path / "users.db")
    token_repo = TokenRepository(db_path=tmp_path / "tokens.db")

    # Primero, registramos un usuario
    register_uc = RegisterUserUseCase(user_repo=user_repo)
    register_uc.execute("login@example.com", "password123", "Login User")

    # Ahora, intentamos hacer login
    login_uc = LoginUserUseCase(user_repo=user_repo, token_repo=token_repo)
    result = login_uc.execute("login@example.com", "password123")

    assert "access_token" in result
    assert "refresh_token" in result
    assert result["user"].email == "login@example.com"


def test_login_with_wrong_password_fails(tmp_path):
    """Verifica que el login falla con una contraseña incorrecta."""
    user_repo = UserRepository(db_path=tmp_path / "users.db")
    token_repo = TokenRepository(db_path=tmp_path / "tokens.db")

    register_uc = RegisterUserUseCase(user_repo=user_repo)
    register_uc.execute("login@example.com", "password123", "Login User")

    login_uc = LoginUserUseCase(user_repo=user_repo, token_repo=token_repo)
    with pytest.raises(ValueError, match="Credenciales inválidas."):
        login_uc.execute("login@example.com", "wrongpassword")


def test_login_with_non_existent_user_fails(tmp_path):
    """Verifica que el login falla si el usuario no existe."""
    user_repo = UserRepository(db_path=tmp_path / "users.db")
    token_repo = TokenRepository(db_path=tmp_path / "tokens.db")

    login_uc = LoginUserUseCase(user_repo=user_repo, token_repo=token_repo)
    with pytest.raises(ValueError, match="Credenciales inválidas."):
        login_uc.execute("non-existent@example.com", "password123")
