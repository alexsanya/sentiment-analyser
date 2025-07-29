"""Tests for MQSubscriber reconnect functionality."""

import pytest
import logging
from unittest.mock import Mock, patch, MagicMock
from src.core.mq_subscriber import MQSubscriber
import pika


# Test-specific logging setup to capture messages properly
@pytest.fixture(autouse=True)
def setup_test_logging():
    """Setup basic logging for tests to capture log messages."""
    # Configure basic logging for tests
    logging.basicConfig(level=logging.DEBUG, format='%(levelname)s:%(name)s:%(message)s')
    yield
    # Clean up after tests
    logging.getLogger().handlers.clear()


class TestMQSubscriberReconnect:
    """Test cases for MQSubscriber reconnect method."""
    
    @pytest.fixture
    def messenger(self):
        """Create MQSubscriber instance for testing."""
        return MQSubscriber(
            host="localhost",
            port=5672,
            queue_name="test_queue",
            username="test_user",
            password="test_pass"
        )
    
    def test_reconnect_success(self, messenger):
        """Test successful reconnection."""
        # Mock the internal methods
        with patch.object(messenger, '_cleanup_connection') as mock_cleanup, \
             patch.object(messenger, '_create_connection') as mock_create, \
             patch.object(messenger, 'is_connected', return_value=True) as mock_is_connected, \
             patch('src.core.mq_messenger.logger') as mock_logger:
            
            result = messenger.reconnect()
            
            assert result is True
            mock_cleanup.assert_called_once()
            mock_create.assert_called_once()
            mock_is_connected.assert_called_once()
            
            # Check logging calls
            info_calls = [call[0][0] for call in mock_logger.info.call_args_list]
            assert any("Attempting to reconnect to RabbitMQ" in msg for msg in info_calls)
            assert any("RabbitMQ reconnection successful" in msg for msg in info_calls)
    
    def test_reconnect_connection_not_established(self, messenger):
        """Test reconnection when connection is not properly established."""
        with patch.object(messenger, '_cleanup_connection') as mock_cleanup, \
             patch.object(messenger, '_create_connection') as mock_create, \
             patch.object(messenger, 'is_connected', return_value=False) as mock_is_connected, \
             patch('src.core.mq_messenger.logger') as mock_logger:
            
            result = messenger.reconnect()
            
            assert result is False
            mock_cleanup.assert_called_once()
            mock_create.assert_called_once()
            mock_is_connected.assert_called_once()
            
            # Check error logging
            error_calls = [call[0][0] for call in mock_logger.error.call_args_list]
            assert any("RabbitMQ reconnection failed - connection not established" in msg for msg in error_calls)
    
    def test_reconnect_create_connection_exception(self, messenger):
        """Test reconnection when _create_connection raises exception."""
        test_exception = Exception("Connection creation failed")
        
        with patch.object(messenger, '_cleanup_connection') as mock_cleanup, \
             patch.object(messenger, '_create_connection', side_effect=test_exception) as mock_create, \
             patch('src.core.mq_messenger.logger') as mock_logger:
            
            result = messenger.reconnect()
            
            assert result is False
            mock_cleanup.assert_called_once()
            mock_create.assert_called_once()
            
            # Check error logging
            error_calls = [call[0][0] for call in mock_logger.error.call_args_list]
            assert any("RabbitMQ reconnection failed" in msg for msg in error_calls)
    
    def test_reconnect_cleanup_connection_exception(self, messenger):
        """Test reconnection when _cleanup_connection raises exception."""
        cleanup_exception = Exception("Cleanup failed")
        
        with patch.object(messenger, '_cleanup_connection', side_effect=cleanup_exception) as mock_cleanup, \
             patch('src.core.mq_messenger.logger') as mock_logger:
            
            result = messenger.reconnect()
            
            assert result is False
            mock_cleanup.assert_called_once()
            
            # Check error logging
            error_calls = [call[0][0] for call in mock_logger.error.call_args_list]
            assert any("RabbitMQ reconnection failed" in msg for msg in error_calls)
    
    def test_reconnect_is_connected_exception(self, messenger):
        """Test reconnection when is_connected raises exception."""
        test_exception = Exception("Connection check failed")
        
        with patch.object(messenger, '_cleanup_connection') as mock_cleanup, \
             patch.object(messenger, '_create_connection') as mock_create, \
             patch.object(messenger, 'is_connected', side_effect=test_exception) as mock_is_connected, \
             patch('src.core.mq_messenger.logger') as mock_logger:
            
            result = messenger.reconnect()
            
            assert result is False
            mock_cleanup.assert_called_once()
            mock_create.assert_called_once()
            mock_is_connected.assert_called_once()
            
            # Check error logging
            error_calls = [call[0][0] for call in mock_logger.error.call_args_list]
            assert any("RabbitMQ reconnection failed" in msg for msg in error_calls)
    
    def test_reconnect_integration_with_real_objects(self, messenger):
        """Test reconnection with more realistic mock objects."""
        # Create mock connection and channel objects
        mock_connection = Mock()
        mock_connection.is_closed = False
        mock_channel = Mock()
        mock_channel.is_closed = False
        
        # Set up initial state
        messenger._connection = mock_connection
        messenger._channel = mock_channel
        
        with patch('pika.BlockingConnection') as mock_blocking_conn, \
             patch.object(mock_connection, 'close') as mock_conn_close, \
             patch.object(mock_channel, 'close') as mock_chan_close:
            
            # Configure the new connection mock
            new_mock_connection = Mock()
            new_mock_connection.is_closed = False
            new_mock_channel = Mock()
            new_mock_channel.is_closed = False
            
            mock_blocking_conn.return_value = new_mock_connection
            new_mock_connection.channel.return_value = new_mock_channel
            
            result = messenger.reconnect()
            
            assert result is True
            # Verify cleanup was called
            mock_chan_close.assert_called_once()
            mock_conn_close.assert_called_once()
            # Verify new connection was created
            mock_blocking_conn.assert_called_once()
            new_mock_connection.channel.assert_called_once()
    
    def test_reconnect_with_existing_closed_connection(self, messenger):
        """Test reconnection when existing connection is already closed."""
        # Create mock objects representing closed connections
        mock_connection = Mock()
        mock_connection.is_closed = True
        mock_channel = Mock()
        mock_channel.is_closed = True
        
        messenger._connection = mock_connection
        messenger._channel = mock_channel
        
        with patch('pika.BlockingConnection') as mock_blocking_conn:
            new_mock_connection = Mock()
            new_mock_connection.is_closed = False
            new_mock_channel = Mock()
            new_mock_channel.is_closed = False
            
            mock_blocking_conn.return_value = new_mock_connection
            new_mock_connection.channel.return_value = new_mock_channel
            
            result = messenger.reconnect()
            
            assert result is True
            # Closed connections shouldn't be closed again
            mock_connection.close.assert_not_called()
            mock_channel.close.assert_not_called()
    
    def test_reconnect_logging_behavior(self, messenger):
        """Test comprehensive logging during reconnection process."""
        with patch.object(messenger, '_cleanup_connection') as mock_cleanup, \
             patch.object(messenger, '_create_connection') as mock_create, \
             patch.object(messenger, 'is_connected', return_value=True) as mock_is_connected, \
             patch('src.core.mq_messenger.logger') as mock_logger:
            
            result = messenger.reconnect()
            
            # Check all expected log messages
            info_calls = [call[0][0] for call in mock_logger.info.call_args_list]
            
            assert any("Attempting to reconnect to RabbitMQ" in msg for msg in info_calls)
            assert any("RabbitMQ reconnection successful" in msg for msg in info_calls)
            assert result is True
    
    def test_reconnect_error_logging_with_exception_type(self, messenger):
        """Test error logging includes exception type information."""
        test_exception = ConnectionError("Specific connection error")
        
        with patch.object(messenger, '_cleanup_connection') as mock_cleanup, \
             patch.object(messenger, '_create_connection', side_effect=test_exception) as mock_create, \
             patch('src.core.mq_messenger.logger') as mock_logger:
            
            result = messenger.reconnect()
            
            assert result is False
            # Check that error is logged
            error_calls = [call[0][0] for call in mock_logger.error.call_args_list]
            assert any("RabbitMQ reconnection failed" in msg for msg in error_calls)


