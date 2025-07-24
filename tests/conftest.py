"""
Shared pytest fixtures for WebSocketManager tests.
"""

import pytest
from unittest.mock import Mock


@pytest.fixture
def mock_callbacks():
    """Create mock callback functions for WebSocketManager initialization."""
    return {
        'on_message': Mock(),
        'on_error': Mock(),
        'on_close': Mock(),
        'on_open': Mock()
    }


@pytest.fixture
def mock_logger(mocker):
    """Mock the get_logger function."""
    return mocker.patch('src.core.websocket_manager.get_logger')