"""Тесты инструментов LLM: LLM оркестрирует, расчёты выполняет код.

Проверяются: разбор вызова инструмента из ответа LLM, детерминированное
исполнение расчёта (calculate_annuity_payment), цикл run_with_tools
(вызов инструмента -> результат в контекст -> финальный ответ) и
интеграция в конвейер POST /api/conversations/{id}/messages.
"""

import json

import pytest
from fastapi.testclient import TestClient

from src.config.tools_config import MAX_TOOL_CALLS, PAYMENT_TOOL_NAME
from src.core.llm.tools import (
    execute_tool,
    format_tool_result,
    parse_tool_call,
    run_with_tools,
)
from src.schemas.llm_schema import ToolExecution
from tests.conftest import ChatStubLLM


class SequenceStubLLM:
    """Стаб LLM: возвращает заданные ответы по очереди, запоминает запросы."""

    def __init__(self, answers: list[str]):
        self.answers = list(answers)
        self.requests: list[list[dict]] = []

    def complete(self, context, temperature=None, max_tokens=None, reasoning_effort=None):
        self.requests.append(context)
        return self.answers.pop(0)


class ToolSequenceStubLLM(ChatStubLLM):
    """Стаб для конвейера сообщений: последовательность ответов в диалоге.

    На промпт извлечения профиля отвечает как обычно (JSON полей),
    в диалоге — по очереди из chat_answers (например, вызов инструмента,
    затем финальный ответ).
    """

    def __init__(self, chat_answers: list[str]):
        super().__init__(chat_answer=chat_answers[0])
        self.chat_answers = list(chat_answers)

    def complete(self, context, temperature=None, max_tokens=None, reasoning_effort=None):
        self.requests.append(context)
        system = context[0]["content"] if context else ""
        if "извлекатель" in system:
            return self.extraction_answer
        return self.chat_answers.pop(0)


def _tool_reply(amount=2_000_000, annual_rate=18.0, months=24) -> str:
    return json.dumps(
        {
            "tool": PAYMENT_TOOL_NAME,
            "arguments": {
                "amount": amount,
                "annual_rate": annual_rate,
                "months": months,
            },
        }
    )


def _context() -> list[dict]:
    return [
        {"role": "system", "content": "Ты — ассистент банка."},
        {"role": "user", "content": "Сколько будет платёж по 2 млн на 24 мес под 18%?"},
    ]


class TestParseToolCall:
    def test_valid_call(self):
        call = parse_tool_call(_tool_reply())
        assert call == {
            "tool": PAYMENT_TOOL_NAME,
            "arguments": {"amount": 2_000_000, "annual_rate": 18.0, "months": 24},
        }

    def test_fenced_json(self):
        assert parse_tool_call(f"```json\n{_tool_reply()}\n```") is not None

    def test_missing_arguments_defaults_to_empty(self):
        call = parse_tool_call('{"tool": "calculate_payment"}')
        assert call == {"tool": PAYMENT_TOOL_NAME, "arguments": {}}

    def test_prose_is_not_a_call(self):
        assert parse_tool_call("Платёж составит около 90 000 руб. в месяц.") is None

    def test_json_without_tool_key_is_not_a_call(self):
        # ответ извлекателя профиля не должен считаться вызовом инструмента
        assert parse_tool_call('{"funding_purpose": "развитие бизнеса"}') is None

    def test_broken_json_is_not_a_call(self):
        assert parse_tool_call('{"tool": "calculate_payment", ') is None

    def test_empty_reply(self):
        assert parse_tool_call("") is None
        assert parse_tool_call(None) is None


class TestExecuteTool:
    def test_known_example(self):
        result = execute_tool(
            {"tool": PAYMENT_TOOL_NAME,
             "arguments": {"amount": 1_000_000, "annual_rate": 18.0, "months": 12}}
        )
        assert isinstance(result, ToolExecution)
        assert result.status == "success"
        assert result.monthly_payment == pytest.approx(91_680.0, rel=1e-3)
        assert result.total_repayment == pytest.approx(
            result.monthly_payment * 12, rel=1e-6
        )
        assert result.overpayment == pytest.approx(
            result.total_repayment - 1_000_000, rel=1e-6
        )

    def test_string_numbers_accepted(self):
        result = execute_tool(
            {"tool": PAYMENT_TOOL_NAME,
             "arguments": {"amount": "2000000", "annual_rate": "18", "months": "24"}}
        )
        assert result.status == "success"
        assert result.amount == 2_000_000.0

    def test_unknown_tool(self):
        result = execute_tool({"tool": "some_other_tool", "arguments": {}})
        assert result.status == "error"
        assert PAYMENT_TOOL_NAME in result.error

    def test_missing_arguments(self):
        result = execute_tool({"tool": PAYMENT_TOOL_NAME, "arguments": {"months": 12}})
        assert result.status == "error"
        assert "amount" in result.error

    def test_non_positive_arguments(self):
        result = execute_tool(
            {"tool": PAYMENT_TOOL_NAME,
             "arguments": {"amount": -5, "annual_rate": 18.0, "months": 12}}
        )
        assert result.status == "error"


