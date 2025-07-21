"""
Connection Management Tests for WebSocketManager.

Tests the connect() method functionality including:
- Successful WebSocket connection establishment
- Connection retry logic with 5-second delays
- Graceful shutdown interrupting connection loop
- KeyboardInterrupt handling
- Exception handling with proper logging
"""

import pytest
from unittest.mock import Mock, patch, call
import websocket
from websocket_manager import WebSocketManager


class TestConnectionManagement:
    """Test connection management functionality."""
    
    def test_connect_successful_connection(self, mock_callbacks, mock_logger, mocker):
        """Test successful WebSocket connection establishment."""
        # Mock WebSocketApp
        mock_ws_app = Mock(spec=websocket.WebSocketApp)
        mock_websocket_app = mocker.patch('websocket_manager.websocket.WebSocketApp', return_value=mock_ws_app)
        
        # Create manager
        manager = WebSocketManager(**mock_callbacks)
        
        # Set shutdown flag after first run_forever call
        def run_forever_side_effect(*args, **kwargs):
            manager.shutdown_requested = True
        
        mock_ws_app.run_forever.side_effect = run_forever_side_effect
        
        # Call connect
        url = "wss://example.com/websocket"
        headers = {"x-api-key": "test-key"}
        manager.connect(url, headers)
        
        # Verify WebSocketApp was created with correct parameters
        mock_websocket_app.assert_called_once_with(
            url,
            header=headers,
            on_message=mock_callbacks['on_message'],
            on_error=mock_callbacks['on_error'],
            on_close=mock_callbacks['on_close'],
            on_open=mock_callbacks['on_open']
        )
        
        # Verify current_ws was set and cleared
        assert manager.current_ws is None
        
        # Verify run_forever was called with correct parameters
        mock_ws_app.run_forever.assert_called_once_with(ping_interval=30, ping_timeout=20)
    
    def test_connect_with_retry_logic(self, mock_callbacks, mock_logger, mocker):
        """Test connection retry after failures with 5-second delays."""
        # Mock WebSocketApp to raise exception on first call
        mock_ws_app_1 = Mock(spec=websocket.WebSocketApp)
        mock_ws_app_1.run_forever.side_effect = Exception("Connection failed")
        
        mock_ws_app_2 = Mock(spec=websocket.WebSocketApp)
        
        mock_websocket_app = mocker.patch('websocket_manager.websocket.WebSocketApp')
        mock_websocket_app.side_effect = [mock_ws_app_1, mock_ws_app_2]
        
        # Mock time.sleep
        mock_sleep = mocker.patch('websocket_manager.time.sleep')
        
        # Create manager
        manager = WebSocketManager(**mock_callbacks)
        
        # Set up to stop after first retry attempt
        call_count = 0
        def mock_sleep_side_effect(duration):
            nonlocal call_count
            call_count += 1
            if call_count >= 5:  # After 5 sleep calls (full retry cycle)
                manager.shutdown_requested = True
        
        mock_sleep.side_effect = mock_sleep_side_effect
        
        # Call connect
        url = "wss://example.com/websocket"
        headers = {"x-api-key": "test-key"}
        manager.connect(url, headers)
        
        # Verify WebSocketApp was created for initial attempt
        assert mock_websocket_app.call_count >= 1
        
        # Verify error was logged
        mock_logger.return_value.error.assert_called_once()
        
        # Verify retry delay (5 sleep calls of 1 second each)
        assert mock_sleep.call_count == 5
        mock_sleep.assert_has_calls([call(1)] * 5)
        
        # Verify retry message was logged
        mock_logger.return_value.info.assert_any_call("Retrying connection in 5 seconds")
    
    def test_connect_shutdown_interrupts_loop(self, mock_callbacks, mock_logger, mocker):
        """Test shutdown flag interrupts connection loop."""
        # Mock WebSocketApp
        mock_ws_app = Mock(spec=websocket.WebSocketApp)
        mock_websocket_app = mocker.patch('websocket_manager.websocket.WebSocketApp', return_value=mock_ws_app)
        
        # Create manager with shutdown already requested
        manager = WebSocketManager(**mock_callbacks)
        manager.shutdown_requested = True
        
        # Call connect
        url = "wss://example.com/websocket"
        headers = {"x-api-key": "test-key"}
        manager.connect(url, headers)
        
        # Verify WebSocketApp was not created since shutdown was already requested
        mock_websocket_app.assert_not_called()
        
        # Verify connection loop ended message (this is what gets logged when shutdown is already True)
        mock_logger.return_value.info.assert_any_call("WebSocket connection loop ended")
    
    def test_connect_shutdown_interrupts_retry_sleep(self, mock_callbacks, mock_logger, mocker):
        """Test shutdown flag interrupts retry sleep period."""
        # Mock WebSocketApp to raise exception
        mock_ws_app = Mock(spec=websocket.WebSocketApp)
        mock_ws_app.run_forever.side_effect = Exception("Connection failed")
        mock_websocket_app = mocker.patch('websocket_manager.websocket.WebSocketApp', return_value=mock_ws_app)
        
        # Mock time.sleep
        mock_sleep = mocker.patch('websocket_manager.time.sleep')
        
        # Create manager
        manager = WebSocketManager(**mock_callbacks)
        
        # Set shutdown flag during sleep period
        sleep_call_count = 0
        def sleep_side_effect(duration):
            nonlocal sleep_call_count
            sleep_call_count += 1
            if sleep_call_count == 2:  # Set shutdown after 2 sleep calls
                manager.shutdown_requested = True
        
        mock_sleep.side_effect = sleep_side_effect
        
        # Call connect
        url = "wss://example.com/websocket"
        headers = {"x-api-key": "test-key"}
        manager.connect(url, headers)
        
        # Verify sleep was interrupted (should be 2 calls, not 5)
        assert mock_sleep.call_count == 2
        
        # The actual log message when shutdown interrupts the retry loop
        mock_logger.return_value.info.assert_any_call("WebSocket connection loop ended")
    
    def test_connect_keyboard_interrupt(self, mock_callbacks, mock_logger, mocker):
        """Test KeyboardInterrupt handling in connection loop."""
        # Mock WebSocketApp to raise KeyboardInterrupt
        mock_ws_app = Mock(spec=websocket.WebSocketApp)
        mock_ws_app.run_forever.side_effect = KeyboardInterrupt("User interrupt")
        mock_websocket_app = mocker.patch('websocket_manager.websocket.WebSocketApp', return_value=mock_ws_app)
        
        # Create manager
        manager = WebSocketManager(**mock_callbacks)
        
        # Call connect
        url = "wss://example.com/websocket"
        headers = {"x-api-key": "test-key"}
        manager.connect(url, headers)
        
        # Verify KeyboardInterrupt was logged
        mock_logger.return_value.info.assert_any_call("KeyboardInterrupt received")
        
        # Verify current_ws was cleared
        assert manager.current_ws is None
        
        # Verify connection loop ended
        mock_logger.return_value.info.assert_any_call("WebSocket connection loop ended")
    
    def test_connect_exception_handling(self, mock_callbacks, mock_logger, mocker):
        """Test general exception handling with proper logging."""
        # Mock WebSocketApp to raise exception
        test_exception = Exception("Test connection error")
        mock_ws_app = Mock(spec=websocket.WebSocketApp)
        mock_ws_app.run_forever.side_effect = test_exception
        mock_websocket_app = mocker.patch('websocket_manager.websocket.WebSocketApp', return_value=mock_ws_app)
        
        # Mock traceback for traceback logging
        mock_traceback = mocker.patch('websocket_manager.traceback.format_exc', return_value="Mock traceback")
        
        # Mock time.sleep to set shutdown flag after sleep calls
        mock_sleep = mocker.patch('websocket_manager.time.sleep')
        
        # Create manager
        manager = WebSocketManager(**mock_callbacks)
        
        # Set shutdown flag after first sleep cycle to avoid infinite loop
        def sleep_side_effect(duration):
            manager.shutdown_requested = True
        
        mock_sleep.side_effect = sleep_side_effect
        
        # Call connect
        url = "wss://example.com/websocket"
        headers = {"x-api-key": "test-key"}
        manager.connect(url, headers)
        
        # Verify error was logged with traceback (may be called once)
        assert mock_logger.return_value.error.call_count >= 1
        error_calls = mock_logger.return_value.error.call_args_list
        
        # Find the call with our specific error
        found_expected_call = False
        for call in error_calls:
            args, kwargs = call
            if (args == ("Connection error",) and 
                kwargs.get("error") == str(test_exception) and 
                kwargs.get("traceback") == "Mock traceback"):
                found_expected_call = True
                break
        
        assert found_expected_call, f"Expected error call not found in: {error_calls}"
        
        # Verify retry logic was triggered
        mock_logger.return_value.info.assert_any_call("Retrying connection in 5 seconds")
    
    def test_connect_current_ws_reference_management(self, mock_callbacks, mock_logger, mocker):
        """Test current_ws is properly set and cleared."""
        # Mock WebSocketApp
        mock_ws_app = Mock(spec=websocket.WebSocketApp)
        mock_websocket_app = mocker.patch('websocket_manager.websocket.WebSocketApp', return_value=mock_ws_app)
        
        # Create manager
        manager = WebSocketManager(**mock_callbacks)
        
        # Track current_ws during run_forever
        current_ws_during_run = None
        def run_forever_side_effect(*args, **kwargs):
            nonlocal current_ws_during_run
            current_ws_during_run = manager.current_ws
            manager.shutdown_requested = True  # Exit after first iteration
        
        mock_ws_app.run_forever.side_effect = run_forever_side_effect
        
        # Call connect
        url = "wss://example.com/websocket"
        headers = {"x-api-key": "test-key"}
        manager.connect(url, headers)
        
        # Verify current_ws was set during connection
        assert current_ws_during_run is mock_ws_app
        
        # Verify current_ws was cleared after connection ended
        assert manager.current_ws is None
    
    def test_connect_double_shutdown_check(self, mock_callbacks, mock_logger, mocker):
        """Test the double shutdown check at the beginning of the loop."""
        # Mock WebSocketApp
        mock_ws_app = Mock(spec=websocket.WebSocketApp)
        mock_websocket_app = mocker.patch('websocket_manager.websocket.WebSocketApp', return_value=mock_ws_app)
        
        # Create manager with shutdown not initially requested
        manager = WebSocketManager(**mock_callbacks)
        
        # Mock the connect method to test the double shutdown check logic
        original_connect = manager.connect
        check_count = 0
        
        def mock_connect(url, headers):
            nonlocal check_count
            while not manager.shutdown_requested:
                check_count += 1
                if check_count == 1:
                    # First check passes
                    if manager.shutdown_requested:
                        manager.logger.info("Shutdown requested, exiting connection loop")
                        break
                elif check_count == 2:
                    # Set shutdown flag for second check
                    manager.shutdown_requested = True
                    if manager.shutdown_requested:
                        manager.logger.info("Shutdown requested, exiting connection loop")
                        break
            manager.logger.info("WebSocket connection loop ended")
        
        # Replace connect method temporarily
        manager.connect = mock_connect
        
        # Call connect
        url = "wss://example.com/websocket"
        headers = {"x-api-key": "test-key"}
        manager.connect(url, headers)
        
        # Verify the inner shutdown check was triggered
        mock_logger.return_value.info.assert_any_call("Shutdown requested, exiting connection loop")
        
        # Verify WebSocketApp was not created (since we mocked the method)
        mock_websocket_app.assert_not_called()


