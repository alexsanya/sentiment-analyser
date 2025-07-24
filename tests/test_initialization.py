"""
Test cases for WebSocketManager initialization functionality.
"""

import pytest
from unittest.mock import Mock
from src.core.websocket_manager import WebSocketManager


class TestWebSocketManagerInitialization:
    """Test cases for WebSocketManager initialization."""
    
    def test_websocket_manager_init(self, mock_callbacks, mock_logger):
        """Test WebSocketManager initialization with callback functions."""
        mock_logger_instance = Mock()
        mock_logger.return_value = mock_logger_instance
        
        manager = WebSocketManager(
            on_message=mock_callbacks['on_message'],
            on_error=mock_callbacks['on_error'],
            on_close=mock_callbacks['on_close'],
            on_open=mock_callbacks['on_open']
        )
        
        # Verify callbacks are stored correctly
        assert manager.on_message == mock_callbacks['on_message']
        assert manager.on_error == mock_callbacks['on_error']
        assert manager.on_close == mock_callbacks['on_close']
        assert manager.on_open == mock_callbacks['on_open']
        
        # Verify logger is set up with correct class name
        mock_logger.assert_called_once_with('WebSocketManager')
        assert manager.logger == mock_logger_instance
    
    def test_initial_state(self, mock_callbacks, mocker):
        """Test initial state values are set correctly."""
        mocker.patch('src.core.websocket_manager.get_logger')
        
        manager = WebSocketManager(
            on_message=mock_callbacks['on_message'],
            on_error=mock_callbacks['on_error'],
            on_close=mock_callbacks['on_close'],
            on_open=mock_callbacks['on_open']
        )
        
        # Verify initial state
        assert manager.shutdown_requested is False
        assert manager.current_ws is None
    
    def test_callback_function_types(self, mock_callbacks, mocker):
        """Test that callback functions are callable."""
        mocker.patch('src.core.websocket_manager.get_logger')
        
        manager = WebSocketManager(
            on_message=mock_callbacks['on_message'],
            on_error=mock_callbacks['on_error'],
            on_close=mock_callbacks['on_close'],
            on_open=mock_callbacks['on_open']
        )
        
        # Verify all callbacks are callable
        assert callable(manager.on_message)
        assert callable(manager.on_error)
        assert callable(manager.on_close)
        assert callable(manager.on_open)
    
    def test_initialization_with_real_functions(self, mocker):
        """Test initialization with actual function objects instead of mocks."""
        def dummy_on_message(ws, message):
            pass
            
        def dummy_on_error(ws, error):
            pass
            
        def dummy_on_close(ws, close_code, close_msg):
            pass
            
        def dummy_on_open(ws):
            pass
        
        mocker.patch('src.core.websocket_manager.get_logger')
        
        manager = WebSocketManager(
            on_message=dummy_on_message,
            on_error=dummy_on_error,
            on_close=dummy_on_close,
            on_open=dummy_on_open
        )
        
        # Verify functions are stored correctly
        assert manager.on_message == dummy_on_message
        assert manager.on_error == dummy_on_error
        assert manager.on_close == dummy_on_close
        assert manager.on_open == dummy_on_open
        
        # Verify initial state
        assert manager.shutdown_requested is False
        assert manager.current_ws is None