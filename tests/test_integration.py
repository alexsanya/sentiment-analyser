"""
Integration Tests for WebSocketManager.

Tests complete WebSocketManager workflows including:
- Complete connection lifecycle from initialization to shutdown with state tracking
- Signal-to-shutdown sequence testing with WebSocket close operations and cleanup
- Manager state transitions during full workflow execution
- Comprehensive logging validation throughout integration flows
- Resource cleanup verification after complete operations
"""

import pytest
from unittest.mock import Mock, patch, call
import websocket
from websocket_manager import WebSocketManager


class TestIntegration:
    """Integration tests for complete WebSocketManager workflows."""
    
    def test_complete_lifecycle(self, mock_callbacks, mock_logger, mocker):
        """Test complete connection lifecycle with mocked WebSocket."""
        # Mock WebSocketApp for complete lifecycle test
        mock_ws_app = Mock(spec=websocket.WebSocketApp)
        mock_websocket_app = mocker.patch('websocket_manager.websocket.WebSocketApp', return_value=mock_ws_app)
        
        # Mock time.sleep for controlled timing
        mock_sleep = mocker.patch('websocket_manager.time.sleep')
        
        # Create manager
        manager = WebSocketManager(**mock_callbacks)
        
        # Verify initial state
        assert manager.shutdown_requested is False
        assert manager.current_ws is None
        assert manager.on_message is mock_callbacks['on_message']
        assert manager.on_error is mock_callbacks['on_error']
        assert manager.on_close is mock_callbacks['on_close']
        assert manager.on_open is mock_callbacks['on_open']
        
        # Track lifecycle phases
        lifecycle_phases = []
        
        def run_forever_side_effect(*args, **kwargs):
            # Record that connection was established
            lifecycle_phases.append('connection_established')
            # Verify current_ws is set during connection
            lifecycle_phases.append(f'current_ws_during_run: {manager.current_ws is mock_ws_app}')
            # Simulate some connection activity then graceful shutdown
            manager.shutdown_requested = True
            lifecycle_phases.append('shutdown_requested')
        
        mock_ws_app.run_forever.side_effect = run_forever_side_effect
        
        # Start connection
        url = "wss://api.twitterapi.io/twitter/tweet/websocket"
        headers = {"x-api-key": "test-key-12345"}
        
        lifecycle_phases.append('starting_connect')
        manager.connect(url, headers)
        lifecycle_phases.append('connect_completed')
        
        # Verify complete lifecycle execution
        expected_phases = [
            'starting_connect',
            'connection_established',
            'current_ws_during_run: True',
            'shutdown_requested',
            'connect_completed'
        ]
        assert lifecycle_phases == expected_phases
        
        # Verify WebSocketApp was created with correct parameters
        mock_websocket_app.assert_called_once_with(
            url,
            header=headers,
            on_message=mock_callbacks['on_message'],
            on_error=mock_callbacks['on_error'],
            on_close=mock_callbacks['on_close'],
            on_open=mock_callbacks['on_open']
        )
        
        # Verify WebSocket connection was established
        mock_ws_app.run_forever.assert_called_once_with(ping_interval=30, ping_timeout=20)
        
        # Verify final state after lifecycle completion
        assert manager.shutdown_requested is True
        assert manager.current_ws is None  # Cleared in finally block
        
        # Verify no retry attempts were made (successful connection)
        mock_sleep.assert_not_called()
        
        # Verify connection loop ended message
        mock_logger.return_value.info.assert_any_call("WebSocket connection loop ended")
    
    def test_shutdown_sequence(self, mock_callbacks, mock_logger, mocker):
        """Test complete shutdown sequence from signal to connection termination."""
        # Mock WebSocketApp
        mock_ws_app = Mock(spec=websocket.WebSocketApp)
        mock_websocket_app = mocker.patch('websocket_manager.websocket.WebSocketApp', return_value=mock_ws_app)
        
        # Create manager
        manager = WebSocketManager(**mock_callbacks)
        
        # Track shutdown sequence phases
        shutdown_phases = []
        
        def run_forever_side_effect(*args, **kwargs):
            shutdown_phases.append('connection_active')
            # Simulate connection being active when signal arrives
            # We'll trigger signal handler manually during this "active" phase
            shutdown_phases.append('signal_received')
            
            # Simulate signal handler execution
            import types
            mock_frame = Mock(spec=types.FrameType)
            manager._signal_handler(15, mock_frame)  # SIGTERM
            
            shutdown_phases.append('signal_handler_completed')
            
            # Connection should continue to check shutdown flag
            # Since shutdown_requested is now True, connection should terminate
            shutdown_phases.append('checking_shutdown_flag')
            assert manager.shutdown_requested is True
            shutdown_phases.append('shutdown_flag_detected')
        
        mock_ws_app.run_forever.side_effect = run_forever_side_effect
        
        # Mock WebSocket close to track if it's called
        mock_ws_app.close = Mock()
        
        # Start connection
        url = "wss://test.example.com/websocket"
        headers = {"Authorization": "Bearer token123"}
        
        shutdown_phases.append('initiating_connection')
        manager.connect(url, headers)
        shutdown_phases.append('connection_method_completed')
        
        # Verify complete shutdown sequence
        expected_phases = [
            'initiating_connection',
            'connection_active',
            'signal_received',
            'signal_handler_completed',
            'checking_shutdown_flag',
            'shutdown_flag_detected',
            'connection_method_completed'
        ]
        assert shutdown_phases == expected_phases
        
        # Verify signal handler actions were executed
        assert manager.shutdown_requested is True
        
        # Verify WebSocket close was called during signal handler
        mock_ws_app.close.assert_called_once()
        
        # Verify proper logging during shutdown sequence
        mock_logger.return_value.info.assert_any_call("Graceful shutdown initiated")
        mock_logger.return_value.info.assert_any_call("WebSocket connection loop ended")
        
        # Verify WebSocketApp creation occurred
        mock_websocket_app.assert_called_once_with(
            url,
            header=headers,
            on_message=mock_callbacks['on_message'],
            on_error=mock_callbacks['on_error'],
            on_close=mock_callbacks['on_close'],
            on_open=mock_callbacks['on_open']
        )
        
        # Verify final cleanup state
        assert manager.current_ws is None