class TestFormatToolResult:
    def test_success(self):
        result = execute_tool(
            {"tool": PAYMENT_TOOL_NAME,
             "arguments": {"amount": 1_000_000, "annual_rate": 18.0, "months": 12}}
        )
        text = format_tool_result(result)
        assert "Ежемесячный платёж" in text
        assert "руб." in text

    def test_error(self):
        assert "Не удалось выполнить расчёт" in format_tool_result(
            ToolExecution(status="error", error="x")
        )


class TestRunWithTools:
    def test_plain_reply_returned_as_is(self):
        llm = SequenceStubLLM(["Обычный ответ без расчёта."])
        assert run_with_tools(llm, _context()) == "Обычный ответ без расчёта."
        assert len(llm.requests) == 1

    def test_tool_call_then_final_reply(self):
        llm = SequenceStubLLM([_tool_reply(), "Платёж 99 842 руб. в месяц."])
        result = run_with_tools(llm, _context())
        assert result == "Платёж 99 842 руб. в месяц."
        assert len(llm.requests) == 2

        second = llm.requests[1]
        # system-промпт дополнен правилами инструментов
        assert second[0]["role"] == "system"
        assert PAYMENT_TOOL_NAME in second[0]["content"]
        # в контекст добавлены вызов инструмента и результат расчёта
        assert second[-2]["role"] == "assistant"
        assert second[-2]["content"] == _tool_reply()
        assert second[-1]["role"] == "user"
        assert "monthly_payment" in second[-1]["content"]
        assert "не пересчитывай" in second[-1]["content"]

    def test_error_result_fed_back_to_llm(self):
        llm = SequenceStubLLM(
            [_tool_reply(amount=None), "Уточните сумму и ставку, пожалуйста."]
        )
        result = run_with_tools(llm, _context())
        assert result == "Уточните сумму и ставку, пожалуйста."
        assert '"status": "error"' in llm.requests[1][-1]["content"]

    def test_limit_reached_fallback_without_llm(self):
        llm = SequenceStubLLM([_tool_reply()] * 10)
        result = run_with_tools(llm, _context(), max_tool_calls=2)
        # лимит вызовов: 2 расчёта + 1 финальный запрос, дальше — fallback кода
        assert len(llm.requests) == 3
        assert "Ежемесячный платёж" in result
        assert "руб." in result

    def test_default_limit(self):
        assert MAX_TOOL_CALLS == 3

    def test_original_context_not_mutated(self):
        llm = SequenceStubLLM([_tool_reply(), "Готово."])
        context = _context()
        run_with_tools(llm, context)
        assert context[0]["content"] == "Ты — ассистент банка."
        assert len(context) == 2


class TestMessageEndpointWithTools:
    """Интеграция: конвейер сообщений использует инструмент расчёта."""

    @pytest.fixture()
    def client(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DATABASE_URI", f"sqlite:///{tmp_path / 'tools_test.db'}")
        from main import app

        with TestClient(app) as test_client:
            yield test_client

    def test_reply_comes_from_tool_flow(self, client):
        final = (
            "При сумме 2 000 000 руб., ставке 18% и сроке 24 месяца "
            "ежемесячный платёж составит 99 842 руб."
        )
        client.app.state.llmAPI = ToolSequenceStubLLM([_tool_reply(), final])
        conversation_id = client.post("/api/conversations", json={}).json()["id"]
        response = client.post(
            f"/api/conversations/{conversation_id}/messages",
            json={
                "role": "user",
                "content": "Посчитай платёж: 2 млн, 18% годовых, 24 месяца",
            },
        )
        assert response.status_code == 201
        body = response.json()
        # пользователю возвращён финальный ответ, а не JSON-вызов инструмента
        assert body["reply"] == final
        assert "tool" not in body["reply"]

    def test_plain_reply_flow_unchanged(self, client):
        client.app.state.llmAPI = ToolSequenceStubLLM(["Расскажите о вашем бизнесе."])
        conversation_id = client.post("/api/conversations", json={}).json()["id"]
        response = client.post(
            f"/api/conversations/{conversation_id}/messages",
            json={"role": "user", "content": "Привет"},
        )
        assert response.status_code == 201
        assert response.json()["reply"] == "Расскажите о вашем бизнесе."