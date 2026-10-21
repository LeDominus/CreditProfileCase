"""Тесты логирования запросов к LLM: отправка → ответ/ошибка."""

import logging
from types import SimpleNamespace

from src.core.llm.LLMApi import LLMApi


class _FakeCompletions:
    def __init__(self, answer="Текст ответа", error=None, responses=None):
        self.answer = answer
        self.error = error
        # последовательность ответов для проверки повторных запросов
        self.responses = responses
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        if self.error:
            raise self.error
        if self.responses is not None:
            response = self.responses.pop(0)
        else:
            response = SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(content=self.answer))]
            )
        return response


def _make_llm(answer="Текст ответа", error=None, responses=None):
    llm = LLMApi()
    llm.client = SimpleNamespace(
        chat=SimpleNamespace(completions=_FakeCompletions(answer, error, responses))
    )
    return llm


class TestLLMRequestLogging:
    def test_complete_logs_send_and_receive(self, caplog):
        llm = _make_llm(answer="Ответ ассистента")
        with caplog.at_level(logging.INFO, logger="src.core.llm.LLMApi"):
            answer = llm.complete([{"role": "user", "content": "Привет"}])
        assert answer == "Ответ ассистента"
        assert "отправка запроса" in caplog.text
        assert "ответ получен" in caplog.text

    def test_complete_logs_error_and_raises(self, caplog):
        llm = _make_llm(error=RuntimeError("network down"))
        with caplog.at_level(logging.INFO, logger="src.core.llm.LLMApi"):
            try:
                llm.complete([{"role": "user", "content": "Привет"}])
                raised = False
            except RuntimeError:
                raised = True
        assert raised
        assert "отправка запроса" in caplog.text
        assert "ошибка запроса" in caplog.text

    def test_complete_retries_on_empty_answer_with_length(self, caplog):
        """Пустой ответ с finish_reason='length' → повтор с увеличенным лимитом."""
        empty = SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(content=""),
                    finish_reason="length",
                )
            ]
        )
        full = SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(content="Полный ответ"),
                    finish_reason="stop",
                )
            ]
        )
        llm = _make_llm(responses=[empty, full])
        with caplog.at_level(logging.INFO, logger="src.core.llm.LLMApi"):
            answer = llm.complete([{"role": "user", "content": "Привет"}])
        assert answer == "Полный ответ"
        assert "повтор с max_tokens" in caplog.text
        completions = llm.client.chat.completions
        assert len(completions.calls) == 2
        assert completions.calls[1]["max_tokens"] > completions.calls[0]["max_tokens"]

    def test_complete_no_retry_on_empty_answer_without_length(self):
        """Пустой ответ с другим finish_reason — без повтора (graceful)."""
        empty = SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(content=""),
                    finish_reason="stop",
                )
            ]
        )
        llm = _make_llm(responses=[empty])
        answer = llm.complete([{"role": "user", "content": "Привет"}])
        assert answer == ""
        assert len(llm.client.chat.completions.calls) == 1

    def test_complete_passes_reasoning_effort_via_extra_body(self):
        """reasoning_effort уходит в запрос через extra_body."""
        llm = _make_llm(answer="Ответ")
        llm.complete(
            [{"role": "user", "content": "Привет"}], reasoning_effort="none"
        )
        call = llm.client.chat.completions.calls[0]
        assert call["extra_body"] == {"reasoning_effort": "none"}

    def test_complete_without_reasoning_effort_uses_config_default(self):
        """Без явного reasoning_effort используется значение из конфига."""
        llm = _make_llm(answer="Ответ")
        llm.complete([{"role": "user", "content": "Привет"}])
        call = llm.client.chat.completions.calls[0]
        assert call["extra_body"] == {"reasoning_effort": "low"}

    def test_complete_reasoning_effort_off_sends_no_extra_body(self):
        """reasoning_effort='off' — параметр не отправляется провайдеру."""
        llm = _make_llm(answer="Ответ")
        llm.complete([{"role": "user", "content": "Привет"}], reasoning_effort="off")
        call = llm.client.chat.completions.calls[0]
        assert "extra_body" not in call

    def test_complete_log_hides_model_uri(self, caplog):
        """В логах нет ссылки модели gpt://<folder>/<model> — folder_id не утекает."""
        llm = _make_llm(answer="Ответ")
        with caplog.at_level(logging.INFO, logger="src.core.llm.LLMApi"):
            llm.complete([{"role": "user", "content": "Привет"}])
        assert "отправка запроса" in caplog.text
        assert "gpt://" not in caplog.text
        assert "test-folder" not in caplog.text