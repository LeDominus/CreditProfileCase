"""Инструменты LLM: оркестрация без самостоятельных вычислений.

LLM не выполняет расчёты сама — при необходимости она возвращает
структурированный вызов инструмента (JSON), код исполняет его
детерминированно и возвращает результат LLM для финального ответа.
"""

import json
import logging
import re
from dataclasses import asdict

from src.config.prompt import TOOL_USE_PROMPT
from src.config.tools_config import (
    MAX_TOOL_CALLS,
    PAYMENT_TOOL_NAME,
    TOOL_RESULT_TEMPLATE,
)
from src.core.credit_calc.calc_payment import calculate_annuity_payment
from src.schemas.llm_schema import ToolExecution

logger = logging.getLogger(__name__)


def parse_tool_call(reply: str) -> dict | None:
    """Разбор ответа LLM: возвращает вызов инструмента или None.

    Вызовом считается ответ, состоящий только из JSON-объекта вида
    {"tool": "...", "arguments": {...}} (допускается обрамление ```json ... ```).
    Обычные текстовые ответы и JSON без ключа "tool" вызовом не считаются.
    """
    if not reply:
        return None
    text = reply.strip()
    fence = re.match(r"^```(?:json)?\s*(.*?)\s*```$", text, re.DOTALL)
    if fence:
        text = fence.group(1).strip()
    if not (text.startswith("{") and text.endswith("}")):
        return None
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict):
        return None
    tool = data.get("tool")
    if not isinstance(tool, str) or not tool.strip():
        return None
    arguments = data.get("arguments")
    if arguments is None:
        arguments = {}
    if not isinstance(arguments, dict):
        return None
    return {"tool": tool.strip(), "arguments": arguments}


def execute_tool(tool_call: dict) -> ToolExecution:
    """Детерминированное исполнение вызова инструмента.

    Расчёт выполняет код (не LLM): LLM получает только результат.
    Любая ошибка возвращается как ToolExecution(status="error", error=...).
    """
    tool = tool_call.get("tool")
    if tool != PAYMENT_TOOL_NAME:
        return ToolExecution(
            status="error",
            tool=tool,
            error=(
                f"Неизвестный инструмент: {tool!r}. "
                f"Доступен только {PAYMENT_TOOL_NAME!r}."
            ),
        )
    arguments = tool_call.get("arguments") or {}
    try:
        amount = float(arguments["amount"])
        annual_rate = float(arguments["annual_rate"])
        months = int(arguments["months"])
    except (KeyError, TypeError, ValueError):
        return ToolExecution(
            status="error",
            tool=PAYMENT_TOOL_NAME,
            error=(
                "Некорректные аргументы: нужны числа amount (сумма, руб.), "
                "annual_rate (годовая ставка, %), months (срок, мес.)."
            ),
        )
    try:
        monthly_payment = calculate_annuity_payment(float(amount), annual_rate, months)
    except (ValueError, ArithmeticError) as exc:
        return ToolExecution(status="error", tool=PAYMENT_TOOL_NAME, error=str(exc))
    monthly_payment = round(monthly_payment, 2)
    total_repayment = round(monthly_payment * months, 2)
    overpayment = round(total_repayment - amount, 2)
    return ToolExecution(
        status="success",
        tool=PAYMENT_TOOL_NAME,
        amount=amount,
        annual_rate=annual_rate,
        months=months,
        monthly_payment=monthly_payment,
        total_repayment=total_repayment,
        overpayment=overpayment,
    )


def format_tool_result(result: ToolExecution) -> str:
    """Человекочитаемый вывод результата инструмента (fallback без LLM)."""
    if result.status != "success":
        return "Не удалось выполнить расчёт: " + str(
            result.error or "неизвестная ошибка"
        )
    return (
        f"Ежемесячный платёж: {result.monthly_payment:.2f} руб., "
        f"всего к возврату: {result.total_repayment:.2f} руб., "
        f"переплата: {result.overpayment:.2f} руб. "
        f"(сумма {result.amount:.0f} руб., ставка {result.annual_rate:.1f}% годовых, "
        f"срок {result.months} мес.). Расчёт аннуитетный, ориентировочный."
    )


def run_with_tools(llm, context: list[dict], max_tool_calls: int = MAX_TOOL_CALLS) -> str:
    """Диалоговый цикл с инструментами: LLM оркестрирует, код считает.

    1. К system-промпту добавляются правила использования инструментов.
    2. Если ответ LLM — вызов инструмента, он исполняется кодом,
       результат добавляется в контекст, и LLM формулирует финальный ответ.
    3. Обычный текстовый ответ возвращается как есть (один запрос к LLM).
    Лимит вызовов защищает от зацикливания: при его достижении результат
    последнего расчёта форматируется кодом без участия LLM.
    Исходный контекст не мутируется.
    """
    messages = [dict(message) for message in context]
    if messages and messages[0].get("role") == "system":
        messages[0] = {
            **messages[0],
            "content": f"{messages[0]['content']}{TOOL_USE_PROMPT}",
        }

    last_result: ToolExecution | None = None
    calls_made = 0
    while True:
        reply = llm.complete(messages)
        tool_call = parse_tool_call(reply)
        if tool_call is None:
            return reply
        if calls_made >= max_tool_calls:
            logger.warning(
                "Инструменты: достигнут лимит вызовов (%d) — "
                "финальный ответ формируется без LLM",
                max_tool_calls,
            )
            break
        calls_made += 1
        result = execute_tool(tool_call)
        last_result = result
        logger.info(
            "Инструмент %s: статус=%s, аргументы=%s",
            tool_call.get("tool"),
            result.status,
            tool_call.get("arguments"),
        )
        messages.append({"role": "assistant", "content": reply})
        messages.append(
            {
                "role": "user",
                "content": TOOL_RESULT_TEMPLATE.format(
                    tool=tool_call.get("tool"),
                    result_json=json.dumps(asdict(result), ensure_ascii=False),
                ),
            }
        )
    if last_result is not None:
        return format_tool_result(last_result)
    return reply