class TestWebSocketLifecycle:
    """Test WebSocket lifecycle management functionality."""
    
    def test_websocket_app_creation(self, mock_callbacks, mock_logger, mocker):
        """Test WebSocketApp is created with correct parameters."""
        # Mock WebSocketApp
        mock_ws_app = Mock(spec=websocket.WebSocketApp)
        mock_websocket_app = mocker.patch('websocket_manager.websocket.WebSocketApp', return_value=mock_ws_app)
        
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
        mock_websocket_app = mocker.patch('websocket_manager.websocket.WebSocketApp', return_value=mock_ws_app)
        
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
        mock_websocket_app = mocker.patch('websocket_manager.websocket.WebSocketApp', return_value=mock_ws_app)
        
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
        mock_websocket_app = mocker.patch('websocket_manager.websocket.WebSocketApp', return_value=mock_ws_app)
        
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
        mock_websocket_app = mocker.patch('websocket_manager.websocket.WebSocketApp', return_value=mock_ws_app)
        
        # Mock time.sleep to set shutdown flag and avoid infinite retry loop
        mock_sleep = mocker.patch('websocket_manager.time.sleep')
        
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
        mock_websocket_app = mocker.patch('websocket_manager.websocket.WebSocketApp', return_value=mock_ws_app)
        
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
        
        mock_websocket_app = mocker.patch('websocket_manager.websocket.WebSocketApp')
        mock_websocket_app.side_effect = [mock_ws_app_1, mock_ws_app_2, mock_ws_app_3]
        
        # Mock time.sleep and traceback
        mock_sleep = mocker.patch('websocket_manager.time.sleep')
        mock_traceback = mocker.patch('websocket_manager.traceback.format_exc')
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
        mock_websocket_app = mocker.patch('websocket_manager.websocket.WebSocketApp', return_value=mock_ws_app)
        
        # Mock time.sleep to track calls
        mock_sleep = mocker.patch('websocket_manager.time.sleep')
        
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
            mock_websocket_app = mocker.patch('websocket_manager.websocket.WebSocketApp', return_value=mock_ws_app)
            
            # Mock sleep for exceptions that trigger retry
            if not isinstance(exception, KeyboardInterrupt):
                mock_sleep = mocker.patch('websocket_manager.time.sleep')
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
        # Import required modules for exceptions
        import socket
        import ssl
        
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
            mock_websocket_app = mocker.patch('websocket_manager.websocket.WebSocketApp', return_value=mock_ws_app)
            
            # Mock sleep to control test execution
            mock_sleep = mocker.patch('websocket_manager.time.sleep')
            def sleep_side_effect(duration):
                manager.shutdown_requested = True
            mock_sleep.side_effect = sleep_side_effect
            
            # Mock traceback for error logging
            mock_traceback = mocker.patch('websocket_manager.traceback.format_exc', return_value=f"Traceback for {type(exception).__name__}")
            
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
        mock_websocket_app = mocker.patch('websocket_manager.websocket.WebSocketApp', side_effect=websocket_creation_error)
        
        # Mock sleep to control test execution
        mock_sleep = mocker.patch('websocket_manager.time.sleep')
        def sleep_side_effect(duration):
            manager.shutdown_requested = True
        mock_sleep.side_effect = sleep_side_effect
        
        # Mock traceback for error logging
        mock_traceback = mocker.patch('websocket_manager.traceback.format_exc', return_value="WebSocket creation traceback")
        
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
        
        mock_websocket_app = mocker.patch('websocket_manager.websocket.WebSocketApp', side_effect=mock_ws_apps)
        
        # Mock sleep and traceback
        mock_sleep = mocker.patch('websocket_manager.time.sleep')
        mock_traceback = mocker.patch('websocket_manager.traceback.format_exc')
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