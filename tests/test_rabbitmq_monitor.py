"""Tests for RabbitMQ connection monitoring functionality."""

import os
import threading
import time
import logging
from unittest.mock import Mock, patch, MagicMock
import pytest
from rabbitmq_monitor import RabbitMQConnectionMonitor


# Test-specific logging setup to capture messages properly
@pytest.fixture(autouse=True)
def setup_test_logging():
    """Setup basic logging for tests to capture log messages."""
    # Configure basic logging for tests
    logging.basicConfig(level=logging.DEBUG, format='%(levelname)s:%(name)s:%(message)s')
    yield
    # Clean up after tests
    logging.getLogger().handlers.clear()


class TestRabbitMQConnectionMonitor:
    """Test cases for RabbitMQ connection monitoring."""
    
    @pytest.fixture
    def mock_mq_messenger(self):
        """Create a mock MQMessenger for testing."""
        mock = Mock()
        mock.is_connected.return_value = True
        mock.test_connection.return_value = True
        mock.reconnect.return_value = True
        mock.close.return_value = None
        mock.connect.return_value = None
        return mock
    
    @pytest.fixture
    def monitor(self, mock_mq_messenger):
        """Create a RabbitMQConnectionMonitor instance for testing."""
        return RabbitMQConnectionMonitor(
            mq_messenger=mock_mq_messenger,
            check_interval=1,  # Short interval for testing
            max_retry_attempts=3,
            retry_delay=0.1  # Short delay for testing
        )
    
    def test_monitor_initialization(self, mock_mq_messenger):
        """Test monitor initialization with default parameters."""
        monitor = RabbitMQConnectionMonitor(mock_mq_messenger)
        
        assert monitor.mq_messenger is mock_mq_messenger
        assert monitor.check_interval == 30
        assert monitor.max_retry_attempts == 3
        assert monitor.retry_delay == 5
        assert not monitor._is_running
        assert monitor._last_connection_status is True
        assert monitor._consecutive_failures == 0
    
    def test_monitor_initialization_with_custom_params(self, mock_mq_messenger):
        """Test monitor initialization with custom parameters."""
        monitor = RabbitMQConnectionMonitor(
            mq_messenger=mock_mq_messenger,
            check_interval=10,
            max_retry_attempts=5,
            retry_delay=2
        )
        
        assert monitor.check_interval == 10
        assert monitor.max_retry_attempts == 5
        assert monitor.retry_delay == 2
    
    def test_from_env_factory_method(self, mock_mq_messenger):
        """Test creation from environment variables."""
        with patch.dict(os.environ, {
            'RABBITMQ_MONITOR_INTERVAL': '45',
            'RABBITMQ_MAX_RETRY_ATTEMPTS': '7',
            'RABBITMQ_RETRY_DELAY': '10'
        }):
            monitor = RabbitMQConnectionMonitor.from_env(mock_mq_messenger)
            
            assert monitor.check_interval == 45
            assert monitor.max_retry_attempts == 7
            assert monitor.retry_delay == 10
    
    def test_from_env_with_defaults(self, mock_mq_messenger):
        """Test creation from environment with default values."""
        with patch.dict(os.environ, {}, clear=True):
            monitor = RabbitMQConnectionMonitor.from_env(mock_mq_messenger)
            
            assert monitor.check_interval == 30
            assert monitor.max_retry_attempts == 3
            assert monitor.retry_delay == 5
    
    def test_start_monitor(self, monitor):
        """Test starting the connection monitor."""
        assert not monitor._is_running
        
        monitor.start()
        
        assert monitor._is_running
        assert monitor._monitor_thread is not None
        assert monitor._monitor_thread.is_alive()
        assert monitor._monitor_thread.daemon is True
        
        # Cleanup
        monitor.stop()
    
    def test_start_monitor_already_running(self, monitor):
        """Test starting monitor when already running."""
        with patch('rabbitmq_monitor.logger') as mock_logger:
            monitor.start()
            
            # Try to start again
            monitor.start()
            
            # Check that warning was logged
            mock_logger.warning.assert_called_with("Connection monitor is already running")
            
            # Cleanup
            monitor.stop()
    
    def test_stop_monitor(self, monitor):
        """Test stopping the connection monitor."""
        monitor.start()
        assert monitor._is_running
        
        monitor.stop()
        
        assert not monitor._is_running
        assert monitor._shutdown_event.is_set()
        
        # Wait a bit for thread to finish
        time.sleep(0.1)
        assert not monitor._monitor_thread.is_alive()
    
    def test_stop_monitor_not_running(self, monitor):
        """Test stopping monitor when not running."""
        assert not monitor._is_running
        
        # Should not raise exception
        monitor.stop()
        
        assert not monitor._is_running
    
    def test_connection_health_check_success(self, monitor, mock_mq_messenger):
        """Test successful connection health check."""
        mock_mq_messenger.is_connected.return_value = True
        mock_mq_messenger.test_connection.return_value = True
        
        monitor._check_and_handle_connection()
        
        assert monitor._consecutive_failures == 0
        assert monitor._last_connection_status is True
        mock_mq_messenger.is_connected.assert_called_once()
        mock_mq_messenger.test_connection.assert_called_once()
    
    def test_connection_health_check_failure(self, monitor, mock_mq_messenger):
        """Test connection health check failure."""
        mock_mq_messenger.is_connected.return_value = False
        mock_mq_messenger.test_connection.return_value = False
        mock_mq_messenger.reconnect.return_value = True
        
        monitor._check_and_handle_connection()
        
        assert monitor._consecutive_failures == 0  # Reset after successful reconnect
        mock_mq_messenger.reconnect.assert_called_once()
    
    def test_connection_test_failure(self, monitor, mock_mq_messenger):
        """Test when connection exists but test fails."""
        mock_mq_messenger.is_connected.return_value = True
        mock_mq_messenger.test_connection.return_value = False
        mock_mq_messenger.reconnect.return_value = True
        
        monitor._check_and_handle_connection()
        
        assert monitor._consecutive_failures == 0  # Reset after successful reconnect
        mock_mq_messenger.reconnect.assert_called_once()
    
    def test_reconnection_attempt_success(self, monitor, mock_mq_messenger):
        """Test successful reconnection attempt."""
        mock_mq_messenger.reconnect.return_value = True
        
        monitor._consecutive_failures = 1
        monitor._attempt_reconnection()
        
        assert monitor._consecutive_failures == 0
        assert monitor._last_connection_status is True
        mock_mq_messenger.reconnect.assert_called_once()
    
    def test_reconnection_attempt_failure(self, monitor, mock_mq_messenger):
        """Test failed reconnection attempt."""
        mock_mq_messenger.reconnect.return_value = False
        
        monitor._consecutive_failures = 1
        monitor._attempt_reconnection()
        
        assert monitor._consecutive_failures == 1  # No change on failure
        mock_mq_messenger.reconnect.assert_called_once()
    
    def test_reconnection_fallback_method(self, monitor, mock_mq_messenger):
        """Test fallback reconnection when reconnect method not available."""
        # Remove reconnect method to test fallback
        delattr(mock_mq_messenger, 'reconnect')
        mock_mq_messenger.test_connection.return_value = True
        
        monitor._consecutive_failures = 1
        monitor._attempt_reconnection()
        
        assert monitor._consecutive_failures == 0
        mock_mq_messenger.close.assert_called_once()
        mock_mq_messenger.connect.assert_called_once()
        mock_mq_messenger.test_connection.assert_called_once()
    
    def test_max_retry_attempts_exceeded(self, monitor, mock_mq_messenger):
        """Test behavior when max retry attempts are exceeded."""
        with patch('rabbitmq_monitor.logger') as mock_logger:
            mock_mq_messenger.reconnect.return_value = False
            
            monitor._consecutive_failures = 4  # Exceeds max of 3
            monitor._attempt_reconnection()
            
            # Check that error was logged with expected message
            mock_logger.error.assert_called_once()
            call_args = mock_logger.error.call_args
            assert "Maximum reconnection attempts exceeded" in call_args[0][0]
            
            assert monitor._consecutive_failures == 4  # No change
            # Should not attempt reconnect
            mock_mq_messenger.reconnect.assert_not_called()
    
    def test_reconnection_exception_handling(self, monitor, mock_mq_messenger):
        """Test exception handling during reconnection."""
        with patch('rabbitmq_monitor.logger') as mock_logger:
            mock_mq_messenger.reconnect.side_effect = Exception("Connection failed")
            
            monitor._consecutive_failures = 1
            monitor._attempt_reconnection()
            
            # Check that error was logged
            mock_logger.error.assert_called_once()
            call_args = mock_logger.error.call_args
            assert "RabbitMQ reconnection attempt failed" in call_args[0][0]
            
            assert monitor._consecutive_failures == 1
    
    def test_get_status(self, monitor):
        """Test getting monitor status information."""
        monitor._consecutive_failures = 2
        monitor._last_connection_status = False
        monitor._is_running = True
        
        status = monitor.get_status()
        
        expected = {
            "is_running": True,
            "last_connection_status": False,
            "consecutive_failures": 2,
            "max_retry_attempts": 3,
            "check_interval": 1
        }
        
        assert status == expected
    
    def test_monitor_loop_integration(self, mock_mq_messenger):
        """Test the complete monitoring loop integration."""
        with patch('rabbitmq_monitor.logger') as mock_logger:
            monitor = RabbitMQConnectionMonitor(
                mq_messenger=mock_mq_messenger,
                check_interval=0.1,  # Very short for testing
                max_retry_attempts=3,
                retry_delay=0.01
            )
            
            # Simulate successful connection consistently
            mock_mq_messenger.is_connected.return_value = True
            mock_mq_messenger.test_connection.return_value = True
            mock_mq_messenger.reconnect.return_value = True
            
            monitor.start()
            
            # Let it run a few cycles
            time.sleep(0.3)
            
            monitor.stop()
            
            # Check that monitoring loop messages were logged
            log_calls = [call[0][0] for call in mock_logger.info.call_args_list]
            assert any("Connection monitoring loop started" in msg for msg in log_calls)
            assert any("Connection monitoring loop ended" in msg for msg in log_calls)
    
    def test_connection_status_change_logging(self, monitor, mock_mq_messenger):
        """Test logging of connection status changes."""
        with patch('rabbitmq_monitor.logger') as mock_logger:
            # Start with good connection
            mock_mq_messenger.is_connected.return_value = True
            mock_mq_messenger.test_connection.return_value = True
            monitor._last_connection_status = True
            
            # Simulate connection failure
            mock_mq_messenger.is_connected.return_value = False
            mock_mq_messenger.test_connection.return_value = False
            mock_mq_messenger.reconnect.return_value = True
            
            monitor._check_and_handle_connection()
            
            # Check for connection lost warning
            warning_calls = [call[0][0] for call in mock_logger.warning.call_args_list]
            assert any("RabbitMQ connection lost" in msg for msg in warning_calls)
            
            # Reset mock and simulate recovery
            mock_logger.reset_mock()
            mock_mq_messenger.is_connected.return_value = True
            mock_mq_messenger.test_connection.return_value = True
            monitor._last_connection_status = False  # Simulate it was false
            
            monitor._check_and_handle_connection()
            
            # Check for connection restored info
            info_calls = [call[0][0] for call in mock_logger.info.call_args_list]
            assert any("RabbitMQ connection restored" in msg for msg in info_calls)
    
    def test_thread_shutdown_timeout(self, monitor):
        """Test thread shutdown with timeout."""
        # Create a monitor that will take time to stop
        with patch.object(monitor, '_monitor_loop') as mock_loop:
            # Make the loop sleep longer than shutdown timeout
            mock_loop.side_effect = lambda: time.sleep(10)
            
            monitor.start()
            
            with patch.object(monitor._monitor_thread, 'join') as mock_join:
                mock_join.return_value = None
                monitor._monitor_thread.is_alive = Mock(return_value=True)
                
                monitor.stop()
                
                mock_join.assert_called_once_with(timeout=5.0)


