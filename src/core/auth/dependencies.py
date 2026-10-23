from fastapi import Depends, Header, HTTPException, status
from src.core.auth.auth import AuthRepository
from src.core.auth.auth_service_methods import get_user_by_token
from src.DI import load_auth_repository
from src.schemas.auth_schema import User


def get_current_user(
    authorization: str = Header(default=None),
    auth_rep: AuthRepository = Depends(load_auth_repository),
) -> User:
    """Текущий пользователь по заголовку Authorization: Bearer <token>."""
    token = None
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1].strip()
    user = get_user_by_token(auth_rep, token) if token else None
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Требуется действительный заголовок Authorization: Bearer <token>",
        )
    return user


def require_role(*roles: str):
    """Фабрика зависимостей: пользователь с одной из указанных ролей, иначе 403."""
    def dependency(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Требуется одна из ролей: {', '.join(roles)}",
            )
        return user
    return dependency
