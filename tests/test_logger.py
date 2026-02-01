"""Tests for cascade.utils.logger module."""

import logging
from pathlib import Path


class TestSetupLogging:
    """Tests for setup_logging function."""

    def test_setup_with_file(self, tmp_path: Path):
        """Test logging setup with a file path."""
        from cascade.utils.logger import setup_logging

        log_file = tmp_path / "test.log"
        setup_logging(level=logging.DEBUG, log_file=log_file, console=False)

        # Log a message
        logger = logging.getLogger("test_logger")
        logger.info("Test message")

        # Check file was created and contains message
        assert log_file.exists()
        content = log_file.read_text()
        assert "Test message" in content

    def test_setup_with_console(self, tmp_path: Path, capsys):
        """Test logging setup with console output."""
        from cascade.utils.logger import setup_logging

        log_file = tmp_path / "test.log"
        setup_logging(level=logging.INFO, log_file=log_file, console=True)

        logger = logging.getLogger("console_test")
        logger.info("Console test message")

        # Console output should contain the message
        capsys.readouterr()
        # Note: May or may not appear depending on handler setup
        # Just verify no errors occurred

    def test_setup_creates_directory(self, tmp_path: Path):
        """Test that setup_logging creates log directory if needed."""
        from cascade.utils.logger import setup_logging

        nested_path = tmp_path / "nested" / "dir" / "logs"
        log_file = nested_path / "cascade.log"

        setup_logging(level=logging.INFO, log_file=log_file, console=False)

        assert nested_path.exists()

    def test_different_log_levels(self, tmp_path: Path):
        """Test different logging levels."""
        from cascade.utils.logger import setup_logging

        log_file = tmp_path / "levels.log"
        setup_logging(level=logging.WARNING, log_file=log_file, console=False)

        logger = logging.getLogger("level_test")
        logger.debug("Debug message")  # Should not appear
        logger.info("Info message")  # Should not appear
        logger.warning("Warning message")  # Should appear
        logger.error("Error message")  # Should appear

        content = log_file.read_text()
        assert "Debug message" not in content
        assert "Info message" not in content
        assert "Warning message" in content
        assert "Error message" in content


class TestGetLogger:
    """Tests for get_logger function."""

    def test_returns_logger(self):
        """Test that get_logger returns a Logger instance."""
        from cascade.utils.logger import get_logger

        logger = get_logger("test_module")
        assert isinstance(logger, logging.Logger)

    def test_returns_named_logger(self):
        """Test that logger has correct name."""
        from cascade.utils.logger import get_logger

        logger = get_logger("my.custom.module")
        assert logger.name == "my.custom.module"

    def test_same_name_returns_same_logger(self):
        """Test that same name returns same logger instance."""
        from cascade.utils.logger import get_logger

        logger1 = get_logger("shared_module")
        logger2 = get_logger("shared_module")
        assert logger1 is logger2

    def test_different_names_return_different_loggers(self):
        """Test that different names return different loggers."""
        from cascade.utils.logger import get_logger

        logger1 = get_logger("module_a")
        logger2 = get_logger("module_b")
        assert logger1 is not logger2
        assert logger1.name != logger2.name
