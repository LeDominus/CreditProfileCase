"""E2E-тест UI (Streamlit AppTest): упрощённый интерфейс «Минимум».

Проверяется: авто-создание диалога (нет hero-экрана), отсутствие чипов,
панель «Профиль бизнеса» убрана из UI, выбор продукта — в правой панели
и доступен только после подбора, полный сценарий подбор -> выбор ->
подтверждение заявки.
"""

from pathlib import Path
import os

from streamlit.testing.v1 import AppTest

APP_PATH = str(Path(__file__).resolve().parent.parent / "frontend" / "app.py")
os.environ["DEMO_MODE"] = "true"


def make_app():
    at = AppTest.from_file(APP_PATH, default_timeout=30)
    at.run()
    assert not at.exception, [str(e.value) for e in at.exception]
    return at


def fill_required_profile(at):
    """Ассистент собрал обязательные параметры бизнеса (имитация извлечения полей)."""
    at.session_state["profile"].update(
        {
            "business_age_months": 36,
            "monthly_revenue": 800_000,
            "monthly_profit": 150_000,
        }
    )
    at.run()
    assert not at.exception


def open_products_without_dialog(at):
    """Панель продуктов напрямую, без диалога (сценарии с неполным профилем)."""
    at.session_state["recommendations"] = [
        {
            "id": 1,
            "name": "Оборотный капитал",
            "rate": 18.9,
            "min_amount": 300_000,
            "max_amount": 5_000_000,
            "min_term": 6,
            "max_term": 36,
        }
    ]
    at.session_state["selected_product_id"] = 1
    at.session_state["selection_unlocked"] = True
    at.run()
    assert not at.exception


def test_no_hero_autocreates_conversation():
    at = make_app()
    assert at.session_state["active_conversation_id"] is not None
    assert len(at.session_state["messages"]) == 1
    assert at.session_state["messages"][0]["role"] == "assistant"


def test_recommend_button_gated_until_profile_complete():
    at = make_app()
    chip_keys = [b.key for b in at.button if b.key and b.key.startswith("chip_")]
    assert chip_keys == []
    # пока ассистент не собрал обязательные данные — кнопки подбора нет
    assert not any(b.key == "chat_recommend" for b in at.button)
    fill_required_profile(at)
    assert any(b.key == "chat_recommend" for b in at.button)


def test_profile_panel_removed():
    at = make_app()
    labels = [e.label for e in at.expander]
    # панель «Профиль бизнеса» убрана из UI: профиль заполняется в диалоге
    assert "Все параметры профиля" not in labels
    assert "Кредитные продукты" not in labels
    assert "История заявок" not in labels


def test_product_selection_gated_until_recommend():
    at = make_app()
    # до подбора кнопок выбора продукта быть не должно
    choose_keys = [
        button.key for button in at.button
        if button.key and button.key.startswith("chat_choose_")
    ]
    assert choose_keys == [], "выбор продукта должен быть закрыт до подбора"
    fill_required_profile(at)
    at.button(key="chat_recommend").click()
    at.run()
    assert not at.exception
    choose_keys = [
        button.key for button in at.button
        if button.key and button.key.startswith("chat_choose_")
    ]
    assert choose_keys, "кнопки выбора продуктов должны появиться после подбора"


def test_full_flow_recommend_choose_confirm():
    at = make_app()

    # ассистент собрал обязательные данные — подбор стал доступен
    fill_required_profile(at)
    at.button(key="chat_recommend").click()
    at.run()
    assert not at.exception
    recs = at.session_state["recommendations"]
    assert recs, "рекомендации должны быть сгенерированы"
    assert at.session_state["selected_product_id"] == recs[0]["id"]

    # выбор продукта в чате
    at.button(key=f"chat_choose_{recs[0]['id']}").click()
    at.run()
    assert not at.exception
    assert at.session_state["show_confirm"] is True

    # подтверждение заявки: чекбокс + кнопка «Подтвердить и отправить»
    at.checkbox[0].check()
    at.run()
    assert not at.exception
    confirm_buttons = [b for b in at.button if "Подтвердить и отправить" in (b.label or "")]
    assert confirm_buttons, "кнопка подтверждения заявки должна рендериться"
    confirm_buttons[0].click()
    at.run()
    assert not at.exception
    assert len(at.session_state["applications"]) == 1
    assert at.session_state["show_confirm"] is False


