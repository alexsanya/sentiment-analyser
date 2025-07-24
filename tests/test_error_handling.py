"""
Error Handling Tests for WebSocketManager.

Tests comprehensive error handling scenarios including:
- Connection failure retry mechanism with different error types
- Shutdown flag checking during granular retry sleep periods
- Finally block cleanup across multiple exception scenarios
- WebSocket-specific exception handling
- Error logging during WebSocket close operations in signal handler
- Edge case handling when WebSocketApp constructor raises exceptions
- Multiple consecutive error recovery cycles with different exception types
"""

import pytest
from unittest.mock import Mock, patch, call
import websocket
import socket
import ssl
from src.core.websocket_manager import WebSocketManager


class TestErrorHandling:
    """Test comprehensive error handling scenarios."""
    
    def test_connection_failure_retry_mechanism(self, mock_callbacks, mock_logger, mocker):
        """Test connection failures trigger retry mechanism with proper logging."""
        # Mock WebSocketApp to raise different types of connection errors
        connection_error = ConnectionError("Network connection failed")
        timeout_error = TimeoutError("Connection timeout")
        
        mock_ws_app_1 = Mock(spec=websocket.WebSocketApp)
        mock_ws_app_1.run_forever.side_effect = connection_error
        
        mock_ws_app_2 = Mock(spec=websocket.WebSocketApp)
        mock_ws_app_2.run_forever.side_effect = timeout_error
        
        mock_ws_app_3 = Mock(spec=websocket.WebSocketApp)
        
        mock_websocket_app = mocker.patch('src.core.websocket_manager.websocket.WebSocketApp')
        mock_websocket_app.side_effect = [mock_ws_app_1, mock_ws_app_2, mock_ws_app_3]
        
        # Mock time.sleep and traceback
        mock_sleep = mocker.patch('src.core.websocket_manager.time.sleep')
        mock_traceback = mocker.patch('src.core.websocket_manager.traceback.format_exc')
        mock_traceback.side_effect = ["ConnectionError traceback", "TimeoutError traceback"]
        
        # Create manager
        manager = WebSocketManager(**mock_callbacks)
        
        # Control test execution
        sleep_call_count = 0
        def sleep_side_effect(duration):
            nonlocal sleep_call_count
            sleep_call_count += 1
            if sleep_call_count >= 10:  # After 2 full retry cycles (2 × 5 sleep calls)
                manager.shutdown_requested = True
        
        mock_sleep.side_effect = sleep_side_effect
        
        # Call connect
        url = "wss://test.example.com/websocket"
        headers = {"x-api-key": "test-key"}
        manager.connect(url, headers)
        
        # Verify multiple WebSocketApp creation attempts
        assert mock_websocket_app.call_count >= 2
        
        # Verify error logging for different error types
        error_calls = mock_logger.return_value.error.call_args_list
        assert len(error_calls) >= 2
        
        # Check that both connection errors were logged with tracebacks
        logged_errors = [call.kwargs.get('error') for call in error_calls]
        assert str(connection_error) in logged_errors
        assert str(timeout_error) in logged_errors
        
        # Verify retry messages were logged
        info_calls = mock_logger.return_value.info.call_args_list
        retry_messages = [call for call in info_calls if call[0][0] == "Retrying connection in 5 seconds"]
        assert len(retry_messages) >= 2
    
    def test_shutdown_check_during_retry_sleep_periods(self, mock_callbacks, mock_logger, mocker):
        """Test shutdown flag is checked during retry sleep periods with granular timing."""
        # Mock WebSocketApp to raise exception
        mock_ws_app = Mock(spec=websocket.WebSocketApp)
        mock_ws_app.run_forever.side_effect = Exception("Connection failed")
        mock_websocket_app = mocker.patch('src.core.websocket_manager.websocket.WebSocketApp', return_value=mock_ws_app)
        
        # Mock time.sleep to track calls
        mock_sleep = mocker.patch('src.core.websocket_manager.time.sleep')
        
        # Create manager
        manager = WebSocketManager(**mock_callbacks)
        
        # Set shutdown flag after specific number of sleep calls
        sleep_call_count = 0
        def sleep_side_effect(duration):
            nonlocal sleep_call_count
            sleep_call_count += 1
            assert duration == 1  # Each sleep call should be 1 second
            if sleep_call_count == 3:  # Set shutdown after 3 sleep calls (mid-cycle)
                manager.shutdown_requested = True
        
        mock_sleep.side_effect = sleep_side_effect
        
        # Call connect
        url = "wss://test.example.com/websocket"
        headers = {"x-api-key": "test-key"}
        manager.connect(url, headers)
        
        # Verify sleep was interrupted (should be 3 calls, not 5)
        assert mock_sleep.call_count == 3
        
        # Verify all sleep calls were 1 second (granular checking)
        for call in mock_sleep.call_args_list:
            assert call[0][0] == 1  # Each call should be sleep(1)
        
        # Verify shutdown was detected during retry loop
        mock_logger.return_value.info.assert_any_call("WebSocket connection loop ended")
    
    def test_finally_block_cleanup_scenarios(self, mock_callbacks, mock_logger, mocker):
        """Test current_ws is cleared in finally block under various scenarios."""
        scenarios = [
            ("Exception during run_forever", Exception("Test error")),
            ("KeyboardInterrupt during run_forever", KeyboardInterrupt("User interrupt")),
            ("ConnectionError during run_forever", ConnectionError("Network error")),
            ("RuntimeError during run_forever", RuntimeError("Runtime issue"))
        ]
        
        for scenario_name, exception in scenarios:
            # Mock WebSocketApp to raise specific exception
            mock_ws_app = Mock()
            mock_ws_app.run_forever.side_effect = exception
            mock_websocket_app = mocker.patch('src.core.websocket_manager.websocket.WebSocketApp', return_value=mock_ws_app)
            
            # Mock sleep for exceptions that trigger retry
            if not isinstance(exception, KeyboardInterrupt):
                mock_sleep = mocker.patch('src.core.websocket_manager.time.sleep')
                def sleep_side_effect(duration):
                    manager.shutdown_requested = True
                mock_sleep.side_effect = sleep_side_effect
            
            # Create fresh manager for each scenario
            manager = WebSocketManager(**mock_callbacks)
            
            # Verify initial state
            assert manager.current_ws is None
            
            # Call connect
            url = "wss://test.example.com/websocket"
            headers = {"x-api-key": "test-key"}
            manager.connect(url, headers)
            
            # Verify current_ws was cleared in finally block
            assert manager.current_ws is None, f"Failed for scenario: {scenario_name}"
    
    def test_various_websocket_exception_scenarios(self, mock_callbacks, mock_logger, mocker):
        """Test handling of different WebSocket-specific exception types."""
        # Test different WebSocket and network related exceptions
        test_exceptions = [
            websocket.WebSocketException("WebSocket protocol error"),
            websocket.WebSocketConnectionClosedException("Connection closed unexpectedly"),
            OSError("Network is unreachable"),
            ConnectionRefusedError("Connection refused by server"),
            ConnectionAbortedError("Connection aborted"),
            BrokenPipeError("Broken pipe error"),
            socket.error("Socket error"),
            ssl.SSLError("SSL handshake failed")
        ]
        
        for exception in test_exceptions:
            # Mock WebSocketApp to raise specific exception
            mock_ws_app = Mock()
            mock_ws_app.run_forever.side_effect = exception
            mock_websocket_app = mocker.patch('src.core.websocket_manager.websocket.WebSocketApp', return_value=mock_ws_app)
            
            # Mock sleep to control test execution
            mock_sleep = mocker.patch('src.core.websocket_manager.time.sleep')
            def sleep_side_effect(duration):
                manager.shutdown_requested = True
            mock_sleep.side_effect = sleep_side_effect
            
            # Mock traceback for error logging
            mock_traceback = mocker.patch('src.core.websocket_manager.traceback.format_exc', return_value=f"Traceback for {type(exception).__name__}")
            
            # Create fresh manager
            manager = WebSocketManager(**mock_callbacks)
            
            # Call connect
            url = "wss://test.example.com/websocket"
            headers = {"x-api-key": "test-key"}
            manager.connect(url, headers)
            
            # Verify error was logged with correct exception details
            # Find the most recent error call with our specific exception
            error_calls = mock_logger.return_value.error.call_args_list
            assert len(error_calls) >= 1
            
            # Find the error call for this specific exception
            found_call = None
            for call in error_calls:
                if (call[0][0] == "Connection error" and 
                    call[1]["error"] == str(exception) and 
                    f"Traceback for {type(exception).__name__}" in call[1]["traceback"]):
                    found_call = call
                    break
            
            assert found_call is not None, f"Expected error call not found for {exception}"
            
            # Verify retry logic was triggered for non-KeyboardInterrupt exceptions
            mock_logger.return_value.info.assert_any_call("Retrying connection in 5 seconds")
    
    def test_logging_error_during_websocket_close(self, mock_callbacks, mock_logger, mocker):
        """Test error logging when WebSocket close operation fails in signal handler."""
        # Create manager with active WebSocket
        manager = WebSocketManager(**mock_callbacks)
        
        # Mock WebSocket that raises exception during close
        mock_ws = Mock(spec=websocket.WebSocketApp)
        close_exception = Exception("WebSocket close failed")
        mock_ws.close.side_effect = close_exception
        manager.current_ws = mock_ws
        
        # Call signal handler
        import types
        mock_frame = Mock(spec=types.FrameType)
        manager._signal_handler(2, mock_frame)  # SIGINT = 2
        
        # Verify error was logged when close failed
        mock_logger.return_value.error.assert_called_once_with("Error closing WebSocket", error=str(close_exception))
        
        # Verify shutdown was still initiated
        assert manager.shutdown_requested is True
        mock_logger.return_value.info.assert_any_call("Graceful shutdown initiated")
    
    def test_edge_case_exception_during_websocket_creation(self, mock_callbacks, mock_logger, mocker):
        """Test handling when WebSocketApp constructor itself raises exception."""
        # Mock WebSocketApp constructor to raise exception
        websocket_creation_error = ValueError("Invalid WebSocket parameters")
        mock_websocket_app = mocker.patch('src.core.websocket_manager.websocket.WebSocketApp', side_effect=websocket_creation_error)
        
        # Mock sleep to control test execution
        mock_sleep = mocker.patch('src.core.websocket_manager.time.sleep')
        def sleep_side_effect(duration):
            manager.shutdown_requested = True
        mock_sleep.side_effect = sleep_side_effect
        
        # Mock traceback for error logging
        mock_traceback = mocker.patch('src.core.websocket_manager.traceback.format_exc', return_value="WebSocket creation traceback")
        
        # Create manager
        manager = WebSocketManager(**mock_callbacks)
        
        # Call connect
        url = "wss://test.example.com/websocket"
        headers = {"x-api-key": "test-key"}
        manager.connect(url, headers)
        
        # Verify WebSocketApp constructor was called
        mock_websocket_app.assert_called()
        
        # Verify error was logged
        mock_logger.return_value.error.assert_called_once()
        error_call = mock_logger.return_value.error.call_args
        assert error_call[0][0] == "Connection error"
        assert error_call[1]["error"] == str(websocket_creation_error)
        assert error_call[1]["traceback"] == "WebSocket creation traceback"
        
        # Verify current_ws remains None (never set due to creation failure)
        assert manager.current_ws is None
    
    def test_multiple_consecutive_error_recovery_cycles(self, mock_callbacks, mock_logger, mocker):
        """Test multiple consecutive error and recovery cycles with different exceptions."""
        # Create sequence of different exceptions followed by success
        exceptions_sequence = [
            ConnectionError("First connection failed"),
            TimeoutError("Second connection timed out"), 
            websocket.WebSocketException("Third connection protocol error"),
            None  # Success on fourth attempt
        ]
        
        mock_ws_apps = []
        for i, exception in enumerate(exceptions_sequence):
            mock_ws = Mock(spec=websocket.WebSocketApp)
            if exception:
                mock_ws.run_forever.side_effect = exception
            else:
                # Success case - set shutdown after connection
                def success_side_effect(*args, **kwargs):
                    manager.shutdown_requested = True
                mock_ws.run_forever.side_effect = success_side_effect
            mock_ws_apps.append(mock_ws)
        
        mock_websocket_app = mocker.patch('src.core.websocket_manager.websocket.WebSocketApp', side_effect=mock_ws_apps)
        
        # Mock sleep and traceback
        mock_sleep = mocker.patch('src.core.websocket_manager.time.sleep')
        mock_traceback = mocker.patch('src.core.websocket_manager.traceback.format_exc')
        mock_traceback.side_effect = [f"Traceback {i}" for i in range(len(exceptions_sequence))]
        
        # Create manager
        manager = WebSocketManager(**mock_callbacks)
        
        # Call connect
        url = "wss://test.example.com/websocket"
        headers = {"x-api-key": "test-key"}
        manager.connect(url, headers)
        
        # Verify all WebSocket attempts were made
        assert mock_websocket_app.call_count == len(exceptions_sequence)
        
        # Verify error logging for failed attempts (first 3)
        error_calls = mock_logger.return_value.error.call_args_list
        assert len(error_calls) == 3  # Three failed attempts
        
        # Verify each error was logged with correct exception
        for i, exception in enumerate(exceptions_sequence[:3]):
            assert error_calls[i][1]["error"] == str(exception)
        
        # Verify retry messages were logged for failed attempts
        info_calls = mock_logger.return_value.info.call_args_list
        retry_messages = [call for call in info_calls if call[0][0] == "Retrying connection in 5 seconds"]
        assert len(retry_messages) == 3  # Three retry attempts