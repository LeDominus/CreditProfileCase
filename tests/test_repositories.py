"""Интеграционные тесты репозиториев на временной SQLite."""

from datetime import datetime, timezone

from src.schemas.conversation_schema import Conversation, Message


def make_profile(**overrides):
    base = dict(
        business_name="ООО Ромашка",
        industry="общепит",
        funding_purpose="Пополнение оборотных средств",
        requested_amount=1_500_000.0,
        business_age_months=24,
        monthly_revenue=2_000_000.0,
        monthly_profit=300_000.0,
        preferred_term_months=24,
        max_monthly_payment=120_000.0,
    )
    base.update(overrides)
    from src.schemas.profile_schema import BusinessProfile

    return BusinessProfile(**base)


class TestProfileRepository:
    def test_create_and_get_roundtrip(self, profile_repo):
        profile_id = profile_repo.create_profile(make_profile())
        assert isinstance(profile_id, int)

        loaded = profile_repo.get_profile(profile_id)
        assert loaded is not None
        assert loaded.id == profile_id
        assert loaded.business_name == "ООО Ромашка"
        assert loaded.industry == "общепит"
        assert loaded.requested_amount == 1_500_000.0
        assert loaded.preferred_term_months == 24

    def test_get_missing_returns_none(self, profile_repo):
        assert profile_repo.get_profile(999) is None

    def test_update_profile(self, profile_repo):
        profile = make_profile()
        profile_id = profile_repo.create_profile(profile)

        profile.id = profile_id
        profile.requested_amount = 3_000_000.0
        profile.updated_at = datetime.now(timezone.utc)
        assert profile_repo.update_profile(profile) == profile_id

        loaded = profile_repo.get_profile(profile_id)
        assert loaded.requested_amount == 3_000_000.0

    def test_update_missing_returns_none(self, profile_repo):
        profile = make_profile(id=999)
        assert profile_repo.update_profile(profile) is None


class TestConversationRepository:
    def test_create_and_get_roundtrip(self, conv_repo):
        conversation = Conversation(state="new")
        conversation_id = conv_repo.create_conversation(conversation)

        loaded = conv_repo.get_conversation(conversation_id)
        assert loaded is not None
        assert loaded.id == conversation_id
        assert loaded.state == "new"

    def test_get_missing_returns_none(self, conv_repo):
        assert conv_repo.get_conversation(999) is None

    def test_send_message(self, conv_repo, temp_db):
        conversation_id = conv_repo.create_conversation(Conversation(state="new"))
        message = Message(
            conversation_id=conversation_id,
            role="user",
            content="Нужен кредит на 2 млн",
        )
        message_id = conv_repo.send_conversation_message(message)
        assert isinstance(message_id, int)

        with temp_db as conn:
            rows = conn.read_data(
                sqlQuery="SELECT * FROM messages WHERE id = :id",
                parameters={"id": message_id},
            )
        assert rows[0]["role"] == "user"
        assert rows[0]["content"] == "Нужен кредит на 2 млн"
        assert rows[0]["conversation_id"] == conversation_id