def _submit_default_application(at, fill_profile=True):
    """Подбор -> выбор продукта -> подтверждение отправки заявки.

    fill_profile=False — сценарии с неполным профилем (needs_info):
    панель продуктов открывается напрямую, без кнопки подбора.
    """
    if fill_profile:
        fill_required_profile(at)
        at.button(key="chat_recommend").click()
        at.run()
        assert not at.exception
    else:
        open_products_without_dialog(at)
    recs = at.session_state["recommendations"]
    at.button(key=f"chat_choose_{recs[0]['id']}").click()
    at.run()
    at.checkbox[0].check()
    at.run()
    confirm_buttons = [b for b in at.button if "Подтвердить и отправить" in (b.label or "")]
    confirm_buttons[0].click()
    at.run()
    assert not at.exception
    return at.session_state["applications"][0]


def _send_draft(at):
    """Отправка черновика кнопкой «Отправить заявку» (демо: локальный скоринг)."""
    submit = [b for b in at.button if b.key and b.key.startswith("app_submit_")]
    assert submit, "кнопка «Отправить заявку» должна рендериться для черновика"
    submit[0].click()
    at.run()
    assert not at.exception
    return at.session_state["applications"][0]


def test_full_lifecycle_submit_accept_sign():
    """Черновик -> отправка -> предложение -> принятие условий -> подписание -> выдача."""
    at = make_app()

    application = _submit_default_application(at)
    assert application["status"] == "draft"
    assert application["score"] is None
    assert any(e.label == "Изменить сумму и срок" for e in at.expander)

    # отправка черновика -> конвейер (демо: локальный скоринг) -> предложение
    application = _send_draft(at)
    assert application["status"] == "offer_ready"
    assert application["score"] >= 70
    assert application["decision_details"]["explanation"]

    # принятие условий предложения
    accept = [b for b in at.button if b.key and b.key.startswith("app_accept_")]
    assert accept, "кнопка «Принять условия» должна рендериться"
    accept[0].click()
    at.run()
    assert not at.exception
    assert at.session_state["applications"][0]["status"] == "accepted"

    # подписание договора (ЭП моделируется кнопкой) -> выдача
    sign = [b for b in at.button if b.key and b.key.startswith("app_sign_")]
    assert sign, "кнопка «Подписать договор» должна рендериться"
    sign[0].click()
    at.run()
    assert not at.exception
    assert at.session_state["applications"][0]["status"] == "issued"


def test_decline_offer():
    """Предложение -> отказ клиента -> client_declined (терминальный статус)."""
    at = make_app()
    _submit_default_application(at)
    _send_draft(at)

    decline = [b for b in at.button if b.key and b.key.startswith("app_decline_")]
    assert decline, "кнопка «Отклонить предложение» должна рендериться"
    decline[0].click()
    at.run()
    assert not at.exception
    assert at.session_state["applications"][0]["status"] == "client_declined"


def test_needs_info_then_rescore():
    """Профиль без финансовых данных -> needs_info -> уточнение -> повторная обработка."""
    at = make_app()

    # профиль без финансовых данных: подбор через диалог недоступен
    application = _submit_default_application(at, fill_profile=False)
    assert application["status"] == "draft"
    application = _send_draft(at)
    assert application["status"] == "needs_info"
    assert "monthly_revenue" in application["decision_details"]["missing_fields"]

    # клиент уточняет данные в профиле и отправляет заявку на повторную обработку
    at.session_state["profile"].update(
        {
            "business_age_months": 36,
            "monthly_revenue": 800_000,
            "monthly_profit": 150_000,
        }
    )
    rescore = [b for b in at.button if b.key and b.key.startswith("app_rescore_")]
    assert rescore, "кнопка повторной обработки должна рендериться"
    rescore[0].click()
    at.run()
    assert not at.exception
    assert at.session_state["applications"][0]["status"] == "offer_ready"
