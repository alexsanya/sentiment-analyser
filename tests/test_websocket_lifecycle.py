"""
WebSocket Lifecycle Tests for WebSocketManager.

Tests the WebSocket lifecycle management functionality including:
- WebSocketApp creation with correct parameters
- Callback function assignment and identity verification
- Ping interval (30s) and ping timeout (20s) parameter validation
- current_ws reference lifecycle during connection flow
- current_ws cleanup on exceptions (finally block execution)
- WebSocket parameter order, types, and configuration validation
"""

import pytest
from unittest.mock import Mock, patch, call
import websocket
from src.core.websocket_manager import WebSocketManager


class TestWebSocketLifecycle:
    """Test WebSocket lifecycle management functionality."""
    
    def test_websocket_app_creation(self, mock_callbacks, mock_logger, mocker):
        """Test WebSocketApp is created with correct parameters."""
        # Mock WebSocketApp
        mock_ws_app = Mock(spec=websocket.WebSocketApp)
        mock_websocket_app = mocker.patch('src.core.websocket_manager.websocket.WebSocketApp', return_value=mock_ws_app)
        
        # Create manager
        manager = WebSocketManager(**mock_callbacks)
        
        # Set shutdown flag after first run_forever call to exit quickly
        def run_forever_side_effect(*args, **kwargs):
            manager.shutdown_requested = True
        
        mock_ws_app.run_forever.side_effect = run_forever_side_effect
        
        # Call connect
        url = "wss://test.example.com/websocket"
        headers = {"Authorization": "Bearer token123", "User-Agent": "TestAgent"}
        manager.connect(url, headers)
        
        # Verify WebSocketApp was created with exact parameters
        mock_websocket_app.assert_called_once_with(
            url,
            header=headers,
            on_message=mock_callbacks['on_message'],
            on_error=mock_callbacks['on_error'],
            on_close=mock_callbacks['on_close'],
            on_open=mock_callbacks['on_open']
        )
    
    def test_callback_assignment(self, mock_callbacks, mock_logger, mocker):
        """Test callback functions are properly assigned to WebSocket."""
        # Mock WebSocketApp
        mock_ws_app = Mock(spec=websocket.WebSocketApp)
        mock_websocket_app = mocker.patch('src.core.websocket_manager.websocket.WebSocketApp', return_value=mock_ws_app)
        
        # Create manager
        manager = WebSocketManager(**mock_callbacks)
        
        # Set shutdown flag after creation to exit quickly
        def run_forever_side_effect(*args, **kwargs):
            manager.shutdown_requested = True
        
        mock_ws_app.run_forever.side_effect = run_forever_side_effect
        
        # Call connect
        url = "wss://test.example.com/websocket"
        headers = {"x-api-key": "test-key"}
        manager.connect(url, headers)
        
        # Verify all callback functions were passed to WebSocketApp
        call_args = mock_websocket_app.call_args
        assert call_args is not None
        
        # Check keyword arguments contain all required callbacks
        kwargs = call_args.kwargs
        assert kwargs['on_message'] is mock_callbacks['on_message']
        assert kwargs['on_error'] is mock_callbacks['on_error'] 
        assert kwargs['on_close'] is mock_callbacks['on_close']
        assert kwargs['on_open'] is mock_callbacks['on_open']
        
        # Verify callbacks are the same objects (identity check)
        assert kwargs['on_message'] == manager.on_message
        assert kwargs['on_error'] == manager.on_error
        assert kwargs['on_close'] == manager.on_close
        assert kwargs['on_open'] == manager.on_open
    
    def test_ping_parameters(self, mock_callbacks, mock_logger, mocker):
        """Test ping_interval and ping_timeout are set correctly."""
        # Mock WebSocketApp
        mock_ws_app = Mock(spec=websocket.WebSocketApp)
        mock_websocket_app = mocker.patch('src.core.websocket_manager.websocket.WebSocketApp', return_value=mock_ws_app)
        
        # Create manager
        manager = WebSocketManager(**mock_callbacks)
        
        # Set shutdown flag after first run_forever call
        def run_forever_side_effect(*args, **kwargs):
            manager.shutdown_requested = True
        
        mock_ws_app.run_forever.side_effect = run_forever_side_effect
        
        # Call connect
        url = "wss://test.example.com/websocket"
        headers = {"x-api-key": "test-key"}
        manager.connect(url, headers)
        
        # Verify run_forever was called with correct ping parameters
        mock_ws_app.run_forever.assert_called_once_with(ping_interval=30, ping_timeout=20)
    
    def test_current_ws_lifecycle_management(self, mock_callbacks, mock_logger, mocker):
        """Test current_ws reference lifecycle during connection."""
        # Mock WebSocketApp
        mock_ws_app = Mock(spec=websocket.WebSocketApp)
        mock_websocket_app = mocker.patch('src.core.websocket_manager.websocket.WebSocketApp', return_value=mock_ws_app)
        
        # Create manager
        manager = WebSocketManager(**mock_callbacks)
        
        # Verify initial state
        assert manager.current_ws is None
        
        # Track current_ws state changes
        ws_states = []
        
        def run_forever_side_effect(*args, **kwargs):
            # Capture current_ws state during run_forever execution
            ws_states.append(('during_run', manager.current_ws))
            manager.shutdown_requested = True
        
        mock_ws_app.run_forever.side_effect = run_forever_side_effect
        
        # Call connect
        url = "wss://test.example.com/websocket"
        headers = {"x-api-key": "test-key"}
        manager.connect(url, headers)
        
        # Verify current_ws lifecycle
        assert len(ws_states) == 1
        assert ws_states[0][0] == 'during_run'
        assert ws_states[0][1] is mock_ws_app  # current_ws was set to the WebSocket instance
        
        # Verify current_ws was cleared after connection ended (finally block)
        assert manager.current_ws is None
    
    def test_current_ws_cleared_on_exception(self, mock_callbacks, mock_logger, mocker):
        """Test current_ws is cleared even when run_forever raises exception."""
        # Mock WebSocketApp to raise exception
        mock_ws_app = Mock(spec=websocket.WebSocketApp)
        mock_ws_app.run_forever.side_effect = Exception("Test connection error")
        mock_websocket_app = mocker.patch('src.core.websocket_manager.websocket.WebSocketApp', return_value=mock_ws_app)
        
        # Mock time.sleep to set shutdown flag and avoid infinite retry loop
        mock_sleep = mocker.patch('src.core.websocket_manager.time.sleep')
        
        def sleep_side_effect(duration):
            manager.shutdown_requested = True
        
        mock_sleep.side_effect = sleep_side_effect
        
        # Create manager
        manager = WebSocketManager(**mock_callbacks)
        
        # Verify initial state
        assert manager.current_ws is None
        
        # Call connect (will raise exception but should still clear current_ws)
        url = "wss://test.example.com/websocket"
        headers = {"x-api-key": "test-key"}
        manager.connect(url, headers)
        
        # Verify current_ws was cleared despite exception (finally block executed)
        assert manager.current_ws is None
    
    def test_websocket_app_creation_parameters_order(self, mock_callbacks, mock_logger, mocker):
        """Test WebSocketApp creation with specific parameter order and types."""
        # Mock WebSocketApp
        mock_ws_app = Mock(spec=websocket.WebSocketApp)
        mock_websocket_app = mocker.patch('src.core.websocket_manager.websocket.WebSocketApp', return_value=mock_ws_app)
        
        # Create manager
        manager = WebSocketManager(**mock_callbacks)
        
        # Set shutdown flag after creation
        def run_forever_side_effect(*args, **kwargs):
            manager.shutdown_requested = True
        
        mock_ws_app.run_forever.side_effect = run_forever_side_effect
        
        # Call connect with specific parameters
        url = "wss://api.example.com/stream"
        headers = {
            "Authorization": "Bearer abc123",
            "Content-Type": "application/json",
            "User-Agent": "NewsTrader/1.0"
        }
        manager.connect(url, headers)
        
        # Verify call structure and parameter order
        call_args = mock_websocket_app.call_args
        assert call_args is not None
        
        # Check positional argument (URL)
        assert call_args.args[0] == url
        
        # Check keyword arguments
        kwargs = call_args.kwargs
        assert kwargs['header'] == headers  # Note: 'header' not 'headers' 
        assert 'on_message' in kwargs
        assert 'on_error' in kwargs
        assert 'on_close' in kwargs
        assert 'on_open' in kwargs
        
        # Verify run_forever parameters are correct types
        run_forever_call = mock_ws_app.run_forever.call_args
        assert run_forever_call.kwargs['ping_interval'] == 30
        assert run_forever_call.kwargs['ping_timeout'] == 20
        assert isinstance(run_forever_call.kwargs['ping_interval'], int)
        assert isinstance(run_forever_call.kwargs['ping_timeout'], int)