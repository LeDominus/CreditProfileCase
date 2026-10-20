import logging
import os
import time
import warnings

from openai import OpenAI
from src.config.llm_config import (
    YANDEX_API_KEY, YANDEX_FOLDER, MODEL_NAME,
    MAX_OUTPUT_TOKENS, TEMPERATURE, BASE_URL, MAX_MESSAGES,
    REASONING_EFFORT,
)
from src.config.prompt import SYSTEM_PROMPT

warnings.filterwarnings('ignore')

logger = logging.getLogger(__name__)


class LLMApi:
    def __init__(self):
        self.api_key = YANDEX_API_KEY
        self.folder_id = YANDEX_FOLDER
        self.model_uri = f"gpt://{self.folder_id}/{MODEL_NAME}"
        
        if not self.api_key:
            raise ValueError("Не удалось найти YANDEX_API_KEY")
        if not self.folder_id:
            raise ValueError("Не удалось найти YANDEX_FOLDER")

        self.client = OpenAI(
            api_key=os.getenv("YANDEX_API_KEY"),
            base_url=BASE_URL,
            default_headers={
                "X-Project-Id": os.getenv("YANDEX_FOLDER")
            }
        )

    def extract_context(
        self,
        messages: list,
        profile: dict | None = None,
        system_prompt: str | None = None,
    ) -> list[dict]:
        """Извлечение контекста диалога для запроса к LLM"""
        if system_prompt is None:
            system_prompt = SYSTEM_PROMPT
        if profile:
            known_fields = ", ".join(
                f"{key}={value}" for key, value in profile.items() if value is not None
            )
            if known_fields:
                system_prompt = (
                    f"{system_prompt}\n\nИзвестные данные профиля бизнеса: {known_fields}."
                )
        context = [{"role": "system", "content": system_prompt}]
        history = (
            messages[-MAX_MESSAGES:] if MAX_MESSAGES and MAX_MESSAGES > 0 else messages
        )
        for message in history:
            if isinstance(message, dict):
                role = message.get("role")
                content = message.get("content")
            else:
                role = getattr(message, "role", None)
                content = getattr(message, "content", None)
            if not content:
                continue
            if role not in ("user", "assistant"):
                role = "user"
            context.append({"role": role, "content": str(content)})
        return context

    def complete(
        self,
        context: list[dict],
        temperature: float | None = None,
        max_tokens: int | None = None,
        reasoning_effort: str | None = None,
    ) -> str:
        """Запрос к LLM с подготовленным контекстом"""
        logger.info(
            "--> LLM: отправка запроса (model=%s, сообщений: %d, temperature=%s%s)",
            self.model_uri,
            len(context),
            TEMPERATURE if temperature is None else temperature,
            f", reasoning_effort={reasoning_effort}" if reasoning_effort else "",
        )
        started = time.perf_counter()
        effective_temperature = TEMPERATURE if temperature is None else temperature
        effective_max_tokens = MAX_OUTPUT_TOKENS if max_tokens is None else max_tokens
        effective_reasoning = (reasoning_effort if reasoning_effort is not None else REASONING_EFFORT)
        request_kwargs = {}
        if effective_reasoning and effective_reasoning != "off":
            request_kwargs["extra_body"] = {"reasoning_effort": effective_reasoning}
        try:
            response = self.client.chat.completions.create(
                model=self.model_uri,
                messages=context,
                temperature=effective_temperature,
                max_tokens=effective_max_tokens,
                **request_kwargs,
            )
            answer = response.choices[0].message.content or ""
            finish_reason = getattr(response.choices[0], "finish_reason", None)
            if not answer.strip() and finish_reason == "length":
                retry_max_tokens = effective_max_tokens * 4
                logger.warning(
                    "LLM: пустой ответ (finish_reason=length) — "
                    "повтор с max_tokens=%d",
                    retry_max_tokens,
                )
                response = self.client.chat.completions.create(
                    model=self.model_uri,
                    messages=context,
                    temperature=effective_temperature,
                    max_tokens=retry_max_tokens,
                    **request_kwargs,
                )
                answer = response.choices[0].message.content or ""
            logger.info(
                "<-- LLM: ответ получен (%d символов, за %.2f сек)",
                len(answer),
                time.perf_counter() - started,
            )
            return answer
        except Exception as e:
            logger.error(
                "LLM: ошибка запроса за %.2f сек: %s",
                time.perf_counter() - started,
                e,
            )
            raise RuntimeError(f"Ошибка при запросе к LLM: {e}") from e
        