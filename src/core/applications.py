import json
from datetime import datetime, timezone
from src.config.sql_queries import (
    CREATE_APPLICATION_QUERY,
    CREATE_APPLICATION_STATUS_HISTORY_QUERY,
    GET_ALL_APPLICATIONS_QUERY,
    GET_APPLICATION_QUERY,
    GET_APPLICATIONS_BY_STATUS_QUERY,
    GET_APPLICATION_STATUS_HISTORY_QUERY,
    GET_PROFILE_APPLICATIONS_QUERY,
    GET_USER_APPLICATIONS_QUERY,
    UPDATE_APPLICATION_DETAILS_QUERY,
    UPDATE_APPLICATION_QUERY,
)
from src.database.database import DatabaseConnector
from src.exceptions import ApplicationNotFoundError, InvalidApplicationStatusError
from src.schemas.application_schema import Application, can_transition


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
                    "decision_details": self._dump_json(application.decision_details),
                    "client_data": self._dump_json(application.client_data),
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

    def get_applications_by_user(self, user_id: int) -> list[Application]:
        """Все заявки пользователя (по всем его профилям), новые сверху"""
        with self.dbConn as conn:
            rows = conn.read_data(
                sqlQuery=GET_USER_APPLICATIONS_QUERY,
                parameters={"user_id": user_id},
            )
        return [self._row_to_application(row) for row in rows]

    def get_all_applications(self, status: str | None = None) -> list[Application]:
        """Все заявки (очередь сотрудника банка), новые сверху.

        status — опциональный фильтр по статусу заявки.
        """
        if status is None:
            with self.dbConn as conn:
                rows = conn.read_data(sqlQuery=GET_ALL_APPLICATIONS_QUERY)
            return [self._row_to_application(row) for row in rows]
        with self.dbConn as conn:
            rows = conn.read_data(
                sqlQuery=GET_APPLICATIONS_BY_STATUS_QUERY,
                parameters={"status": status},
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
                    "decision_details": self._dump_json(application.decision_details),
                    "updated_at": application.updated_at.isoformat(),
                    "id": application.id,
                },
            )
        return application.id

    def update_application_details(self, application: Application) -> int | None:
        """Обновление параметров заявки (сумма/срок/платежи) без смены статуса."""
        if application.id is None or self.get_application(application.id) is None:
            return None
        with self.dbConn as conn:
            conn.load_data(
                sqlQuery=UPDATE_APPLICATION_DETAILS_QUERY,
                parameters={
                    "requested_amount": application.requested_amount,
                    "term_months": application.term_months,
                    "monthly_payment": application.monthly_payment,
                    "total_repayment": application.total_repayment,
                    "overpayment": application.overpayment,
                    "updated_at": application.updated_at.isoformat(),
                    "id": application.id,
                },
            )
        return application.id

    def add_status_history(
        self,
        application_id: int,
        from_status: str,
        to_status: str,
        actor_type: str,
        actor_id: int | None,
        comment: str | None,
        created_at: datetime,
    ) -> int:
        """Запись о смене статуса в историю заявок."""
        with self.dbConn as conn:
            return conn.load_data(
                sqlQuery=CREATE_APPLICATION_STATUS_HISTORY_QUERY,
                parameters={
                    "application_id": application_id,
                    "from_status": from_status,
                    "to_status": to_status,
                    "actor_type": actor_type,
                    "actor_id": actor_id,
                    "comment": comment,
                    "created_at": created_at.isoformat(),
                },
            )

    def get_status_history(self, application_id: int) -> list[dict]:
        """История смены статуса заявки, от ранней записи к поздней."""
        with self.dbConn as conn:
            rows = conn.read_data(
                sqlQuery=GET_APPLICATION_STATUS_HISTORY_QUERY,
                parameters={"application_id": application_id},
            )
        return [
            {
                "id": row["id"],
                "application_id": row["application_id"],
                "from_status": row["from_status"],
                "to_status": row["to_status"],
                "actor_type": row["actor_type"],
                "actor_id": row["actor_id"],
                "comment": row["comment"],
                "created_at": row["created_at"],
            }
            for row in rows
        ]

    @staticmethod
    def _dump_json(value: dict | None) -> str | None:
        if value is None:
            return None
        return json.dumps(value, ensure_ascii=False)

    @staticmethod
    def _load_json(value: str | None) -> dict | None:
        if not value:
            return None
        return json.loads(value)

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
            decision_details=ApplicationRepository._load_json(row["decision_details"]),
            client_data=ApplicationRepository._load_json(row["client_data"]),
            id=row["id"],
        )

def transition_application(
    application: Application,
    target_status: str,
    actor_type: str,
    actor_id: int | None,
    app_rep: ApplicationRepository,
    comment: str | None = None,
) -> Application:
    """Единая точка смены статуса заявки.

    Проверяет переход по матрице ALLOWED_TRANSITIONS, обновляет статус и
    updated_at, сохраняет заявку и пишет запись в application_status_history.
    Скоринговые поля (score/decision/decision_details) вызывающий код задаёт
    на объекте заявки до вызова — они сохраняются тем же UPDATE-запросом.
    Возвращает заявку, перечитанную из БД.
    """
    if not can_transition(application.status, target_status):
        raise InvalidApplicationStatusError(
            f"Недопустимый переход статуса: {application.status!r} -> {target_status!r}"
        )
    from_status = application.status
    application.status = target_status
    application.updated_at = datetime.now(timezone.utc)
    if app_rep.update_application(application) is None:
        raise ApplicationNotFoundError(f"Заявка id={application.id} не найдена")
    app_rep.add_status_history(
        application_id=application.id,
        from_status=from_status,
        to_status=target_status,
        actor_type=actor_type,
        actor_id=actor_id,
        comment=comment,
        created_at=application.updated_at,
    )
    return app_rep.get_application(application.id)