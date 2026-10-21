"""Юнит-тесты ИИ-объяснения решения по заявке (п. 2.8 плана MVP)."""

import pytest

from src.config.prompt import EXPLAIN_ANALYST_PROMPT, EXPLAIN_CLIENT_PROMPT
from src.core.llm.explain_pipeline import explain_application_decision
from tests.conftest import StubLLM


APPLICATION = {
    "id": 1,
    "product_name": "Оборотный капитал",
    "requested_amount": 1_500_000,
    "term_months": 24,
    "status": "rejected",
    "decision_details": {
        "score": 35.0,
        "decision": "rejected",
        "explanation": "Балл 35 из 100 — ниже порога отказа (50).",
        "factors": [
            {
                "name": "margin",
                "label": "Рентабельность",
                "value": "5.0%",
                "normalized": 0.17,
                "weight": 20.0,
                "contribution": 3.33,
            },
            {
                "name": "payment_burden",
                "label": "Долговая нагрузка",
                "value": "37.8% выручки",
                "normalized": -0.39,
                "weight": 25.0,
                "contribution": -9.72,
            },
        ],
        "missing_fields": [],
    },
}


class FailingLLM(StubLLM):
    """Стаб LLM, имитирующий недоступность модели."""

    def complete(self, context, temperature=None, max_tokens=None, reasoning_effort=None):
        self.requests.append(context)
        raise RuntimeError("LLM unavailable")


class TestExplainDecision:
    def test_llm_answer_returned(self):
        llm = StubLLM(answer="Платёж слишком велик для вашей выручки.")
        result = explain_application_decision(llm, APPLICATION)
        assert result == {
            "audience": "client",
            "explanation": "Платёж слишком велик для вашей выручки.",
            "source": "llm",
        }

    def test_client_prompt_is_strict(self):
        llm = StubLLM(answer="ok")
        explain_application_decision(llm, APPLICATION)
        system = llm.requests[0][0]["content"]
        assert system == EXPLAIN_CLIENT_PROMPT
        assert "ТОЛЬКО" in system

    def test_analyst_prompt_for_analyst_audience(self):
        llm = StubLLM(answer="ok")
        explain_application_decision(llm, APPLICATION, audience="analyst")
        assert llm.requests[0][0]["content"] == EXPLAIN_ANALYST_PROMPT

    def test_brief_contains_only_decision_data(self):
        llm = StubLLM(answer="ok")
        explain_application_decision(llm, APPLICATION)
        user_message = llm.requests[0][1]["content"]
        assert "Оборотный капитал" in user_message
        assert "35" in user_message
        assert "Рентабельность" in user_message
        # единственный источник — decision_details: посторонних данных быть не должно
        assert "monthly_profit" not in user_message

    def test_fallback_when_llm_fails(self):
        result = explain_application_decision(FailingLLM(), APPLICATION)
        assert result["source"] == "fallback"
        assert "Балл 35" in result["explanation"]
        # самые слабые факторы попадают в fallback-объяснение
        assert "Долговая нагрузка" in result["explanation"]

    def test_fallback_when_llm_answer_empty(self):
        result = explain_application_decision(StubLLM(answer="   "), APPLICATION)
        assert result["source"] == "fallback"
        assert result["explanation"]

    def test_fallback_analyst_mentions_stop_factors(self):
        result = explain_application_decision(
            FailingLLM(), APPLICATION, audience="analyst"
        )
        assert result["source"] == "fallback"
        assert "Стоп-факторы" in result["explanation"]

    def test_fallback_with_missing_fields(self):
        details = dict(APPLICATION["decision_details"])
        details["missing_fields"] = ["monthly_revenue"]
        application = {**APPLICATION, "decision_details": details}
        result = explain_application_decision(FailingLLM(), application)
        assert "monthly_revenue" in result["explanation"]

    def test_unknown_audience_rejected(self):
        with pytest.raises(ValueError):
            explain_application_decision(StubLLM(), APPLICATION, audience="manager")