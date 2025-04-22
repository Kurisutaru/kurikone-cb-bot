import os
from unittest.mock import patch, MagicMock

import pytest
from dependency_injector import providers

from logger import KuriLogger


@patch.dict(os.environ, {}, clear=True)
def test_check_env_vars_all_set(mock_container):
    mock_logger = MagicMock(spec=KuriLogger)
    mock_container.logger.override(providers.Object(mock_logger))
    with pytest.raises(SystemExit):
        from config import check_env_vars

        check_env_vars()
    mock_logger.critical.assert_called_once()