class TestRabbitMQMonitorEnvironmentIntegration:
    """Integration tests for monitor with environment configuration."""
    
    def test_monitor_environment_configuration(self):
        """Test monitor configuration from environment variables."""
        test_env = {
            'RABBITMQ_MONITOR_INTERVAL': '60',
            'RABBITMQ_MAX_RETRY_ATTEMPTS': '10',
            'RABBITMQ_RETRY_DELAY': '15'
        }
        
        mock_messenger = Mock()
        
        with patch.dict(os.environ, test_env):
            monitor = RabbitMQConnectionMonitor.from_env(mock_messenger)
            
            assert monitor.check_interval == 60
            assert monitor.max_retry_attempts == 10
            assert monitor.retry_delay == 15
    
    def test_monitor_with_main_integration(self):
        """Test monitor integration patterns similar to main.py usage."""
        mock_messenger = Mock()
        mock_messenger.is_connected.return_value = True
        mock_messenger.test_connection.return_value = True
        
        # Test the pattern used in main.py
        monitor = RabbitMQConnectionMonitor.from_env(mock_messenger)
        
        # Start monitoring
        monitor.start()
        assert monitor._is_running
        
        # Simulate graceful shutdown
        monitor.stop()
        assert not monitor._is_running
        
        # Should be safe to call multiple times
        monitor.stop()
        assert not monitor._is_running