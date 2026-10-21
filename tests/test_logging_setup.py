"""Тесты настройки файлового логирования backend (data/logs/backend.log)."""

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

import pytest

from main import setup_logging


@pytest.fixture(autouse=True)
def restore_default_logging():
    """После каждого теста вернуть файловый обработчик на data/logs/backend.log."""
    yield
    setup_logging()


class TestSetupLogging:
    def test_creates_log_dir_and_file(self, tmp_path):
        log_file = setup_logging(tmp_path)
        assert log_file == tmp_path / "backend.log"
        assert log_file.exists()

    def test_records_go_to_log_file(self, tmp_path):
        log_file = setup_logging(tmp_path)
        logging.getLogger("test.logging").info("запись для проверки файла")
        for handler in logging.getLogger().handlers:
            handler.flush()
        assert "запись для проверки файла" in log_file.read_text(encoding="utf-8")

    def test_replaces_previous_file_handler(self, tmp_path):
        setup_logging(tmp_path)
        file_handlers = [
            h for h in logging.getLogger().handlers
            if isinstance(h, RotatingFileHandler)
        ]
        assert len(file_handlers) == 1
        assert Path(file_handlers[0].baseFilename) == tmp_path / "backend.log"
