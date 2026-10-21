import logging
import os
import re
import sys
import time
import uuid
from pathlib import Path
from dotenv import load_dotenv
import requests
import streamlit as st
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP

load_dotenv()

# скоринговая модель и аннуитетный расчёт — общие модули с backend
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.core.scoring import score_application
from src.core.alternatives import suggest_alternative_products
from src.core.calc_payment import calculate_annuity_payment

PRODUCTS = [
    {
        "id": 1,
        "name": "Оборотный капитал",
        "tagline": "Для закупок, зарплат и покрытия кассовых разрывов",
        "purpose": "Пополнение оборотных средств",
        "min_amount": 300_000,
        "max_amount": 5_000_000,
        "min_term": 6,
        "max_term": 36,
        "min_age": 6,
        "rate": 18.9,
        "badge": "ЛУЧШЕЕ СОВПАДЕНИЕ",
        "description": "Гибкое финансирование ежедневных расходов бизнеса.",
    },
    {
        "id": 2,
        "name": "Бизнес-рост",
        "tagline": "Для расширения компании и запуска новых направлений",
        "purpose": "Развитие бизнеса",
        "min_amount": 1_000_000,
        "max_amount": 15_000_000,
        "min_term": 12,
        "max_term": 60,
        "min_age": 12,
        "rate": 16.5,
        "badge": "ДЛЯ РАЗВИТИЯ",
        "description": "Финансирование масштабирования и долгосрочных планов.",
    },
    {
        "id": 3,
        "name": "Оборудование",
        "tagline": "Для покупки техники, станков и коммерческого оборудования",
        "purpose": "Покупка оборудования",
        "min_amount": 500_000,
        "max_amount": 10_000_000,
        "min_term": 12,
        "max_term": 48,
        "min_age": 12,
        "rate": 15.9,
        "badge": "НА ИНВЕСТИЦИИ",
        "description": "Отдельный продукт для обновления основных средств.",
    },
    {
        "id": 4,
        "name": "Экспресс для бизнеса",
        "tagline": "Для небольших срочных расходов компании",
        "purpose": "Любые бизнес-цели",
        "min_amount": 100_000,
        "max_amount": 1_500_000,
        "min_term": 3,
        "max_term": 24,
        "min_age": 3,
        "rate": 22.4,
        "badge": "БЫСТРЫЙ СТАРТ",
        "description": "Небольшая сумма и короткий срок финансирования.",
    },
]

st.set_page_config(
    page_title="Кредитный помощник ММБ",
    page_icon="◈",
    layout="wide",
    initial_sidebar_state="expanded",
)

API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:5555")
DEMO_MODE = os.getenv("DEMO_MODE", "true").lower() == "true"

# Поля профиля, обязательные для отправки заявки: ассистент уточняет их в диалоге,
# пока все не заполнены (зеркало REQUIRED_PROFILE_FIELDS бэкенда)
REQUIRED_PROFILE_FIELDS = {
    "business_age_months": "срок работы бизнеса (в месяцах)",
    "monthly_revenue": "выручка в месяц (руб.)",
    "monthly_profit": "прибыль в месяц (руб.)",
}

logger = logging.getLogger("frontend")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)

STATUS_LABELS = {
    "draft": ("Черновик", "⚪"),
    "submitted": ("Отправлена", "🔵"),
    "data_check": ("Проверка данных", "🟣"),
    "scoring": ("На скоринге", "🟣"),
    "needs_info": ("Нужны данные", "🟠"),
    "manual_review": ("Ручная экспертиза", "🟠"),
    "approved": ("Одобрена", "🟢"),
    "approved_with_changes": ("Одобрена с изменениями", "🟡"),
    "rejected": ("Отказ", "🔴"),
    "offer_ready": ("Предложение готово", "🟢"),
    "accepted": ("Условия приняты", "🟢"),
    "signed": ("Подписана", "✅"),
    "issued": ("Выдана", "✅"),
    "client_declined": ("Вы отказались от предложения", "⚪"),
    "demo_received": ("Заявка получена · демо", "🔵"),
    "demo_review": ("Демо-проверка", "🟠"),
    "error": ("Ошибка", "🔴"),
}

# Решения скоринга, после которых банк формирует предложение (статус offer_ready)
DECISION_OFFER_STATUSES = {"approved": "offer_ready", "approved_with_changes": "offer_ready"}


def money(value):
    try:
        amount = Decimal(str(value)).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
        return f"{amount:,.0f}".replace(",", " ") + " ₽"
    except Exception:
        return "—"


def payment_calculation(principal, annual_rate, months):
    """Аннуитетный расчёт через общий модуль backend (src/core/calc_payment.py).

    Возвращает ежемесячный платёж, итоговую сумму выплат и переплату.
    Значения совпадают с расчётом, который backend сохраняет в заявке.
    """
    principal = Decimal(str(principal))
    months = int(months)
    rate = Decimal(str(annual_rate))
    if months <= 0 or principal <= 0:
        return Decimal("0"), Decimal("0"), Decimal("0")
    if rate == 0:
        # беспроцентный период — сумма делится равными долями
        monthly = principal / months
    else:
        monthly = Decimal(str(calculate_annuity_payment(principal, float(rate), months)))
    monthly = monthly.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    total = (monthly * months).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    overpayment = total - principal
    return monthly, total, overpayment


def format_message_text(text):
    """Подготовка текста сообщения к выводу в чате.

    Экранирует HTML и преобразует markdown-выделения в теги:
    **жирный** -> <b>жирный</b>, *курсив* -> <i>курсив</i>.
    """
    safe = (
        str(text)
        .strip()  # убираем ведущие/замыкающие отступы и переводы строк
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace("\n", "<br>")
    )
    safe = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", safe, flags=re.DOTALL)
    safe = re.sub(r"(?<!\*)\*([^*\n]+?)\*(?!\*)", r"<i>\1</i>", safe)
    return safe


