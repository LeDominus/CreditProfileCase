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


def test_no_hero_autocreates_conversation():
    at = make_app()
    assert at.session_state["active_conversation_id"] is not None
    assert len(at.session_state["messages"]) == 1
    assert at.session_state["messages"][0]["role"] == "assistant"


def test_chips_removed_but_recommend_button_kept():
    at = make_app()
    chip_keys = [b.key for b in at.button if b.key and b.key.startswith("chip_")]
    assert chip_keys == []
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

    # подбор продуктов
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