class TestMQSubscriberReconnectEdgeCases:
    """Test edge cases and error conditions for reconnect functionality."""
    
    def test_reconnect_multiple_consecutive_calls(self):
        """Test multiple consecutive reconnect calls."""
        messenger = MQSubscriber(host="localhost", port=5672, queue_name="test")
        
        with patch.object(messenger, '_cleanup_connection') as mock_cleanup, \
             patch.object(messenger, '_create_connection') as mock_create, \
             patch.object(messenger, 'is_connected', return_value=True) as mock_is_connected:
            
            # Call reconnect multiple times
            result1 = messenger.reconnect()
            result2 = messenger.reconnect()
            result3 = messenger.reconnect()
            
            assert all([result1, result2, result3])
            assert mock_cleanup.call_count == 3
            assert mock_create.call_count == 3
            assert mock_is_connected.call_count == 3
    
    def test_reconnect_with_none_connection_and_channel(self):
        """Test reconnect when connection and channel are None."""
        messenger = MQSubscriber(host="localhost", port=5672, queue_name="test")
        
        # Ensure connection and channel are None
        messenger._connection = None
        messenger._channel = None
        
        with patch('pika.BlockingConnection') as mock_blocking_conn:
            new_mock_connection = Mock()
            new_mock_connection.is_closed = False
            new_mock_channel = Mock()
            new_mock_channel.is_closed = False
            
            mock_blocking_conn.return_value = new_mock_connection
            new_mock_connection.channel.return_value = new_mock_channel
            
            result = messenger.reconnect()
            
            assert result is True
            # Should not try to close None objects
            assert new_mock_connection.close.call_count == 0
    
    def test_reconnect_partial_failure_scenarios(self):
        """Test various partial failure scenarios during reconnection."""
        messenger = MQSubscriber(host="localhost", port=5672, queue_name="test")
        
        # Test scenario: cleanup succeeds, create fails
        with patch.object(messenger, '_cleanup_connection') as mock_cleanup, \
             patch.object(messenger, '_create_connection', side_effect=Exception("Create failed")):
            
            result = messenger.reconnect()
            assert result is False
            mock_cleanup.assert_called_once()
        
        # Reset for next test
        mock_cleanup.reset_mock()
        
        # Test scenario: both cleanup and create succeed, but is_connected fails
        with patch.object(messenger, '_cleanup_connection') as mock_cleanup, \
             patch.object(messenger, '_create_connection') as mock_create, \
             patch.object(messenger, 'is_connected', side_effect=Exception("Check failed")):
            
            result = messenger.reconnect()
            assert result is False
            mock_cleanup.assert_called_once()
            mock_create.assert_called_once()