def api_request(method, path, timeout=8, **kwargs):
    """HTTP-запрос к backend с логированием отправки и получения ответа.

    Таймаут по умолчанию — 8 сек (достаточно для быстрых эндпоинтов).
    LLM-эндпоинты (генерация ответа ассистента) занимают до десятков
    секунд — для них передается увеличенный timeout.
    """
    started = time.perf_counter()
    logger.info("→ %s %s — отправка запроса…", method, path)
    # токен авторизации добавляется ко всем запросам (если пользователь вошёл)
    headers = dict(kwargs.pop("headers", None) or {})
    if st.session_state.get("auth_token"):
        headers.setdefault("Authorization", f"Bearer {st.session_state.auth_token}")
    try:
        response = requests.request(
            method,
            f"{API_BASE_URL}{path}",
            timeout=timeout,
            headers=headers,
            **kwargs,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        logger.error(
            "✗ %s %s — ошибка запроса (%.0f мс): %s",
            method,
            path,
            (time.perf_counter() - started) * 1000,
            exc,
        )
        raise
    logger.info(
        "← %s %s — запрос получен: %s (%.0f мс)",
        method,
        path,
        response.status_code,
        (time.perf_counter() - started) * 1000,
    )
    if response.content:
        return response.json()
    return {}


# ---------------------------------------------------------------------------
# API-клиент: обёртки над всеми эндпоинтами, реализованными на backend (main.py)
# ---------------------------------------------------------------------------

def api_health() -> dict:
    """GET /health — проверка доступности backend."""
    return api_request("GET", "/health")


def api_register(username: str, password: str, role: str = "client") -> dict:
    """POST /api/auth/register — регистрация пользователя."""
    return api_request("POST", "/api/auth/register", json={"username": username, "password": password, "role": role})


def api_login(username: str, password: str) -> dict:
    """POST /api/auth/login — вход (получение токена сессии)."""
    return api_request("POST", "/api/auth/login", json={"username": username, "password": password})


def api_me() -> dict:
    """GET /api/auth/me — текущий пользователь по токену."""
    return api_request("GET", "/api/auth/me")


ROLE_LABELS = {
    "client": "Предприниматель (клиент)",
    "bank_manager": "Кредитный менеджер банка",
    "bank_analyst": "Кредитный аналитик (андеррайтер)",
}

# Роли банковской стороны: им видны служебные блоки заявки («Разбор решения»,
# «История статусов»). Предпринимателю (client) достаточно понятного
# объяснения — кнопка «Объяснить решение (ИИ)» после обработки заявки.
BANK_ROLES = ("bank_manager", "bank_analyst")


def is_bank_user() -> bool:
    """Текущий пользователь — сотрудник банка (не предприниматель)."""
    role = (st.session_state.auth_user or {}).get("role")
    return role in BANK_ROLES


def render_login_page():
    """Страница авторизации: вкладки «Вход» и «Регистрация».

    Живой режим требует входа до основного интерфейса; в демо-режиме
    авторизация не нужна (синтетические данные без backend).
    """
    st.markdown(
        """
        <div class="login-hero">
            <div class="login-icon">◈</div>
            <div class="page-title">ФинПомощник · кредиты для бизнеса</div>
            <div class="login-sub">Войдите, чтобы продолжить диалог о финансировании</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    login_tab, register_tab = st.tabs(["Вход", "Регистрация"])

    with login_tab:
        username = st.text_input("Логин", key="login_username")
        password = st.text_input("Пароль", type="password", key="login_password")
        if st.button("Войти", type="primary", use_container_width=True, key="login_submit"):
            if not username or not password:
                st.warning("Введите логин и пароль.")
            else:
                try:
                    result = api_login(username.strip(), password)
                except requests.HTTPError as exc:
                    if exc.response is not None and exc.response.status_code == 401:
                        st.error("Неверный логин или пароль.")
                    else:
                        st.error(f"Ошибка входа ({exc}).")
                except requests.RequestException as exc:
                    st.error(f"Backend недоступен: {exc}")
                else:
                    st.session_state.auth_token = result.get("token")
                    st.session_state.auth_user = result.get("user")
                    st.rerun()

    with register_tab:
        username = st.text_input("Логин (минимум 3 символа)", key="register_username")
        password = st.text_input("Пароль (минимум 4 символа)", type="password", key="register_password")
        password_repeat = st.text_input("Повторите пароль", type="password", key="register_password_repeat")
        role = st.selectbox(
            "Роль",
            options=list(ROLE_LABELS.keys()),
            format_func=lambda value: ROLE_LABELS[value],
            key="register_role",
        )
        if st.button("Создать аккаунт", type="primary", use_container_width=True, key="register_submit"):
            if not username or not password:
                st.warning("Заполните логин и пароль.")
            elif password != password_repeat:
                st.warning("Пароли не совпадают.")
            else:
                try:
                    result = api_register(username.strip(), password, role)
                except requests.HTTPError as exc:
                    if exc.response is not None and exc.response.status_code == 409:
                        st.error("Этот логин уже занят.")
                    elif exc.response is not None and exc.response.status_code == 422:
                        st.error("Проверьте длину логина (от 3 символов) и пароля (от 4 символов).")
                    else:
                        st.error(f"Ошибка регистрации ({exc}).")
                except requests.RequestException as exc:
                    st.error(f"Backend недоступен: {exc}")
                else:
                    st.session_state.auth_token = result.get("token")
                    st.session_state.auth_user = result.get("user")
                    st.rerun()


def api_create_conversation(state: str = "new") -> dict:
    """POST /api/conversations — создать диалог."""
    return api_request("POST", "/api/conversations", json={"state": state})


def api_send_message(conversation_id, content, profile_id=None, role: str = "user") -> dict:
    """POST /api/conversations/{id}/messages — LLM-конвейер:
    ответ ассистента, извлечённые поля профиля и рекомендации.

    Генерация ответа LLM (с рассуждениями) занимает до десятков секунд,
    поэтому таймаут увеличен до 120 сек (default 8 сек — read timeout).
    """
    return api_request(
        "POST",
        f"/api/conversations/{conversation_id}/messages",
        json={"role": role, "content": content, "profile_id": profile_id},
        timeout=120,
    )


def api_get_conversations() -> dict:
    """GET /api/conversations — список диалогов, свежие сверху."""
    return api_request("GET", "/api/conversations")


def api_get_conversation_messages(conversation_id) -> dict:
    """GET /api/conversations/{id}/messages — все сообщения диалога."""
    return api_request("GET", f"/api/conversations/{conversation_id}/messages")


def api_get_recommendations(profile: dict) -> dict:
    """POST /api/recommendations — подбор продуктов под профиль."""
    return api_request("POST", "/api/recommendations", json=profile)


def api_create_profile(profile_data: dict) -> dict:
    """POST /api/profile — создать профиль бизнеса на backend."""
    return api_request("POST", "/api/profile", json=profile_data)


def api_update_profile(profile_id, profile_data: dict) -> dict:
    """PATCH /api/profile/{id} — обновить переданные поля профиля."""
    return api_request("PATCH", f"/api/profile/{profile_id}", json=profile_data)


def api_get_profile(profile_id) -> dict:
    """GET /api/profile/{id} — получить профиль с backend."""
    return api_request("GET", f"/api/profile/{profile_id}")


def api_calc_profile_payment(profile_id) -> dict:
    """POST /api/profile/{id}/payment — аннуитетный расчёт по профилю:
    лучший продукт, ежемесячный платёж, total и переплата."""
    return api_request("POST", f"/api/profile/{profile_id}/payment")


def api_get_products() -> list:
    """GET /api/products — каталог кредитных продуктов с backend."""
    return api_request("GET", "/api/products")


def api_create_application(profile_id, product_id, amount, term) -> dict:
    """POST /api/applications — создать заявку на backend."""
    return api_request(
        "POST",
        "/api/applications",
        json={
            "profile_id": profile_id,
            "product_id": product_id,
            "requested_amount": amount,
            "term_months": term,
        },
    )


def api_score_application(application_id) -> dict:
    """POST /api/applications/{id}/scoring — повторная обработка заявки на backend."""
    return api_request("POST", f"/api/applications/{application_id}/scoring")


def api_submit_application(application_id) -> dict:
    """POST /api/applications/{id}/submit — отправка черновика + автозапуск конвейера."""
    return api_request("POST", f"/api/applications/{application_id}/submit")


def api_update_application(application_id, amount, term) -> dict:
    """PATCH /api/applications/{id} — правка суммы/срока черновика с пересчётом аннуитета."""
    return api_request(
        "PATCH",
        f"/api/applications/{application_id}",
        json={"requested_amount": int(amount), "term_months": int(term)},
    )


def api_offer_response(application_id, accept: bool, decline_reason=None) -> dict:
    """POST /api/applications/{id}/offer-response — отклик клиента на предложение."""
    payload = {"accept": accept}
    if decline_reason:
        payload["decline_reason"] = decline_reason
    return api_request(
        "POST", f"/api/applications/{application_id}/offer-response", json=payload
    )


def api_sign_application(application_id) -> dict:
    """POST /api/applications/{id}/sign — подписание договора (ЭП моделируется кнопкой)."""
    return api_request("POST", f"/api/applications/{application_id}/sign")


def api_application_history(application_id) -> dict:
    """GET /api/applications/{id}/history — история смены статусов заявки."""
    return api_request("GET", f"/api/applications/{application_id}/history")


def api_explain_application(application_id, audience: str = "client") -> dict:
    """POST /api/applications/{id}/explain — ИИ-объяснение решения по заявке
    (audience: client — для клиента, analyst — сводка для аналитика)."""
    return api_request(
        "POST",
        f"/api/applications/{application_id}/explain",
        json={"audience": audience},
        timeout=120,
    )


WELCOME_MESSAGE = (
    "Здравствуйте! Я ИИ-ассистент по подбору кредитных продуктов для малого и "
    "среднего бизнеса. Расскажите, для чего вам нужно финансирование, какая "
    "сумма требуется и на какой срок. Для отправки заявки мне также понадобятся "
    "срок работы бизнеса, выручка и прибыль в месяц."
)


def init_state():
    defaults = {
        "conversations": [],
        "active_conversation_id": None,
        "messages": [],
        "applications": [],
        "profile": {
            "industry": None,
            "funding_purpose": None,
            "requested_amount": 1_500_000,
            "business_age_months": None,
            "monthly_revenue": None,
            "monthly_profit": None,
            "preferred_term_months": 24,
            "max_monthly_payment": None,
        },
        "recommendations": None,
        "selected_product_id": 1,
        "show_confirm": False,
        "loading": False,
        "api_available": False,
        "api_checked": False,
        "backend_profile_id": None,
        "products": None,
        "awaiting_reply": False,
        "selection_unlocked": False,
        "auth_token": None,
        "auth_user": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def create_conversation():
    conversation_id = str(uuid.uuid4())
    title = "Новая заявка"
    if not DEMO_MODE:
        try:
            result = api_create_conversation()
            conversation_id = str(result.get("id", conversation_id))
        except requests.RequestException:
            st.warning("Backend недоступен. Открыт локальный демо-диалог.")
    st.session_state.conversations.insert(
        0,
        {
            "id": conversation_id,
            "title": title,
            "created_at": datetime.now().strftime("%d.%m.%Y %H:%M"),
        },
    )
    st.session_state.active_conversation_id = conversation_id
    st.session_state.messages = [{"role": "assistant", "content": WELCOME_MESSAGE}]
    st.session_state.recommendations = None
    st.session_state.show_confirm = False
    st.session_state.selection_unlocked = False
    st.session_state.awaiting_reply = False


def load_conversation_messages(conversation_id):
    """Загрузка сообщений диалога с backend в ленту чата (live-режим)."""
    try:
        result = api_get_conversation_messages(conversation_id)
    except requests.RequestException as exc:
        st.warning(f"Не удалось загрузить историю диалога: {exc}")
        return
    messages = [
        {"role": m["role"], "content": m["content"]}
        for m in result.get("messages") or []
        if m.get("role") in ("user", "assistant") and m.get("content")
    ]
    if not messages:
        # пустой диалог на backend — показываем стандартное приветствие
        messages = [{"role": "assistant", "content": WELCOME_MESSAGE}]
    st.session_state.messages = messages
    # заголовок — по первому сообщению пользователя (как при живом диалоге)
    first_user = next((m["content"] for m in messages if m["role"] == "user"), None)
    if first_user:
        conversation = next(
            (c for c in st.session_state.conversations if c["id"] == conversation_id),
            None,
        )
        if conversation:
            conversation["title"] = first_user[:28] + ("…" if len(first_user) > 28 else "")


def restore_conversations():
    """Восстановление истории диалогов с backend после перезагрузки страницы."""
    try:
        result = api_get_conversations()
    except requests.RequestException as exc:
        logger.warning("История диалогов не получена с backend: %s", exc)
        return
    remote = result.get("conversations") or []
    if not remote:
        return
    st.session_state.conversations = [
        {
            "id": str(conv["id"]),
            "title": "Диалог · "
            + datetime.fromisoformat(conv["created_at"]).strftime("%d.%m %H:%M"),
            "created_at": datetime.fromisoformat(conv["created_at"]).strftime("%d.%m.%Y %H:%M"),
        }
        for conv in remote
    ]
    # активным делаем самый свежий диалог и подгружаем его сообщения
    st.session_state.active_conversation_id = st.session_state.conversations[0]["id"]
    load_conversation_messages(st.session_state.active_conversation_id)
    logger.info("История диалогов восстановлена с backend: %d шт.", len(remote))


def calculate_match(product, profile):
    amount = profile.get("requested_amount")
    term = profile.get("preferred_term_months")
    age = profile.get("business_age_months")
    purpose = (profile.get("funding_purpose") or "").lower()
    if not product["min_amount"] <= amount <= product["max_amount"]:
        return None
    if not product["min_term"] <= term <= product["max_term"]:
        return None
    if age is not None and age < product["min_age"]:
        return None
    score = 70
    if purpose and (
        purpose in product["purpose"].lower()
        or any(word in product["purpose"].lower() for word in purpose.split() if len(word) > 3)
    ):
        score += 15
    else:
        score += 5
    term_mid = (product["min_term"] + product["max_term"]) / 2
    score += max(0, 10 - abs(term - term_mid) / max(term_mid, 1))
    return min(round(score), 99)


def get_recommendations():
    profile = st.session_state.profile
    if not DEMO_MODE:
        try:
            result = api_get_recommendations(profile)
            recommendations = result.get("recommendations") or []
            st.session_state.recommendations = recommendations
            if recommendations:
                st.session_state.selected_product_id = recommendations[0]["id"]
            return
        except requests.RequestException as exc:
            st.error(f"Не удалось получить рекомендации из backend: {exc}")
            return
    catalog = st.session_state.products or PRODUCTS
    results = []
    for product in catalog:
        score = calculate_match(product, profile)
        if score is not None:
            results.append({**product, "score": score})
    results.sort(key=lambda item: (item["score"], -item["rate"]), reverse=True)
    st.session_state.recommendations = results
    if results:
        st.session_state.selected_product_id = results[0]["id"]


def ensure_backend_profile():
    """Идентификатор профиля на backend: создаёт профиль при первом обращении."""
    if st.session_state.backend_profile_id is not None:
        return st.session_state.backend_profile_id
    profile_data = {
        key: value for key, value in st.session_state.profile.items() if value is not None
    }
    # POST /api/profile требует industry и funding_purpose (в БД они NOT NULL),
    # но в начале диалога они ещё не извлечены — ставим нейтральные заглушки;
    # LLM-конвейер перезапишет их реальными значениями из сообщений пользователя.
    profile_data.setdefault("industry", "Не указано")
    profile_data.setdefault("funding_purpose", "Не указано")
    result = api_create_profile(profile_data)
    st.session_state.backend_profile_id = result.get("id")
    return st.session_state.backend_profile_id


def run_local_scoring(product, amount, term, monthly):
    """Скоринг той же моделью, что на backend (src/core/scoring.py)."""
    result = score_application(
        st.session_state.profile, product, int(amount), int(term), float(monthly)
    )
    return result.to_dict()


def submit_application(product, amount, term):
    """Создание черновика заявки: консультация -> профиль -> черновик (без скоринга)."""
    monthly, total, overpayment = payment_calculation(amount, product["rate"], term)
    application_id = str(uuid.uuid4())[:8].upper()
    if not DEMO_MODE:
        try:
            profile_id = ensure_backend_profile()
            created = api_create_application(
                profile_id, product["id"], int(amount), int(term)
            )
            application = created.get("application") or {}
            application_id = application.get("id", application_id)
            status = application.get("status", "draft")
        except requests.RequestException as exc:
            logger.error("Не удалось создать заявку на backend: %s", exc)
            st.error(f"Заявка не создана: backend недоступен ({exc}).")
            return False
    else:
        status = "draft"

    application_record = {
        "id": application_id,
        "product_name": product["name"],
        "product_id": product["id"],
        "amount": int(amount),
        "term": int(term),
        "monthly_payment": float(monthly),
        "total_repayment": float(total),
        "overpayment": float(overpayment),
        "status": status,
        "score": None,
        "decision_details": {},
        "created_at": datetime.now().strftime("%d.%m.%Y %H:%M"),
    }
    st.session_state.applications.insert(0, application_record)
    st.session_state.show_confirm = False

    label = STATUS_LABELS.get(status, ("Получена", "🔵"))[0]
    message = (
        f"Заявка № {application_id} сохранена как черновик (статус «{label}»). "
        "Отправьте её на обработку в разделе «Мои заявки», когда будете готовы."
    )
    message += " Решение демонстрационное и не является офертой банка."
    st.session_state.messages.append({"role": "assistant", "content": message})
    return True


def find_application_product(application):
    """Продукт заявки по product_id из каталога (backend или локального)."""
    return next(
        (
            p
            for p in (st.session_state.products or PRODUCTS)
            if p.get("id") == application.get("product_id")
        ),
        None,
    )


def send_application(application):
    """Отправка черновика на обработку: draft -> submitted (+ конвейер на backend)."""
    if not DEMO_MODE:
        try:
            result = api_submit_application(application["id"])
        except requests.RequestException as exc:
            logger.error("Не удалось отправить заявку на backend: %s", exc)
            st.error(f"Заявка не отправлена: {exc}")
            return False
        updated = result.get("application") or {}
        scoring = result.get("scoring") or {}
        application["status"] = updated.get("status", application["status"])
        application["score"] = updated.get("score")
        application["decision_details"] = scoring or (updated.get("decision_details") or {})
        explanation = (application.get("decision_details") or {}).get("explanation")
        message = f"Заявка № {application['id']} отправлена и обработана."
        if explanation:
            message += f" {explanation}"
        message += " Решение демонстрационное и не является офертой банка."
        st.session_state.messages.append({"role": "assistant", "content": message})
        return True
    # демо-режим: локальный скоринг той же моделью, одобрение -> предложение
    return rescore_application(application)


def update_draft(application, amount, term):
    """Правка черновика: сумма/срок с пересчётом аннуитета (PATCH на backend)."""
    if not DEMO_MODE:
        try:
            result = api_update_application(application["id"], int(amount), int(term))
        except requests.RequestException as exc:
            logger.error("Не удалось сохранить черновик на backend: %s", exc)
            st.error(f"Изменения не сохранены: {exc}")
            return False
        updated = result.get("application") or {}
        application["amount"] = updated.get("requested_amount", application["amount"])
        application["term"] = updated.get("term_months", application["term"])
        application["monthly_payment"] = updated.get(
            "monthly_payment", application["monthly_payment"]
        )
        application["total_repayment"] = updated.get(
            "total_repayment", application["total_repayment"]
        )
        application["overpayment"] = updated.get("overpayment", application["overpayment"])
        return True
    product = find_application_product(application)
    if product is None:
        st.error("Продукт заявки не найден в каталоге.")
        return False
    monthly, total, overpayment = payment_calculation(amount, product["rate"], term)
    application["amount"] = int(amount)
    application["term"] = int(term)
    application["monthly_payment"] = float(monthly)
    application["total_repayment"] = float(total)
    application["overpayment"] = float(overpayment)
    return True


def accept_offer(application):
    """Принятие предложения: offer_ready -> accepted."""
    if not DEMO_MODE:
        try:
            result = api_offer_response(application["id"], accept=True)
        except requests.RequestException as exc:
            logger.error("Не удалось принять предложение: %s", exc)
            st.error(f"Не удалось принять предложение: {exc}")
            return False
        application["status"] = (result.get("application") or {}).get("status", "accepted")
    else:
        application["status"] = "accepted"
    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": (
                f"Условия по заявке № {application['id']} приняты. "
                "Можно подписывать договор."
            ),
        }
    )
    return True


def decline_offer(application):
    """Отказ от предложения: offer_ready -> client_declined."""
    if not DEMO_MODE:
        try:
            result = api_offer_response(application["id"], accept=False)
        except requests.RequestException as exc:
            logger.error("Не удалось отклонить предложение: %s", exc)
            st.error(f"Не удалось отклонить предложение: {exc}")
            return False
        application["status"] = (result.get("application") or {}).get(
            "status", "client_declined"
        )
    else:
        application["status"] = "client_declined"
    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": (
                f"Предложение по заявке № {application['id']} отклонено. "
                "Вы можете создать новую заявку на других условиях."
            ),
        }
    )
    return True


def sign_application(application):
    """Подписание договора (ЭП моделируется кнопкой): accepted -> signed -> issued."""
    if not DEMO_MODE:
        try:
            result = api_sign_application(application["id"])
        except requests.RequestException as exc:
            logger.error("Не удалось подписать договор на backend: %s", exc)
            st.error(f"Не удалось подписать договор: {exc}")
            return False
        application["status"] = (result.get("application") or {}).get("status", "issued")
    else:
        application["status"] = "issued"
    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": (
                f"Договор по заявке № {application['id']} подписан. "
                "Выдача финансирования смоделирована: в демо-режиме деньги не переводятся."
            ),
        }
    )
    return True


def render_application_history(application):
    """Таймлайн истории статусов: «статус — дата — комментарий»."""
    with st.expander("История статусов", key=f"app_history_{application.get('id')}"):
        try:
            result = api_application_history(application["id"])
        except requests.RequestException as exc:
            logger.error("История статусов недоступна: %s", exc)
            st.caption("История недоступна: backend не отвечает.")
            return
        history = result.get("history") or []
        if not history:
            st.caption("История пуста.")
            return
        for item in history:
            to_label = STATUS_LABELS.get(item.get("to_status"), (item.get("to_status"), ""))[0]
            when = str(item.get("created_at", ""))[:16].replace("T", " ")
            line = f"**{to_label}** — {when}"
            if item.get("comment"):
                line += f" — {item['comment']}"
            st.markdown(line)


def attach_alternatives(application, scoring):
    """Демо-режим: альтернативные продукты при отказе — той же логикой,
    что и конвейер backend (п. 2.7)."""
    decision = scoring.get("decision")
    if decision not in ("rejected", "approved_with_changes"):
        return
    if decision == "approved_with_changes" and scoring.get("suggested_amount") is not None:
        return
    profile = dict(st.session_state.profile)
    profile["requested_amount"] = application.get("amount")
    profile["preferred_term_months"] = application.get("term")
    scoring["alternatives"] = suggest_alternative_products(
        profile, exclude_product_id=application.get("product_id")
    )


def create_alternative_application(application, alternative):
    """Оформление заявки на альтернативный продукт после отказа (п. 2.7):
    новый черновик с суммой/сроком, вписанными в диапазон продукта."""
    try:
        profile_id = ensure_backend_profile()
        created = api_create_application(
            profile_id,
            alternative["id"],
            int(alternative["amount"]),
            int(alternative["term_months"]),
        )
    except requests.RequestException as exc:
        logger.error("Не удалось создать заявку на альтернативу: %s", exc)
        st.error(f"Заявка не создана: backend недоступен ({exc}).")
        return False
    new_application = created.get("application") or {}
    record = {
        "id": new_application.get("id"),
        "product_name": new_application.get("product_name", alternative.get("name")),
        "product_id": alternative.get("id"),
        "amount": int(alternative.get("amount")),
        "term": int(alternative.get("term_months")),
        "monthly_payment": new_application.get(
            "monthly_payment", alternative.get("monthly_payment")
        ),
        "total_repayment": new_application.get(
            "total_repayment", alternative.get("total_repayment")
        ),
        "overpayment": new_application.get("overpayment", alternative.get("overpayment")),
        "status": new_application.get("status", "draft"),
        "score": None,
        "decision_details": {},
        "created_at": datetime.now().strftime("%d.%m.%Y %H:%M"),
    }
    st.session_state.applications.insert(0, record)
    message = (
        f"Заявка № {record['id']} на продукт «{record['product_name']}» сохранена "
        "как черновик — альтернатива после отказа. Проверьте параметры и отправьте "
        "её на обработку в разделе «Мои заявки»."
    )
    message += " Решение демонстрационное и не является офертой банка."
    st.session_state.messages.append({"role": "assistant", "content": message})
    return True


def rescore_application(application):
    """Повторная обработка после уточнения данных (needs_info -> решение -> предложение)."""
    product = find_application_product(application)
    if product is None:
        st.error("Продукт заявки не найден в каталоге.")
        return False
    if not DEMO_MODE:
        try:
            result = api_score_application(application["id"])
            updated = result.get("application") or {}
            scoring = result.get("scoring") or {}
            application["status"] = updated.get("status", application["status"])
            application["score"] = updated.get("score")
            application["decision_details"] = scoring
        except requests.RequestException as exc:
            logger.error("Повторная обработка не выполнена: %s", exc)
            st.error(f"Повторная обработка не выполнена: {exc}")
            return False
    else:
        scoring = run_local_scoring(
            product, application["amount"], application["term"], application["monthly_payment"]
        )
        decision = scoring.get("decision", application["status"])
        # демо-режим: одобрение отображаем как готовое предложение (offer_ready)
        application["status"] = DECISION_OFFER_STATUSES.get(decision, decision)
        application["score"] = scoring.get("score")
        attach_alternatives(application, scoring)
        application["decision_details"] = scoring
    explanation = (application.get("decision_details") or {}).get(
        "explanation", "Повторный скоринг выполнен."
    )
    st.session_state.messages.append({"role": "assistant", "content": explanation})
    return True


init_state()

# Живой режим: страница авторизации до основного интерфейса
# (демо-режим работает без авторизации — синтетические данные без backend)
if not DEMO_MODE and st.session_state.auth_token is None:
    render_login_page()
    st.stop()

# Живой режим: при первом запуске проверяем backend и подтягиваем каталог продуктов
if not DEMO_MODE and not st.session_state.api_checked:
    st.session_state.api_checked = True
    try:
        api_health()
        st.session_state.api_available = True
        logger.info("Backend доступен: %s", API_BASE_URL)
    except requests.RequestException as exc:
        st.session_state.api_available = False
        logger.warning("Backend недоступен (%s): %s", API_BASE_URL, exc)
    if st.session_state.api_available:
        try:
            products = api_get_products()
            if products:
                st.session_state.products = products
                logger.info("Каталог продуктов получен с backend: %d позиций", len(products))
        except requests.RequestException as exc:
            logger.warning("Каталог продуктов не получен с backend, используется локальный: %s", exc)
        # история диалогов живёт в БД backend — восстанавливаем после перезагрузки
        restore_conversations()

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
    :root { --ink:#e8edf8; --muted:#93a0b8; --line:#26304a; --blue:#4f8cff; --blue-soft:#182642; --green:#3ddc97; --panel:#141a28; }
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    .stApp { background: #0b0f1a; color: var(--ink); }
    header[data-testid="stHeader"] { background: transparent; }
    [data-testid="stSidebar"] { background: #0e1424; border-right: 1px solid var(--line); }
    [data-testid="stSidebar"] > div:first-child { padding-top: 0.4rem; }
    .brand { display:flex; align-items:center; gap:10px; padding:4px 2px 22px; }
    .brand-icon { width:38px; height:38px; border-radius:12px; display:flex; align-items:center; justify-content:center; color:#fff; background:linear-gradient(145deg,#3568ed,#2147b6); font-size:22px; font-weight:800; box-shadow:0 5px 15px #4f8cff40; }
    .brand-name { font-weight:800; font-size:15px; letter-spacing:-.4px; color:#f2f5fc; }
    .brand-sub { font-size:11px; color:#8d99b0; margin-top:2px; }
    .section-kicker { font-size:10px; font-weight:800; letter-spacing:1.3px; color:#7f8ca6; margin:17px 0 9px; text-transform:uppercase; }
    .page-title { font-size:28px; line-height:1.2; font-weight:800; letter-spacing:-1.1px; color:#f2f5fc; margin:0 0 7px; }
    .page-subtitle { font-size:13px; color:#93a0b8; margin-bottom:22px; }
    .eyebrow { color:#6ea8ff; font-size:10px; letter-spacing:1.5px; font-weight:800; text-transform:uppercase; margin-bottom:8px; }
    .hero { background:linear-gradient(120deg,#173b9b 0%,#2459d3 55%,#5080ee 100%); color:white; border-radius:20px; padding:24px 25px; margin-bottom:18px; box-shadow:0 12px 30px #00000040; }
    .hero h2 { color:white; font-size:22px; letter-spacing:-.6px; margin:0 0 8px; }
    .hero p { color:#e1eaff; font-size:12px; line-height:1.7; margin:0; max-width:650px; }
    .hero-pill { display:inline-block; border:1px solid #ffffff50; border-radius:100px; padding:5px 9px; color:#fff; font-size:10px; font-weight:700; margin-bottom:13px; }
    .panel { background:var(--panel); border:1px solid var(--line); border-radius:16px; padding:18px; margin-bottom:12px; }
    .panel-title { font-size:15px; font-weight:750; color:#eef2fb; margin-bottom:5px; }
    .panel-sub { color:#93a0b8; font-size:11px; line-height:1.6; }
    .product-card { background:var(--panel); border:1px solid var(--line); border-radius:16px; padding:17px; margin:0 0 12px; position:relative; }
    .product-card.top { border:1.5px solid #4f8cff; background:linear-gradient(145deg,#1b2742 0%,#141a28 60%); box-shadow:0 7px 24px #4f8cff26; }
    .product-rank { font-size:9px; font-weight:800; letter-spacing:.7px; color:#9cc0ff; background:#1d2f55; display:inline-block; padding:5px 8px; border-radius:6px; margin-bottom:10px; }
    .product-name { color:#f0f4fd; font-size:15px; font-weight:800; margin-bottom:5px; }
    .product-desc { color:#93a0b8; font-size:11px; line-height:1.6; margin-bottom:13px; min-height:34px; }
    .metric-label { font-size:10px; color:#8d99b0; margin-bottom:4px; }
    .metric-value { font-size:14px; color:#eef2fb; font-weight:800; }
    .metric-rate { color:#6ea8ff; font-size:20px; font-weight:800; letter-spacing:-.5px; }
    .product-foot { border-top:1px solid #232d45; padding-top:10px; margin-top:12px; font-size:10px; color:#8d99b0; }
    .chat-shell { background:var(--panel); border:1px solid var(--line); border-radius:18px; overflow:hidden; }
    .chat-header { display:flex; align-items:center; gap:10px; padding:15px 18px; border-bottom:1px solid #232d45; }
    .bot-avatar { display:flex; align-items:center; justify-content:center; width:34px; height:34px; border-radius:11px; background:#1d2f55; color:#6ea8ff; font-size:18px; }
    .chat-header-title { font-size:13px; font-weight:800; color:#eef2fb; }
    .chat-header-sub { font-size:10px; color:#93a0b8; margin-top:3px; }
    .online-dot { display:inline-block; width:6px; height:6px; border-radius:50%; background:#3ddc97; margin-right:5px; }
    .chat-space { padding:18px; min-height:300px; }
    .chat-note { font-size:11px; color:#7f8ca6; text-align:center; margin:4px 0 18px; }
    .bubble { padding:14px 16px; border-radius:14px; font-size:14.5px; line-height:1.75; margin-bottom:14px; max-width:94%; white-space:pre-wrap; overflow-wrap:anywhere; }
    .bubble.assistant { background:#1c2438; color:#dfe6f5; border-bottom-left-radius:4px; }
    .bubble.user { background:#2459d3; color:white; margin-left:auto; border-bottom-right-radius:4px; }
    .bubble-label { font-size:10.5px; color:#7f8ca6; margin-bottom:5px; }
    .typing-dots { display:inline-flex; align-items:center; gap:5px; padding:14px 16px; background:#1c2438; border-radius:14px; border-bottom-left-radius:4px; margin-bottom:14px; }
    .typing-dots span { width:8px; height:8px; border-radius:50%; background:#6ea8ff; display:inline-block; animation:typing-blink 1.2s infinite ease-in-out; }
    .typing-dots span:nth-child(2) { animation-delay:0.2s; }
    .typing-dots span:nth-child(3) { animation-delay:0.4s; }
    @keyframes typing-blink { 0%, 60%, 100% { transform:scale(0.7); opacity:0.35; } 30% { transform:scale(1); opacity:1; } }
    .application-row { border:1px solid var(--line); border-radius:12px; padding:12px; margin-bottom:9px; background:var(--panel); }
    .application-name { font-size:12px; font-weight:750; color:#eef2fb; }
    .application-meta { font-size:10px; color:#93a0b8; margin-top:5px; line-height:1.6; }
    .status-note { background:#2a2413; border:1px solid #4a3d1c; border-radius:10px; padding:10px 12px; color:#e8c37a; font-size:10px; line-height:1.6; }
    .skeleton { background:linear-gradient(90deg,#1a2133 25%,#26304a 37%,#1a2133 63%); background-size:400% 100%; border-radius:8px; height:13px; margin:10px 0; }
    div.stButton > button { border-radius:10px; font-weight:650; min-height:38px; }
    div[data-testid="stChatInput"] { border-color:var(--line); }
    div[data-testid="stMetric"] { background:var(--panel); border:1px solid var(--line); border-radius:12px; padding:12px 14px; }
    div[data-testid="stMetricLabel"] { font-size:11px; }
    div[data-testid="stMetricValue"] { font-size:20px; }
    main.block-container, div[data-testid="stMainBlockContainer"] { padding-top: 1rem !important; padding-bottom: 1rem !important; }
    .chip-label { font-size:10px; font-weight:800; letter-spacing:.8px; color:#7f8ca6; text-transform:uppercase; margin:12px 0 6px; }
    .param-summary { display:flex; flex-wrap:wrap; gap:8px; margin:2px 0 6px; }
    .param-pill { border:1px solid var(--line); border-radius:9px; padding:7px 10px; font-size:11px; color:#dfe6f5; background:#101627; }
    .param-pill b { color:#6ea8ff; font-weight:700; }
    .product-row { display:flex; align-items:center; gap:12px; border:1px solid var(--line); border-radius:12px; padding:11px 13px; margin-bottom:8px; background:var(--panel); }
    .product-row.selected { border:1.5px solid #4f8cff; background:linear-gradient(145deg,#1b2742 0%,#141a28 60%); }
    .product-row-name { font-size:12.5px; font-weight:750; color:#eef2fb; }
    .product-row-meta { font-size:10.5px; color:#93a0b8; margin-top:3px; line-height:1.5; }
    .product-row-badge { margin-left:auto; font-size:9px; font-weight:800; letter-spacing:.6px; color:#9cc0ff; background:#1d2f55; padding:4px 8px; border-radius:6px; white-space:nowrap; }
    div[data-testid="stExpander"] { border:1px solid var(--line); border-radius:12px; }
    @media (max-width: 900px) { .page-title {font-size:23px;} .hero {padding:18px;} .product-card {padding:13px;} }
    .login-hero { max-width:520px; margin:9vh auto 26px; text-align:center; }
    .login-icon { width:64px; height:64px; margin:0 auto 18px; border-radius:20px; display:flex; align-items:center; justify-content:center; color:#fff; background:linear-gradient(145deg,#3568ed,#2147b6); font-size:34px; font-weight:800; box-shadow:0 10px 30px #0008; }
    .login-sub { color:var(--muted); font-size:13.5px; margin-top:8px; }
    </style>
    """,
    unsafe_allow_html=True,
)

with st.sidebar:
    st.markdown(
        """
        <div class="brand">
            <div class="brand-icon">◈</div>
            <div><div class="brand-name">ФинПомощник</div><div class="brand-sub">Кредитные решения для бизнеса</div></div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if st.button("＋  Новая заявка", use_container_width=True, type="primary"):
        create_conversation()
        st.rerun()
    st.markdown('<div class="section-kicker">История диалогов</div>', unsafe_allow_html=True)
    if not st.session_state.conversations:
        st.markdown('<div style="font-size:11px;color:#98a3b3;padding:7px 2px 12px;">Здесь появятся ваши диалоги</div>', unsafe_allow_html=True)
    for conversation in st.session_state.conversations:
        label = "◉  " + conversation["title"]
        if st.button(label, key=f"conversation_{conversation['id']}", use_container_width=True):
            if st.session_state.active_conversation_id != conversation["id"]:
                st.session_state.active_conversation_id = conversation["id"]
                # в live-режиме сообщения диалога подгружаются с backend
                if not DEMO_MODE and st.session_state.api_available:
                    load_conversation_messages(conversation["id"])
            st.rerun()
    # Заявки перенесены в expander «История заявок» правой панели (упрощение UI)
    if DEMO_MODE:
        st.caption("● Демо-режим · синтетические данные")
    else:
        # карточка текущего пользователя + выход (живой режим с авторизацией)
        if st.session_state.auth_user:
            role_label = ROLE_LABELS.get(
                st.session_state.auth_user.get("role"), st.session_state.auth_user.get("role")
            )
            st.markdown('<div class="section-kicker">Аккаунт</div>', unsafe_allow_html=True)
            st.markdown(
                f'<div style="font-size:12px;color:#e8edf8;padding:4px 2px;">👤 {st.session_state.auth_user.get("username")}</div>'
                f'<div style="font-size:10.5px;color:#93a0b8;padding:2px 2px 10px;">{role_label}</div>',
                unsafe_allow_html=True,
            )
            if st.button("⏻  Выйти", use_container_width=True):
                st.session_state.auth_token = None
                st.session_state.auth_user = None
                st.rerun()
        backend_state = "онлайн" if st.session_state.api_available else "недоступен"
        st.caption(f"API: {API_BASE_URL} · {backend_state}")

# «Минимум»: без hero-экрана — диалог начинается сразу
if not st.session_state.active_conversation_id:
    create_conversation()

if st.session_state.loading:
    st.markdown(
        """
        <div class="panel">
            <div class="skeleton" style="width:34%"></div>
            <div class="skeleton" style="width:72%;height:11px"></div>
            <div class="skeleton" style="width:57%;height:11px"></div>
            <div style="display:flex;gap:12px;margin-top:20px">
                <div style="flex:1;background:#1a2133;border-radius:12px;padding:12px"><div class="skeleton" style="width:70%"></div><div class="skeleton" style="width:48%;height:24px"></div></div>
                <div style="flex:1;background:#1a2133;border-radius:12px;padding:12px"><div class="skeleton" style="width:62%"></div><div class="skeleton" style="width:54%;height:24px"></div></div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

chat_col, product_col = st.columns([1.5, 1], gap="large")

with chat_col:
    st.markdown(
        """
        <div class="chat-shell">
            <div class="chat-header">
                <div class="bot-avatar">✳</div>
                <div style="flex:1">
                    <div class="chat-header-title">ИИ-ассистент</div>
                    <div class="chat-header-sub"><span class="online-dot"></span>Помощь с подбором финансирования</div>
                </div>
                <div style="font-size:10px;color:#8b98aa">MVP</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    with st.container(border=True, height=640):
        st.markdown('<div class="chat-note">Сообщения этого диалога</div>', unsafe_allow_html=True)
        if not st.session_state.messages:
            st.markdown('<div class="bubble assistant">Здравствуйте! Я ИИ-ассистент. Расскажите, какая задача стоит перед вашим бизнесом и какое финансирование вам нужно.</div>', unsafe_allow_html=True)
        else:
            for message in st.session_state.messages:
                role = message["role"]
                label = "Вы" if role == "user" else "ИИ-ассистент"
                bubble_class = "user" if role == "user" else "assistant"
                safe_content = format_message_text(message["content"])
                st.markdown(
                    f'<div class="bubble-label" style="text-align:{"right" if role == "user" else "left"}">{label}</div><div class="bubble {bubble_class}">{safe_content}</div>',
                    unsafe_allow_html=True,
                )
        # Индикатор «ассистент печатает» — внутри ленты сообщений
        if st.session_state.awaiting_reply:
            st.markdown(
                '<div class="bubble-label">ИИ-ассистент</div>'
                '<div class="typing-dots"><span></span><span></span><span></span></div>',
                unsafe_allow_html=True,
            )
    prompt = st.chat_input("Напишите о потребности бизнеса…", key="chat_prompt")
    if prompt:
        st.session_state.messages.append({"role": "user", "content": prompt})
        conversation = next(
            (c for c in st.session_state.conversations if c["id"] == st.session_state.active_conversation_id),
            None,
        )
        if conversation and conversation["title"] == "Новая заявка":
            conversation["title"] = prompt[:28] + ("…" if len(prompt) > 28 else "")
        # Ответ генерируется на следующем прогоне: чат отрисуется вместе с
        # сообщением пользователя и индикатором «печатает» внутри ленты.
        st.session_state.awaiting_reply = True
        st.rerun()

    if st.session_state.awaiting_reply:
        # Запрос к ассистенту выполняется после отрисовки чата, поэтому
        # анимация ожидания видна внутри ленты сообщений.
        try:
            if DEMO_MODE:
                time.sleep(0.8)
                missing = [
                    label
                    for key, label in REQUIRED_PROFILE_FIELDS.items()
                    if st.session_state.profile.get(key) is None
                ]
                if missing:
                    reply_text = (
                        "Спасибо, я принял описание. Для отправки заявки не хватает "
                        "данных: " + ", ".join(missing) + ". Уточните их, а также "
                        "сумму, цель и срок финансирования."
                    )
                else:
                    reply_text = (
                        "Спасибо, все обязательные параметры зафиксированы. "
                        "Нажмите «Подобрать продукты» — подберу варианты под ваш запрос."
                    )
            else:
                # Профиль на backend создаётся при первом сообщении —
                # тогда конвейер извлекает поля из каждого сообщения диалога
                # и возвращает рекомендации, как только известны сумма и срок.
                profile_id = ensure_backend_profile()
                result = api_send_message(
                    st.session_state.active_conversation_id,
                    st.session_state.messages[-1]["content"],
                    profile_id=profile_id,
                )
                reply_text = result.get("reply", "Сообщение принято.")
                updates = result.get("profile_updates") or {}
                st.session_state.profile.update(
                    {key: value for key, value in updates.items() if value is not None}
                )
                recommendations = result.get("recommendations") or []
                if recommendations:
                    st.session_state.recommendations = recommendations
                    st.session_state.selected_product_id = recommendations[0]["id"]
                    if not st.session_state.selection_unlocked:
                        # панель выбора открывается автоматически, как только
                        # данных профиля достаточно для подбора продуктов
                        st.session_state.selection_unlocked = True
                        st.session_state.messages.append(
                            {
                                "role": "assistant",
                                "content": "Данных достаточно — подобрал подходящие продукты. Выберите вариант в панели «Подобранные продукты» справа.",
                            }
                        )
            st.session_state.messages.append({"role": "assistant", "content": reply_text})
        except requests.RequestException as exc:
            st.session_state.messages.append(
                {"role": "assistant", "content": f"Не удалось связаться с сервером: {exc}"}
            )
        st.session_state.awaiting_reply = False
        st.rerun()
    # Кнопка подбора появляется ровно тогда, когда ассистент собрал все
    # обязательные данные профиля — до этого подбор недоступен «в обход» диалога
    profile_ready = all(
        st.session_state.profile.get(key) is not None
        for key in REQUIRED_PROFILE_FIELDS
    )
    if profile_ready and st.button("✦  Подобрать продукты", key="chat_recommend", use_container_width=True, type="primary"):
        with st.spinner("Подбираем продукты…"):
            get_recommendations()
        # Выбор продукта открывается только после явного подбора
        st.session_state.selection_unlocked = True
        st.session_state.messages.append({"role": "assistant", "content": "Готово! Подобрал продукты под ваши параметры — выберите подходящий в панели «Подобранные продукты» справа."})
        st.rerun()

with product_col:
    recommendations = st.session_state.recommendations
    if not (recommendations and st.session_state.selection_unlocked):
        # Выбор продукта открывается только после подбора в чате
        st.markdown(
            '<div class="panel"><div class="panel-title">Кредитные продукты</div>'
            '<div class="panel-sub">Опишите потребность бизнеса в чате — ассистент уточнит недостающие данные и подберёт подходящие варианты.</div></div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown('<div class="chip-label">Подобранные продукты</div>', unsafe_allow_html=True)
        for index, product in enumerate(recommendations):
            if not isinstance(product, dict):
                continue
            rate = float(product.get("rate", product.get("annual_rate", 18.9)))
            product_amount = int(st.session_state.profile.get("requested_amount") or product.get("min_amount", 100000))
            product_term = int(st.session_state.profile.get("preferred_term_months") or 24)
            monthly, _, _ = payment_calculation(product_amount, rate, product_term)
            chip_label = f"{'★ ' if index == 0 else ''}{product.get('name', 'Продукт')} · {rate:.1f}%"
            selected_now = st.session_state.selected_product_id == product.get("id")
            if st.button(chip_label, key=f"chat_choose_{product.get('id', index)}", use_container_width=True, type="primary" if selected_now else "secondary", help=f"Платёж ≈ {money(monthly)}/мес"):
                st.session_state.selected_product_id = product.get("id", index)
                st.session_state.show_confirm = True
                st.session_state.messages.append({"role": "user", "content": f"Выбираю «{product.get('name')}»."})
                st.session_state.messages.append({"role": "assistant", "content": f"Хороший выбор: «{product.get('name')}» под {rate:.1f}% в год, платёж ≈ {money(monthly)}/мес. Проверьте параметры заявки справа — отправлю только после вашего подтверждения."})
                st.rerun()
        if st.session_state.show_confirm:
            selected = next(
                (p for p in recommendations if p.get("id") == st.session_state.selected_product_id),
                recommendations[0],
            )
            st.markdown('<div class="panel-title" style="margin-top:10px">Параметры заявки</div><div class="panel-sub">Проверьте сумму и срок. Перед отправкой потребуется отдельное подтверждение.</div>', unsafe_allow_html=True)
            selected_rate = float(selected.get("rate", selected.get("annual_rate", 18.9)))
            amount_min = int(selected.get("min_amount", 100_000))
            amount_max = int(selected.get("max_amount", 50_000_000))
            amount_default = max(amount_min, min(int(st.session_state.profile.get("requested_amount") or amount_min), amount_max))
            term_min = int(selected.get("min_term", 3))
            term_max = int(selected.get("max_term", 60))
            term_default = max(term_min, min(int(st.session_state.profile.get("preferred_term_months") or term_min), term_max))
            chosen_amount = st.number_input("Сумма заявки, ₽", min_value=amount_min, max_value=amount_max, step=100_000, value=amount_default, key="application_amount")
            chosen_term = st.number_input("Срок заявки, месяцев", min_value=term_min, max_value=term_max, value=term_default, key="application_term")
            monthly, total, overpayment = payment_calculation(chosen_amount, selected_rate, chosen_term)
            metric_a, metric_b, metric_c = st.columns(3)
            metric_a.metric("Платёж в месяц", money(monthly))
            metric_b.metric("Всего к возврату", money(total))
            metric_c.metric("Переплата", money(overpayment))
            st.caption("Расчёт аннуитетный, ориентировочный. Не учитывает комиссии, страховку, нерегулярные даты платежей и досрочное погашение.")
            st.markdown('<div class="status-note">Отправка заявки не означает одобрение кредита. В демо-режиме статус назначается автоматически и не отражает решение банка.</div>', unsafe_allow_html=True)
            confirmed = st.checkbox("Подтверждаю отправку заявки с указанными параметрами")
            confirm_col, cancel_col = st.columns(2)
            with confirm_col:
                if st.button("Подтвердить и отправить", type="primary", use_container_width=True, disabled=not confirmed):
                    if submit_application(selected, int(chosen_amount), int(chosen_term)):
                        st.success("Демонстрационная заявка создана.")
                        st.rerun()
            with cancel_col:
                if st.button("Отмена", use_container_width=True):
                    st.session_state.show_confirm = False
                    st.rerun()

    # --- Мои заявки: путь от обращения до выдачи ---------------------------
    if st.session_state.applications:
        st.markdown('<div class="chip-label">Мои заявки</div>', unsafe_allow_html=True)
        for application in st.session_state.applications:
            status_key = application.get("status", "draft")
            status_label, status_icon = STATUS_LABELS.get(status_key, ("Получена", "🔵"))
            details = application.get("decision_details") or {}
            score_line = (
                f" · балл скоринга: {application['score']:g}"
                if application.get("score") is not None
                else ""
            )
            st.markdown(
                f'<div class="application-row">'
                f'<div class="application-name">{status_icon} {application.get("product_name", "Заявка")} · № {application.get("id")}</div>'
                f'<div class="application-meta">'
                f'{money(application.get("amount"))} на {application.get("term")} мес · '
                f'платёж {money(application.get("monthly_payment"))}/мес<br>'
                f'Статус: {status_label}{score_line}'
                f'</div></div>',
                unsafe_allow_html=True,
            )
            if details.get("explanation"):
                st.caption(details["explanation"])
            # «Разбор решения» (факторы скоринга) — служебный блок сотрудников
            # банка; предпринимателю остаётся «Объяснить решение (ИИ)»
            if details.get("factors") and is_bank_user():
                with st.expander("Разбор решения", key=f"app_factors_{application.get('id')}"):
                    for factor in details["factors"]:
                        contribution = factor.get("contribution")
                        contribution_line = (
                            f" · вклад в балл: {contribution:+g}"
                            if contribution is not None
                            else ""
                        )
                        st.markdown(
                            f"**{factor.get('label', factor.get('name'))}** — "
                            f"{factor.get('value')}{contribution_line}"
                        )
                    missing = details.get("missing_fields") or []
                    if missing:
                        st.caption(
                            "Полнота данных: не заполнены поля — " + ", ".join(missing) + "."
                        )
                    else:
                        st.caption("Полнота данных: все обязательные поля профиля заполнены.")
                    st.caption(
                        "Стоп-факторы: не зафиксированы (проверка данных пройдена автоматически)."
                    )
            if details.get("decision") and not DEMO_MODE:
                if st.button(
                    "Объяснить решение (ИИ)",
                    key=f"app_explain_{application.get('id')}",
                ):
                    try:
                        result = api_explain_application(application["id"])
                    except requests.RequestException as exc:
                        logger.error("ИИ-объяснение недоступно: %s", exc)
                        st.warning("ИИ-объяснение недоступно: backend не отвечает.")
                    else:
                        if result.get("status") == "success" and result.get("explanation"):
                            st.info(result["explanation"])
            if status_key == "draft":
                if st.button(
                    "Отправить заявку",
                    key=f"app_submit_{application.get('id')}",
                    type="primary",
                    use_container_width=True,
                ):
                    if send_application(application):
                        st.success("Заявка отправлена на обработку.")
                        st.rerun()
                product = find_application_product(application)
                if product is not None:
                    with st.expander("Изменить сумму и срок", key=f"app_edit_{application.get('id')}"):
                        rate = float(product.get("rate", 18.9))
                        new_amount = st.number_input(
                            "Сумма заявки, ₽",
                            min_value=int(product.get("min_amount", 100_000)),
                            max_value=int(product.get("max_amount", 50_000_000)),
                            step=100_000,
                            value=int(application.get("amount")),
                            key=f"edit_amount_{application.get('id')}",
                        )
                        new_term = st.number_input(
                            "Срок заявки, месяцев",
                            min_value=int(product.get("min_term", 3)),
                            max_value=int(product.get("max_term", 60)),
                            value=int(application.get("term")),
                            key=f"edit_term_{application.get('id')}",
                        )
                        monthly, total, _ = payment_calculation(new_amount, rate, new_term)
                        st.caption(
                            f"Платёж ≈ {money(monthly)}/мес · всего к возврату {money(total)}"
                        )
                        if st.button(
                            "Сохранить изменения",
                            key=f"app_save_{application.get('id')}",
                            use_container_width=True,
                        ):
                            if update_draft(application, new_amount, new_term):
                                st.success("Изменения сохранены.")
                                st.rerun()
            elif status_key == "offer_ready":
                if details.get("decision") == "approved_with_changes" and details.get(
                    "suggested_amount"
                ):
                    term_hint = (
                        f" на {details['suggested_term_months']} мес"
                        if details.get("suggested_term_months")
                        else ""
                    )
                    st.info(
                        f"Предложение банка: сумма {money(details['suggested_amount'])}{term_hint}, "
                        f"платёж ≈ {money(details.get('suggested_monthly_payment'))}/мес."
                    )
                accept_col, decline_col = st.columns(2)
                with accept_col:
                    if st.button(
                        "Принять условия",
                        key=f"app_accept_{application.get('id')}",
                        type="primary",
                        use_container_width=True,
                    ):
                        if accept_offer(application):
                            st.rerun()
                with decline_col:
                    if st.button(
                        "Отклонить предложение",
                        key=f"app_decline_{application.get('id')}",
                        use_container_width=True,
                    ):
                        if decline_offer(application):
                            st.rerun()
            elif status_key == "accepted":
                if st.button(
                    "Подписать договор",
                    key=f"app_sign_{application.get('id')}",
                    type="primary",
                    use_container_width=True,
                ):
                    if sign_application(application):
                        st.success("Договор подписан. Выдача смоделирована.")
                        st.rerun()
            elif status_key == "needs_info":
                missing = ", ".join(details.get("missing_fields") or [])
                st.warning(
                    "Уточните данные о бизнесе в диалоге"
                    + (f": {missing}" if missing else "")
                    + " — затем отправьте заявку на повторную обработку."
                )
                if st.button(
                    "Отправить на повторную обработку",
                    key=f"app_rescore_{application.get('id')}",
                    use_container_width=True,
                ):
                    if rescore_application(application):
                        st.rerun()
            elif status_key == "rejected":
                # п. 2.7: альтернативные продукты при отказе
                alternatives = details.get("alternatives") or []
                if alternatives:
                    with st.expander(
                        "Альтернативные предложения",
                        key=f"app_alt_{application.get('id')}",
                    ):
                        st.caption(
                            "Запрошенный продукт не подошёл профилю бизнеса — "
                            "вот ближайшие альтернативы банка."
                        )
                        for alt in alternatives:
                            reduced = " · сумма снижена" if alt.get("amount_reduced") else ""
                            st.markdown(
                                f"**{alt.get('name')}** ({alt.get('rate'):g}% годовых{reduced}): "
                                f"{money(alt.get('amount'))} на {alt.get('term_months')} мес · "
                                f"платёж ≈ {money(alt.get('monthly_payment'))}/мес"
                            )
                        best = alternatives[0]
                        if not DEMO_MODE and st.button(
                            f"Оформить заявку: {best.get('name')}",
                            key=f"app_alt_create_{application.get('id')}",
                            use_container_width=True,
                        ):
                            if create_alternative_application(application, best):
                                st.success(
                                    "Заявка-альтернатива создана черновиком — "
                                    "проверьте параметры и отправьте её."
                                )
                                st.rerun()
            # История статусов — служебный блок сотрудников банка:
            # предпринимателю достаточно текущего статуса и объяснения решения
            if not DEMO_MODE and is_bank_user():
                render_application_history(application)


   
st.markdown(
    '<div style="padding:22px 0 8px;text-align:center;color:#9aa5b5;font-size:10px">ФинПомощник · MVP · Демонстрационный прототип на синтетических данных</div>',
    unsafe_allow_html=True,
)
