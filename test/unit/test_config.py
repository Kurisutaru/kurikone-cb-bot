import os
from unittest.mock import MagicMock, patch
import pytest
from config import check_env_vars, REQUIRED_ENV_VARS
from logger import KuriLogger
from dependency_injector import providers


@pytest.fixture
def mock_logger(mock_container):
    logger = MagicMock(spec=KuriLogger)
    mock_container.logger.override(providers.Object(logger))
    return logger


def test_check_env_vars_missing(mock_container, mock_logger):
    with patch.dict(os.environ, {}, clear=True):
        with pytest.raises(SystemExit):
            check_env_vars()

    expected_calls = [
        f"❌ Missing Environment Variable: {var}" for var in REQUIRED_ENV_VARS
    ]
    actual_calls = [call[0][0] for call in mock_logger.critical.call_args_list]
    assert len(actual_calls) == len(
        REQUIRED_ENV_VARS
    ), f"Expected {len(REQUIRED_ENV_VARS)} log calls, got {len(actual_calls)}"
    for expected in expected_calls:
        assert expected in actual_calls, f"Expected log message '{expected}' not found"


def test_check_env_vars_di_wiring(mock_container, mock_logger):
    with patch.dict(os.environ, {}, clear=True):
        assert "DISCORD_TOKEN" not in os.environ, "DISCORD_TOKEN still present"
        with pytest.raises(SystemExit):
            check_env_vars()

    assert mock_logger.critical.called, "Injected logger was not used"


@patch.dict(os.environ, {})
@patch("config.REQUIRED_ENV_VARS", {})
def test_check_env_vars_empty_required(mock_container):
    mock_logger = MagicMock(spec=KuriLogger)
    mock_container.logger.override(providers.Object(mock_logger))

    check_env_vars()

    mock_logger.critical.assert_not_called()


def test_check_env_vars_all_set(mock_container, mock_logger):
    with patch.dict(os.environ, {"DISCORD_TOKEN": "dummy_token"}, clear=True):
        check_env_vars()
    mock_logger.critical.assert_not_called()
