from datetime import datetime
from src.database.database import DatabaseConnector
from src.schemas.profile_schema import BusinessProfile
from src.config.sql_queries import (
    CREATE_PROFILE_QUERY,
    GET_PROFILE_QUERY,
    UPDATE_PROFILE_QUERY,
)


class ProfileRepository:
    def __init__(self, dbConn: DatabaseConnector):
        self.dbConn: DatabaseConnector = dbConn

    def create_profile(self, profile: BusinessProfile) -> int:
        """Создание записи профиля в БД. Возвращает id, сгенерированный БД."""
        with self.dbConn as conn:
            return conn.load_data(
                sqlQuery=CREATE_PROFILE_QUERY,
                parameters={
                    "user_id": profile.user_id,
                    "business_name": profile.business_name,
                    "industry": profile.industry,
                    "funding_purpose": profile.funding_purpose,
                    "requested_amount": profile.requested_amount,
                    "business_age_months": profile.business_age_months,
                    "monthly_revenue": profile.monthly_revenue,
                    "monthly_profit": profile.monthly_profit,
                    "preferred_term_months": profile.preferred_term_months,
                    "max_monthly_payment": profile.max_monthly_payment,
                    "created_at": str(profile.created_at.isoformat()),
                    "updated_at": str(profile.updated_at.isoformat()),
                }
            )

    def get_profile(self, profile_id: int) -> BusinessProfile | None:
        """Получение профиля из БД по id. Возвращает None, если профиль не найден."""
        with self.dbConn as conn:
            rows = conn.read_data(
                sqlQuery=GET_PROFILE_QUERY,
                parameters={"id": profile_id}
            )
        if not rows:
            return None
        row = rows[0]
        return BusinessProfile(
            user_id=row["user_id"],
            business_name=row["business_name"],
            industry=row["industry"],
            funding_purpose=row["funding_purpose"],
            requested_amount=row["requested_amount"],
            business_age_months=row["business_age_months"],
            monthly_revenue=row["monthly_revenue"],
            monthly_profit=row["monthly_profit"],
            preferred_term_months=row["preferred_term_months"],
            max_monthly_payment=row["max_monthly_payment"],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
            id=row["id"],
        )

    def update_profile(self, profile: BusinessProfile) -> int | None:
        """Обновление записи профиля в БД. Возвращает id профиля, None — если профиль не найден."""
        if profile.id is None or self.get_profile(profile.id) is None:
            return None
        with self.dbConn as conn:
            conn.load_data(
                sqlQuery=UPDATE_PROFILE_QUERY,
                parameters={
                    "business_name": profile.business_name,
                    "industry": profile.industry,
                    "funding_purpose": profile.funding_purpose,
                    "requested_amount": profile.requested_amount,
                    "business_age_months": profile.business_age_months,
                    "monthly_revenue": profile.monthly_revenue,
                    "monthly_profit": profile.monthly_profit,
                    "preferred_term_months": profile.preferred_term_months,
                    "max_monthly_payment": profile.max_monthly_payment,
                    "updated_at": str(profile.updated_at.isoformat()),
                    "id": profile.id,
                }
            )
        return profile.id