"""Unit-тесты: извлечение контекста и структурированных полей профиля."""

from src.config.llm_config import EXTRACTION_TEMPERATURE, MODEL_EXTRACTION
from src.core.llm.utils import (
    extract_profile_fields,
    parse_profile_fields,
    validate_profile_fields,
)
from src.schemas.conversation_schema import Message


class TestExtractContext:
    def test_basic_dict_messages(self, stub_llm):
        ctx = stub_llm.extract_context(
            messages=[
                {"role": "user", "content": "Привет"},
                {"role": "assistant", "content": "Здравствуйте!"},
            ]
        )
        assert ctx[0]["role"] == "system"
        assert len(ctx) == 3
        assert ctx[1] == {"role": "user", "content": "Привет"}
        assert ctx[2] == {"role": "assistant", "content": "Здравствуйте!"}

    def test_profile_fields_injected_into_system_prompt(self, stub_llm):
        ctx = stub_llm.extract_context(
            messages=[{"role": "user", "content": "hi"}],
            profile={"industry": "общепит", "requested_amount": None},
        )
        assert "industry=общепит" in ctx[0]["content"]
        assert "requested_amount" not in ctx[0]["content"]  # None-поля не попадают

    def test_custom_system_prompt(self, stub_llm):
        ctx = stub_llm.extract_context(
            messages=[{"role": "user", "content": "hi"}],
            system_prompt="Свой промпт",
        )
        assert ctx[0]["content"] == "Свой промпт"

    def test_message_dataclass_supported(self, stub_llm):
        from src.config.llm_config import MAX_MESSAGES

        msgs = [
            Message(conversation_id=1, role=r, content=f"msg-{i}")
            for i, r in enumerate(["user", "assistant"] * (MAX_MESSAGES // 2 + 3))
        ]
        ctx = stub_llm.extract_context(messages=msgs)
        # в контекст попадают только последние MAX_MESSAGES сообщений
        assert len(ctx) == 1 + MAX_MESSAGES
        assert ctx[-1]["content"] == f"msg-{len(msgs) - 1}"
        assert ctx[-1]["role"] == "assistant"

    def test_foreign_roles_remapped_and_empty_skipped(self, stub_llm):
        ctx = stub_llm.extract_context(
            messages=[
                {"role": "tool", "content": "служебное"},
                {"role": "user", "content": ""},
                {"role": "user", "content": "вопрос"},
            ]
        )
        assert len(ctx) == 3
        assert ctx[1]["role"] == "user"  # tool -> user
        assert ctx[2]["content"] == "вопрос"
    def test_required_fields_hint_when_profile_incomplete(self, stub_llm):
        ctx = stub_llm.extract_context(
            messages=[{"role": "user", "content": "hi"}],
            profile={
                "industry": "IT",
                "business_age_months": 36,
                "monthly_revenue": None,
                "monthly_profit": None,
            },
            require_complete_profile=True,
        )
        prompt = ctx[0]["content"]
        assert "пока не хватает данных" in prompt
        assert "monthly_revenue (выручка в месяц" in prompt
        assert "monthly_profit (прибыль в месяц" in prompt
        assert "business_age_months (" not in prompt  # заполненное поле не в списке
        assert "не завершай диалог" in prompt

    def test_no_hint_when_required_fields_complete(self, stub_llm):
        ctx = stub_llm.extract_context(
            messages=[{"role": "user", "content": "hi"}],
            profile={
                "business_age_months": 36,
                "monthly_revenue": 800000.0,
                "monthly_profit": 150000.0,
            },
            require_complete_profile=True,
        )
        assert "пока не хватает данных" not in ctx[0]["content"]

    def test_no_hint_without_flag(self, stub_llm):
        ctx = stub_llm.extract_context(
            messages=[{"role": "user", "content": "hi"}],
            profile={"industry": "IT"},
        )
        assert "пока не хватает данных" not in ctx[0]["content"]


class TestParseProfileFields:
    def test_clean_json(self):
        assert parse_profile_fields(
            '{"requested_amount": 1500000, "preferred_term_months": 24}'
        ) == {"requested_amount": 1500000.0, "preferred_term_months": 24}

    def test_markdown_fenced_json(self):
        assert parse_profile_fields(
            '```json\n{"funding_purpose": "Оборот"}\n```'
        ) == {"funding_purpose": "Оборот"}

    def test_json_with_text_around(self):
        assert parse_profile_fields(
            'Ответ: {"industry": "общепит"} — готово'
        ) == {"industry": "общепит"}

    def test_float_coerced_to_int(self):
        assert parse_profile_fields('{"business_age_months": 36.0}') == {
            "business_age_months": 36
        }

    def test_duration_string_years_converted_to_months(self):
        # LLM вернула срок строкой в годах — парсер переводит в месяцы
        assert parse_profile_fields('{"business_age_months": "2 года"}') == {
            "business_age_months": 24
        }

    def test_duration_fractional_years(self):
        assert parse_profile_fields('{"business_age_months": "полтора года"}') == {
            "business_age_months": 18
        }
        assert parse_profile_fields('{"business_age_months": "1,5 года"}') == {
            "business_age_months": 18
        }

    def test_duration_years_and_months_combined(self):
        assert parse_profile_fields('{"business_age_months": "1 год 6 месяцев"}') == {
            "business_age_months": 18
        }

    def test_duration_months_string(self):
        assert parse_profile_fields('{"preferred_term_months": "18 мес"}') == {
            "preferred_term_months": 18
        }

    def test_unparseable_duration_dropped(self):
        assert parse_profile_fields('{"business_age_months": "молодой бизнес"}') == {}

    def test_unknown_and_invalid_fields_dropped(self):
        assert parse_profile_fields(
            '{"unknown_field": 1, "requested_amount": "abc", "industry": null}'
        ) == {}

    def test_no_json(self):
        assert parse_profile_fields("мусор без json") == {}

    def test_empty_answer(self):
        assert parse_profile_fields("") == {}


class TestValidateProfileFields:
    def test_dict_input(self):
        assert validate_profile_fields(
            {"requested_amount": 1500000, "unknown_field": 1}
        ) == {"requested_amount": 1500000.0}

    def test_duration_string_converted(self):
        assert validate_profile_fields({"business_age_months": "2 года"}) == {
            "business_age_months": 24
        }

    def test_non_dict_input(self):
        assert validate_profile_fields(None) == {}
        assert validate_profile_fields([1, 2]) == {}


class TestExtractProfileFields:
    def test_end_to_end_with_stub(self, stub_llm):
        stub_llm.answer = '{"requested_amount": 2000000, "preferred_term_months": 24}'
        fields = extract_profile_fields(
            "нужно 2 млн на 24 месяца", stub_llm, current_profile={"industry": "IT"}
        )
        assert fields == {"requested_amount": 2000000.0, "preferred_term_months": 24}
        # контекст построен корректно
        ctx = stub_llm.requests[0]
        assert ctx[0]["role"] == "system"
        assert "извлеки" in ctx[0]["content"].lower()
        assert "industry=IT" in ctx[0]["content"]
        assert ctx[-1] == {"role": "user", "content": "нужно 2 млн на 24 месяца"}

    def test_extraction_uses_low_reasoning(self, stub_llm):
        """Извлечение полей: reasoning_effort='low' (минимум для Yandex API), температура фиксированная."""
        stub_llm.answer = '{"industry": "общепит"}'
        extract_profile_fields("работаю в общепите", stub_llm)
        assert stub_llm.kwargs[0]["reasoning_effort"] == "low"
        assert stub_llm.kwargs[0]["temperature"] == EXTRACTION_TEMPERATURE

    def test_extraction_uses_extraction_model(self, stub_llm):
        """Извлечение полей идёт на модель для экстракции, не на диалоговую."""
        stub_llm.answer = '{"industry": "общепит"}'
        extract_profile_fields("работаю в общепите", stub_llm)
        assert stub_llm.kwargs[0]["model"] == MODEL_EXTRACTION

    def test_empty_message(self, stub_llm):
        assert extract_profile_fields("   ", stub_llm) == {}
        assert stub_llm.requests == []

    def test_llm_failure_returns_empty_dict(self):
        class FailLLM:
            def extract_context(self, *args, **kwargs):
                return [{"role": "system", "content": "s"}]

            def complete(self, *args, **kwargs):
                raise RuntimeError("network down")

        assert extract_profile_fields("нужно 2 млн", FailLLM()) == {}
