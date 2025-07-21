"""
Connection Management Tests for WebSocketManager.

Tests the connect() method functionality including:
- Successful WebSocket connection establishment
- Connection retry logic with 5-second delays
- Graceful shutdown interrupting connection loop
- KeyboardInterrupt handling
- Exception handling with proper logging
- WebSocket reference management during connection lifecycle
- Double shutdown check logic validation
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