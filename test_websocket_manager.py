import pytest
import types
from unittest.mock import Mock, MagicMock
from websocket_manager import WebSocketManager


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
    return mocker.patch('websocket_manager.get_logger')


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
        mocker.patch('websocket_manager.get_logger')
        
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
        mocker.patch('websocket_manager.get_logger')
        
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
        
        mocker.patch('websocket_manager.get_logger')
        
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