"""
Test cases for WebSocketManager signal handler functionality.
"""

import pytest
import types
from unittest.mock import Mock
from websocket_manager import WebSocketManager


class TestWebSocketManagerSignalHandler:
    """Test cases for WebSocketManager signal handler functionality."""
    
    def test_signal_handler_sets_shutdown_flag(self, mock_callbacks, mock_logger):
        """Test signal handler sets shutdown_requested to True."""
        mock_logger_instance = Mock()
        mock_logger.return_value = mock_logger_instance
        
        manager = WebSocketManager(
            on_message=mock_callbacks['on_message'],
            on_error=mock_callbacks['on_error'],
            on_close=mock_callbacks['on_close'],
            on_open=mock_callbacks['on_open']
        )
        
        # Initially shutdown_requested should be False
        assert manager.shutdown_requested is False
        
        # Call signal handler with mock frame
        mock_frame = Mock(spec=types.FrameType)
        manager._signal_handler(2, mock_frame)  # SIGINT = 2
        
        # Verify shutdown flag is set
        assert manager.shutdown_requested is True
        
        # Verify logging
        mock_logger_instance.info.assert_any_call("Shutdown signal received", signal=2)
        mock_logger_instance.info.assert_any_call("Graceful shutdown initiated")
    
    def test_signal_handler_closes_active_websocket(self, mock_callbacks, mock_logger):
        """Test signal handler closes current WebSocket connection."""
        mock_logger_instance = Mock()
        mock_logger.return_value = mock_logger_instance
        
        manager = WebSocketManager(
            on_message=mock_callbacks['on_message'],
            on_error=mock_callbacks['on_error'],
            on_close=mock_callbacks['on_close'],
            on_open=mock_callbacks['on_open']
        )
        
        # Set up mock WebSocket
        mock_websocket = Mock()
        manager.current_ws = mock_websocket
        
        # Call signal handler
        mock_frame = Mock(spec=types.FrameType)
        manager._signal_handler(2, mock_frame)
        
        # Verify WebSocket close was called
        mock_websocket.close.assert_called_once()
        
        # Verify shutdown flag is set
        assert manager.shutdown_requested is True
        
        # Verify logging
        mock_logger_instance.info.assert_any_call("Closing WebSocket connection...")
        mock_logger_instance.info.assert_any_call("Graceful shutdown initiated")
    
    def test_signal_handler_no_active_websocket(self, mock_callbacks, mock_logger):
        """Test signal handler when no active WebSocket exists."""
        mock_logger_instance = Mock()
        mock_logger.return_value = mock_logger_instance
        
        manager = WebSocketManager(
            on_message=mock_callbacks['on_message'],
            on_error=mock_callbacks['on_error'],
            on_close=mock_callbacks['on_close'],
            on_open=mock_callbacks['on_open']
        )
        
        # Ensure no current WebSocket
        assert manager.current_ws is None
        
        # Call signal handler
        mock_frame = Mock(spec=types.FrameType)
        manager._signal_handler(2, mock_frame)
        
        # Verify shutdown flag is set
        assert manager.shutdown_requested is True
        
        # Verify logging (should not log WebSocket closing message)
        mock_logger_instance.info.assert_any_call("Shutdown signal received", signal=2)
        mock_logger_instance.info.assert_any_call("Graceful shutdown initiated")
        
        # Verify WebSocket closing message was NOT logged
        closing_calls = [call for call in mock_logger_instance.info.call_args_list 
                        if len(call[0]) > 0 and "Closing WebSocket connection" in call[0][0]]
        assert len(closing_calls) == 0
    
    def test_signal_handler_websocket_close_error(self, mock_callbacks, mock_logger):
        """Test signal handler handles WebSocket close errors gracefully."""
        mock_logger_instance = Mock()
        mock_logger.return_value = mock_logger_instance
        
        manager = WebSocketManager(
            on_message=mock_callbacks['on_message'],
            on_error=mock_callbacks['on_error'],
            on_close=mock_callbacks['on_close'],
            on_open=mock_callbacks['on_open']
        )
        
        # Set up mock WebSocket that raises exception on close
        mock_websocket = Mock()
        close_error = Exception("WebSocket close failed")
        mock_websocket.close.side_effect = close_error
        manager.current_ws = mock_websocket
        
        # Call signal handler
        mock_frame = Mock(spec=types.FrameType)
        manager._signal_handler(2, mock_frame)
        
        # Verify WebSocket close was attempted
        mock_websocket.close.assert_called_once()
        
        # Verify shutdown flag is still set despite error
        assert manager.shutdown_requested is True
        
        # Verify error logging
        mock_logger_instance.error.assert_called_once_with(
            "Error closing WebSocket", error="WebSocket close failed"
        )
        
        # Verify normal shutdown logging still occurs
        mock_logger_instance.info.assert_any_call("Shutdown signal received", signal=2)
        mock_logger_instance.info.assert_any_call("Graceful shutdown initiated")
    
    def test_signal_handler_with_different_signals(self, mock_callbacks, mock_logger):
        """Test signal handler works with different signal numbers."""
        mock_logger_instance = Mock()
        mock_logger.return_value = mock_logger_instance
        
        manager = WebSocketManager(
            on_message=mock_callbacks['on_message'],
            on_error=mock_callbacks['on_error'],
            on_close=mock_callbacks['on_close'],
            on_open=mock_callbacks['on_open']
        )
        
        # Test with SIGTERM (15)
        mock_frame = Mock(spec=types.FrameType)
        manager._signal_handler(15, mock_frame)
        
        # Verify shutdown flag is set
        assert manager.shutdown_requested is True
        
        # Verify correct signal number is logged
        mock_logger_instance.info.assert_any_call("Shutdown signal received", signal=15)