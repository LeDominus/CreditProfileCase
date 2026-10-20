class ScoringError(Exception):
    """Базовая ошибка конвейера скоринга заявки."""


class ApplicationNotFoundError(ScoringError):
    """Заявка не найдена."""


class InvalidApplicationStatusError(ScoringError):
    """Недопустимый статус заявки или переход статусов."""


class ProfileNotFoundError(ScoringError):
    """Профиль, на который ссылается заявка, не найден."""


class ProductNotFoundError(ScoringError):
    """Продукт, на который ссылается заявка, не найден."""


class ScoringRepositoryError(ScoringError):
    """Сбой доступа к БД при скоринге заявки."""
    

class UsernameTakenError(Exception):
    """Логин уже занят."""


class InvalidCredentialsError(Exception):
    """Неверный логин или пароль."""


class InvalidRoleError(Exception):
    """Неизвестная роль пользователя."""