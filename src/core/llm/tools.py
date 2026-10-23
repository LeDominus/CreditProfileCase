import json
import logging
import re
from dataclasses import asdict
from src.config.prompt import DIALOGUE_RESPONSE_PROMPT
from src.config.tools_config import (
    MAX_TOOL_CALLS,
    PAYMENT_TOOL_NAME,
    TOOL_RESULT_TEMPLATE,
)
from src.core.calc_payment import calculate_annuity_payment
from src.schemas.llm_schema import ToolExecution

logger = logging.getLogger(__name__)


def parse_dialogue_response(reply: str) -> dict | None:
    """Разбор merged-ответа LLM: JSON с profile_updates, tool и reply.

    Возвращает dict или None, если ответ не является JSON-объектом
    (модель нарушила формат — текст целиком уходит пользователю).
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
    return data


def execute_tool(tool_call: dict) -> ToolExecution:
    """Детерминированное исполнение вызова инструмента"""
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


def run_dialogue(
    llm, context: list[dict], max_tool_calls: int | None = None
) -> dict:
    """Единый диалоговый цикл: извлечение полей + ответ + инструменты.

    Модель отвечает merged-JSON (profile_updates + tool + reply) одним
    запросом. Возвращает {"reply": str, "profile_updates": dict, "parsed": bool};
    при parsed=False модель ответила текстом вне формата.
    """
    limit = MAX_TOOL_CALLS if max_tool_calls is None else max_tool_calls
    messages = [dict(message) for message in context]
    if messages and messages[0].get("role") == "system":
        messages[0] = {
            **messages[0],
            "content": f"{messages[0]['content']}{DIALOGUE_RESPONSE_PROMPT}",
        }

    profile_updates: dict = {}
    last_result: ToolExecution | None = None
    calls_made = 0
    while True:
        reply = llm.complete(messages)
        data = parse_dialogue_response(reply)
        if data is None:
            return {"reply": reply, "profile_updates": {}, "parsed": False}
        updates = data.get("profile_updates")
        if isinstance(updates, dict):
            profile_updates.update(updates)
        tool = data.get("tool")
        if not (isinstance(tool, str) and tool.strip()):
            return {
                "reply": str(data.get("reply") or ""),
                "profile_updates": profile_updates,
                "parsed": True,
            }
        arguments = data.get("arguments")
        tool_call = {
            "tool": tool.strip(),
            "arguments": arguments if isinstance(arguments, dict) else {},
        }
        if calls_made >= limit:
            logger.warning(
                "Инструменты: достигнут лимит вызовов (%d) — "
                "финальный ответ формируется без LLM",
                limit,
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
        return {
            "reply": format_tool_result(last_result),
            "profile_updates": profile_updates,
            "parsed": True,
        }
    return {"reply": "", "profile_updates": profile_updates, "parsed": True}