import logging
import os
import re
import time
import uuid
from dotenv import load_dotenv
import requests
import streamlit as st
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP

load_dotenv()

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

API_BASE_URL = "http://127.0.0.1:5555"
DEMO_MODE = os.getenv("DEMO_MODE", "true").lower() == "true"

logger = logging.getLogger("frontend")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)

STATUS_LABELS = {
    "draft": ("Черновик", "⚪"),
    "demo_received": ("Заявка получена · демо", "🔵"),
    "demo_review": ("Демо-проверка", "🟠"),
    "submitted": ("Отправлена · демо", "🔵"),
    "error": ("Ошибка", "🔴"),
}


def money(value):
    try:
        amount = Decimal(str(value)).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
        return f"{amount:,.0f}".replace(",", " ") + " ₽"
    except Exception:
        return "—"


def payment_calculation(principal, annual_rate, months):
    principal = Decimal(str(principal))
    months = int(months)
    rate = Decimal(str(annual_rate)) / Decimal("1200")
    if months <= 0:
        return Decimal("0"), Decimal("0"), Decimal("0")
    if rate == 0:
        monthly = principal / months
    else:
        factor = (Decimal("1") + rate) ** months
        monthly = principal * rate * factor / (factor - Decimal("1"))
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
    try:
        response = requests.request(
            method,
            f"{API_BASE_URL}{path}",
            timeout=timeout,
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
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": "Здравствуйте! Я ИИ-ассистент по подбору кредитных продуктов для малого и среднего бизнеса. Расскажите, для чего вам нужно финансирование, какая сумма требуется и на какой срок.",
        }
    ]
    st.session_state.recommendations = None
    st.session_state.show_confirm = False
    st.session_state.selection_unlocked = False
    st.session_state.awaiting_reply = False


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


def submit_application(product, amount, term):
    monthly, total, overpayment = payment_calculation(amount, product["rate"], term)
    # Эндпоинт заявок на backend пока не реализован (в main.py есть
    # /api/profile/{id}/payment, но нет /api/applications) — заявка
    # фиксируется локально, в session_state.
    application_id = str(uuid.uuid4())[:8].upper()
    if not DEMO_MODE:
        logger.warning(
            "POST /api/applications не реализован на backend — заявка №%s сохранена локально",
            application_id,
        )
        status = "submitted"
    else:
        status = "demo_received"
    application = {
        "id": application_id,
        "product_name": product["name"],
        "product_id": product["id"],
        "amount": amount,
        "term": term,
        "monthly_payment": float(monthly),
        "total_repayment": float(total),
        "overpayment": float(overpayment),
        "status": status,
        "created_at": datetime.now().strftime("%d.%m.%Y %H:%M"),
    }
    st.session_state.applications.insert(0, application)
    st.session_state.show_confirm = False
    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": f"Заявка № {application_id} создана в демонстрационном режиме. Текущий статус: «{STATUS_LABELS.get(status, ('Получена', '🔵'))[0]}». Это не является одобрением банка.",
        }
    )
    return True


init_state()

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
            st.session_state.active_conversation_id = conversation["id"]
            st.rerun()
    # Заявки перенесены в expander «История заявок» правой панели (упрощение UI)
    if DEMO_MODE:
        st.caption("● Демо-режим · синтетические данные")
    else:
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
                reply_text = "Спасибо, я принял описание. Расскажите о сумме, цели и сроке — я зафиксирую параметры в профиле. Затем нажмите «Подобрать продукты»."
            else:
                result = api_send_message(
                    st.session_state.active_conversation_id,
                    st.session_state.messages[-1]["content"],
                    profile_id=st.session_state.backend_profile_id,
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
            st.session_state.messages.append({"role": "assistant", "content": reply_text})
        except requests.RequestException as exc:
            st.session_state.messages.append(
                {"role": "assistant", "content": f"Не удалось связаться с сервером: {exc}"}
            )
        st.session_state.awaiting_reply = False
        st.rerun()
    if st.button("✦  Подобрать продукты", key="chat_recommend", use_container_width=True, type="primary"):
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
            '<div class="panel-sub">Опишите потребность бизнеса в чате и нажмите «Подобрать продукты» — здесь появятся подходящие варианты.</div></div>',
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


   
st.markdown(
    '<div style="padding:22px 0 8px;text-align:center;color:#9aa5b5;font-size:10px">ФинПомощник · MVP · Демонстрационный прототип на синтетических данных</div>',
    unsafe_allow_html=True,
)
