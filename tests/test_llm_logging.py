"""Тесты логирования запросов к LLM: отправка → ответ/ошибка."""

import logging
from types import SimpleNamespace

import pytest
from openai import APIConnectionError, APITimeoutError

from src.config.llm_config import MODEL_EXTRACTION
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
            if isinstance(response, Exception):
                raise response
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
            [{"role": "user", "content": "Привет"}], reasoning_effort="medium"
        )
        call = llm.client.chat.completions.calls[0]
        assert call["extra_body"] == {"reasoning_effort": "medium"}

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


def _response(text):
    return SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(content=text), finish_reason="stop"
            )
        ]
    )


class TestLLMFallback:
    def test_timeout_switches_to_fallback_model(self):
        llm = _make_llm(responses=[APITimeoutError(None), _response("Ответ fallback")])
        llm.fallback_model_uri = "gpt://test-folder/fallback-model"
        answer = llm.complete([{"role": "user", "content": "Привет"}])
        assert answer == "Ответ fallback"
        calls = llm.client.chat.completions.calls
        assert len(calls) == 2
        assert calls[0]["model"] == llm.model_uri
        assert calls[1]["model"] == "gpt://test-folder/fallback-model"

    def test_connection_error_switches_to_fallback_model(self):
        llm = _make_llm(
            responses=[APIConnectionError(message="net", request=None), _response("Ответ")]
        )
        llm.fallback_model_uri = "gpt://test-folder/fallback-model"
        assert llm.complete([{"role": "user", "content": "Привет"}]) == "Ответ"

    def test_no_fallback_configured_raises(self):
        llm = _make_llm(responses=[APITimeoutError(None)])
        llm.fallback_model_uri = None
        with pytest.raises(RuntimeError):
            llm.complete([{"role": "user", "content": "Привет"}])

    def test_fallback_failure_raises(self):
        llm = _make_llm(
            responses=[APITimeoutError(None), APIConnectionError(message="net", request=None)]
        )
        llm.fallback_model_uri = "gpt://test-folder/fallback-model"
        with pytest.raises(RuntimeError):
            llm.complete([{"role": "user", "content": "Привет"}])

    def test_non_api_error_does_not_switch_model(self):
        llm = _make_llm(error=ValueError("bug"))
        llm.fallback_model_uri = "gpt://test-folder/fallback-model"
        with pytest.raises(RuntimeError):
            llm.complete([{"role": "user", "content": "Привет"}])
        assert len(llm.client.chat.completions.calls) == 1

    def test_extraction_model_used_first(self):
        llm = _make_llm(answer="Ответ")
        llm.extraction_model_uri = "gpt://test-folder/extraction-model"
        llm.complete(
            [{"role": "user", "content": "Привет"}], model=MODEL_EXTRACTION
        )
        calls = llm.client.chat.completions.calls
        assert len(calls) == 1
        assert calls[0]["model"] == "gpt://test-folder/extraction-model"

    def test_extraction_model_falls_back_to_main(self):
        llm = _make_llm(responses=[APITimeoutError(None), _response("Ответ")])
        llm.extraction_model_uri = "gpt://test-folder/extraction-model"
        llm.fallback_model_uri = None
        answer = llm.complete(
            [{"role": "user", "content": "Привет"}], model=MODEL_EXTRACTION
        )
        assert answer == "Ответ"
        calls = llm.client.chat.completions.calls
        assert calls[0]["model"] == "gpt://test-folder/extraction-model"
        assert calls[1]["model"] == llm.model_uri

    def test_extraction_without_extraction_model_uses_main(self):
        llm = _make_llm(answer="Ответ")
        llm.extraction_model_uri = None
        llm.complete(
            [{"role": "user", "content": "Привет"}], model=MODEL_EXTRACTION
        )
        assert llm.client.chat.completions.calls[0]["model"] == llm.model_uri
