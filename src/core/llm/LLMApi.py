import logging
import time
import warnings
from openai import OpenAI
from src.config.llm_config import (
    YANDEX_API_KEY, YANDEX_FOLDER, MODEL_NAME,
    MAX_OUTPUT_TOKENS, TEMPERATURE, BASE_URL, MAX_MESSAGES,
    REASONING_EFFORT, REQUIRED_PROFILE_FIELDS, FALLBACK_MODEL_NAME,
    EXTRACTION_MODEL_NAME, LLM_TIMEOUT, MODEL_DIALOGUE, MODEL_EXTRACTION,
    SDK_UNAVAILABLE_ERRORS
)
from src.config.prompt import SYSTEM_PROMPT

warnings.filterwarnings('ignore')

logger = logging.getLogger(__name__)


class LLMApi:
    def __init__(self):
        self.api_key = YANDEX_API_KEY
        self.folder_id = YANDEX_FOLDER
        self.model_uri = f"gpt://{self.folder_id}/{MODEL_NAME}"
        self.fallback_model_uri = (
            f"gpt://{self.folder_id}/{FALLBACK_MODEL_NAME}"
            if FALLBACK_MODEL_NAME
            else None
        )
        self.extraction_model_uri = (
            f"gpt://{self.folder_id}/{EXTRACTION_MODEL_NAME}"
            if EXTRACTION_MODEL_NAME
            else None
        )

        if not self.api_key:
            raise ValueError("Не удалось найти YANDEX_API_KEY")
        if not self.folder_id:
            raise ValueError("Не удалось найти YANDEX_FOLDER")

        self.client = OpenAI(
            api_key=self.api_key,
            base_url=BASE_URL,
            timeout=LLM_TIMEOUT,
            max_retries=0,
            default_headers={
                "X-Project-Id": self.folder_id
            }
        )

    def extract_context(
        self,
        messages: list,
        profile: dict | None = None,
        system_prompt: str | None = None,
        require_complete_profile: bool = False,
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
            if require_complete_profile:
                missing_fields = [
                    f"{key} ({label})"
                    for key, label in REQUIRED_PROFILE_FIELDS.items()
                    if profile.get(key) is None
                ]
                if missing_fields:
                    system_prompt += (
                        f"\n\nДля отправки заявки пока не хватает данных: "
                        f"{', '.join(missing_fields)}. Уточни их у пользователя. "
                        f"Пока хотя бы один обязательный параметр не заполнен — "
                        f"не завершай диалог."
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
        model: str = MODEL_DIALOGUE,
    ) -> str:
        """Запрос к LLM с подготовленным контекстом

        model задаёт цепочку моделей: MODEL_DIALOGUE — основная + fallback,
        MODEL_EXTRACTION — модель для извлечения + fallback + основная.
        """
        logger.info("--> LLM: отправка запроса... ")

        started = time.perf_counter()
        effective_temperature = TEMPERATURE if temperature is None else temperature
        effective_max_tokens = MAX_OUTPUT_TOKENS if max_tokens is None else max_tokens
        effective_reasoning = (reasoning_effort if reasoning_effort is not None else REASONING_EFFORT)
        request_kwargs = {}
        if effective_reasoning and effective_reasoning != "off":
            request_kwargs["extra_body"] = {"reasoning_effort": effective_reasoning}
        chain = self._model_chain(model)
        for index, model_uri in enumerate(chain):
            try:
                answer = self._request(
                    model_uri,
                    context,
                    effective_temperature,
                    effective_max_tokens,
                    request_kwargs,
                )
            except Exception as e:
                if not isinstance(e, SDK_UNAVAILABLE_ERRORS) or index + 1 >= len(chain):
                    logger.error(
                        "LLM: ошибка запроса за %.2f сек: %s",
                        time.perf_counter() - started,
                        e,
                    )
                    raise RuntimeError(f"Ошибка при запросе к LLM: {e}") from e
                logger.warning(
                    "LLM: модель недоступна (%s, %.2f сек) — "
                    "переключение на следующую модель цепочки",
                    e.__class__.__name__,
                    time.perf_counter() - started,
                )
                continue
            logger.info(
                "<-- LLM: ответ получен (%d символов, за %.2f сек)",
                len(answer),
                time.perf_counter() - started,
            )
            return answer
        raise RuntimeError("Ошибка при запросе к LLM: цепочка моделей пуста")

    def _model_chain(self, model: str) -> list[str]:
        """Цепочка моделей для задачи: от основной к запасным"""
        if model == MODEL_EXTRACTION and self.extraction_model_uri:
            chain = [
                self.extraction_model_uri,
                self.fallback_model_uri,
                self.model_uri,
            ]
        else:
            chain = [self.model_uri, self.fallback_model_uri]
        return list(dict.fromkeys(uri for uri in chain if uri))

    def _request(
        self,
        model_uri: str,
        context: list[dict],
        temperature: float,
        max_tokens: int,
        request_kwargs: dict,
    ) -> str:
        """Одиночный запрос к модели с повтором при обрезанном ответе"""
        response = self.client.chat.completions.create(
            model=model_uri,
            messages=context,
            temperature=temperature,
            max_tokens=max_tokens,
            **request_kwargs,
        )
        answer = response.choices[0].message.content or ""
        finish_reason = getattr(response.choices[0], "finish_reason", None)
        if not answer.strip() and finish_reason == "length":
            retry_max_tokens = max_tokens * 2
            logger.warning(
                "LLM: пустой ответ (finish_reason=length) — "
                "повтор с max_tokens=%d",
                retry_max_tokens,
            )
            response = self.client.chat.completions.create(
                model=model_uri,
                messages=context,
                temperature=temperature,
                max_tokens=retry_max_tokens,
                **request_kwargs,
            )
            answer = response.choices[0].message.content or ""
        return answer
        
