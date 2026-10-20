import hashlib
import secrets
from src.config.database_config import PBKDF2_ITERATIONS
from src.core.auth.auth import AuthRepository
from src.exceptions import InvalidCredentialsError, InvalidRoleError, UsernameTakenError
from src.schemas.auth_schema import User
from src.config.database_config import ALLOWED_ROLES


def hash_password(password: str, salt: str) -> str:
    """Хеш пароля PBKDF2-HMAC-SHA256 с hex-солью."""
    return hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), bytes.fromhex(salt), PBKDF2_ITERATIONS
    ).hex()



def register_user(rep: AuthRepository, username: str, password: str, role: str = "client") -> tuple[User, str]:
    """Регистрация нового пользователя. Возвращает (User, token)"""
    if role not in ALLOWED_ROLES:
        raise InvalidRoleError(
            f"Неизвестная роль '{role}'. Доступны: {', '.join(ALLOWED_ROLES)}"
        )
    if rep.get_user_by_username(username) is not None:
        raise UsernameTakenError(f"Логин '{username}' уже занят")
    salt = secrets.token_hex(16)
    user_id = rep.create_user(username, hash_password(password, salt), salt, role)
    user = rep.get_user_by_id(user_id)
    token = rep.create_token(user_id)
    return user, token


def login_user(rep: AuthRepository, username: str, password: str) -> tuple[User, str]:
    """Вход по логину и паролю. Возвращает (User, token)"""
    found = rep.get_user_by_username(username)
    if found is None:
        raise InvalidCredentialsError("Неверный логин или пароль")
    user, password_hash, salt = found
    if not secrets.compare_digest(hash_password(password, salt), password_hash):
        raise InvalidCredentialsError("Неверный логин или пароль")
    token = rep.create_token(user.id)
    return user, token

def user_response(user: User) -> dict:
    """Публичное представление пользователя (без хеша пароля)."""
    return {
        "id": user.id,
        "username": user.username,
        "role": user.role,
        "created_at": user.created_at.isoformat(),
    }

def get_user_by_token(rep: AuthRepository, token: str) -> User | None:
    """Пользователь по токену сессии (None, если токен неизвестен)."""
    return rep.get_user_by_token(token)