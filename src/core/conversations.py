from datetime import datetime
from src.database.database import DatabaseConnector
from src.schemas.conversation_schema import Conversation, Message
from src.config.sql_queries import (
    CREATE_CONVERSATION_QUERY,
    GET_CONVERSATION_QUERY,
    GET_MESSAGES_QUERY,
    LIST_CONVERSATIONS_QUERY,
    SEND_MESSAGE_CONVERSATION_QUERY,
)

class ConversationRepository:
    def __init__(self, dbConn: DatabaseConnector):
        self.dbConn: DatabaseConnector = dbConn
    
    def create_conversation(self, conversation: Conversation) -> int:
        """Создание обсуждения в БД. Возвращает id, сгенерированный БД."""
        with self.dbConn as conn:
            return conn.load_data(
                sqlQuery=CREATE_CONVERSATION_QUERY,
                parameters={
                    "state": conversation.state,
                    "created_at": str(conversation.created_at.isoformat()),
                    "updated_at": str(conversation.updated_at.isoformat())
                })
    
    def get_conversation(self, conversation_id: int) -> Conversation | None:
        """Получение обсуждения по id. Возвращает None, если не найдено"""
        with self.dbConn as conn:
            rows = conn.read_data(
                sqlQuery=GET_CONVERSATION_QUERY,
                parameters={"id": conversation_id}
            )
        if not rows:
            return None
        row = rows[0]
        return Conversation(
            state=row["state"],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
            id=row["id"],
        )

    def get_conversations(self) -> list[Conversation]:
        """Все диалоги, свежие сверху (для восстановления истории в UI)."""
        with self.dbConn as conn:
            rows = conn.read_data(sqlQuery=LIST_CONVERSATIONS_QUERY)
        return [
            Conversation(
                state=row["state"],
                created_at=datetime.fromisoformat(row["created_at"]),
                updated_at=datetime.fromisoformat(row["updated_at"]),
                id=row["id"],
            )
            for row in rows
        ]
    
    def send_conversation_message(self, message: Message) -> int:
        """Запись сообщения в БД. Возвращает id, сгенерированный БД"""
        with self.dbConn as conn:
            return conn.load_data(
                sqlQuery=SEND_MESSAGE_CONVERSATION_QUERY,
                parameters={
                    "conversation_id": message.conversation_id,
                    "role": message.role,
                    "content": message.content,
                    "created_at": str(message.created_at.isoformat())
                }
            )

    def get_conversation_messages(self, conversation_id: int) -> list[Message]:
        """Все сообщения диалога в хронологическом порядке (для контекста LLM)"""
        with self.dbConn as conn:
            rows = conn.read_data(
                sqlQuery=GET_MESSAGES_QUERY,
                parameters={"conversation_id": conversation_id},
            )
        return [
            Message(
                conversation_id=row["conversation_id"],
                role=row["role"],
                content=row["content"],
                created_at=datetime.fromisoformat(row["created_at"]),
                id=row["id"],
            )
            for row in rows
        ]
        