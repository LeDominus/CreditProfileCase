import json
from datetime import datetime
from src.config.sql_queries import (
    CREATE_APPLICATION_QUERY,
    GET_APPLICATION_QUERY,
    GET_PROFILE_APPLICATIONS_QUERY,
    UPDATE_APPLICATION_QUERY,
)
from src.database.database import DatabaseConnector
from src.schemas.application_schema import Application


class ApplicationRepository:
    def __init__(self, dbConn: DatabaseConnector):
        self.dbConn: DatabaseConnector = dbConn

    def create_application(self, application: Application) -> int:
        """Создание заявки в БД. Возвращает id, сгенерированный БД"""
        with self.dbConn as conn:
            return conn.load_data(
                sqlQuery=CREATE_APPLICATION_QUERY,
                parameters={
                    "profile_id": application.profile_id,
                    "product_id": application.product_id,
                    "product_name": application.product_name,
                    "requested_amount": application.requested_amount,
                    "term_months": application.term_months,
                    "monthly_payment": application.monthly_payment,
                    "total_repayment": application.total_repayment,
                    "overpayment": application.overpayment,
                    "status": application.status,
                    "score": application.score,
                    "decision": application.decision,
                    "decision_details": self._dump_details(application.decision_details),
                    "created_at": application.created_at.isoformat(),
                    "updated_at": application.updated_at.isoformat(),
                },
            )

    def get_application(self, application_id: int) -> Application | None:
        """Получение заявки по id. Возвращает None, если заявка не найдена"""
        with self.dbConn as conn:
            rows = conn.read_data(
                sqlQuery=GET_APPLICATION_QUERY,
                parameters={"id": application_id},
            )
        if not rows:
            return None
        return self._row_to_application(rows[0])

    def get_applications_by_profile(self, profile_id: int) -> list[Application]:
        """Все заявки профиля, новые сверху"""
        with self.dbConn as conn:
            rows = conn.read_data(
                sqlQuery=GET_PROFILE_APPLICATIONS_QUERY,
                parameters={"profile_id": profile_id},
            )
        return [self._row_to_application(row) for row in rows]

    def update_application(self, application: Application) -> int | None:
        """Обновление статуса и результата скоринга"""
        if application.id is None or self.get_application(application.id) is None:
            return None
        with self.dbConn as conn:
            conn.load_data(
                sqlQuery=UPDATE_APPLICATION_QUERY,
                parameters={
                    "status": application.status,
                    "score": application.score,
                    "decision": application.decision,
                    "decision_details": self._dump_details(application.decision_details),
                    "updated_at": application.updated_at.isoformat(),
                    "id": application.id,
                },
            )
        return application.id

    @staticmethod
    def _dump_details(decision_details: dict | None) -> str | None:
        if decision_details is None:
            return None
        return json.dumps(decision_details, ensure_ascii=False)

    @staticmethod
    def _row_to_application(row: dict) -> Application:
        return Application(
            profile_id=row["profile_id"],
            product_id=row["product_id"],
            product_name=row["product_name"],
            requested_amount=row["requested_amount"],
            term_months=row["term_months"],
            monthly_payment=row["monthly_payment"],
            total_repayment=row["total_repayment"],
            overpayment=row["overpayment"],
            status=row["status"],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
            score=row["score"],
            decision=row["decision"],
            decision_details=json.loads(row["decision_details"]) if row["decision_details"] else None,
            id=row["id"],
        )