"""Unit tests for main.py RabbitMQ initialization function."""

import pytest
from unittest.mock import Mock, patch
from main import initialize_rabbitmq
from mq_messenger import MQMessenger


class TestInitializeRabbitMQ:
    """Test initialize_rabbitmq function."""
    
    @patch("main.MQMessenger.from_env")
    def test_initialize_rabbitmq_success(self, mock_from_env):
        """Test successful RabbitMQ initialization."""
        mock_messenger = Mock(spec=MQMessenger)
        mock_messenger.test_connection.return_value = True
        mock_from_env.return_value = mock_messenger
        
        result = initialize_rabbitmq()
        
        # Verify calls
        mock_from_env.assert_called_once_with(connect_on_init=True)
        mock_messenger.test_connection.assert_called_once()
        
        # Verify return value
        assert result == mock_messenger
    
    @patch("main.MQMessenger.from_env")
    def test_initialize_rabbitmq_test_connection_fails(self, mock_from_env):
        """Test RabbitMQ initialization when test_connection fails."""
        mock_messenger = Mock(spec=MQMessenger)
        mock_messenger.test_connection.return_value = False
        mock_from_env.return_value = mock_messenger
        
        with pytest.raises(SystemExit) as exc_info:
            initialize_rabbitmq()
        
        assert exc_info.value.code == 1
        mock_messenger.test_connection.assert_called_once()
    
    @patch("main.MQMessenger.from_env")
    def test_initialize_rabbitmq_connection_exception(self, mock_from_env):
        """Test RabbitMQ initialization when connection creation fails."""
        mock_from_env.side_effect = Exception("Connection failed")
        
        with pytest.raises(SystemExit) as exc_info:
            initialize_rabbitmq()
        
        assert exc_info.value.code == 1
        mock_from_env.assert_called_once_with(connect_on_init=True)
    
    @patch("main.MQMessenger.from_env")
    def test_initialize_rabbitmq_test_connection_exception(self, mock_from_env):
        """Test RabbitMQ initialization when test_connection raises exception."""
        mock_messenger = Mock(spec=MQMessenger)
        mock_messenger.test_connection.side_effect = Exception("Test failed")
        mock_from_env.return_value = mock_messenger
        
        with pytest.raises(SystemExit) as exc_info:
            initialize_rabbitmq()
        
        assert exc_info.value.code == 1
        mock_messenger.test_connection.assert_called_once()
    
    @patch("main.logger")
    @patch("main.MQMessenger.from_env")
    def test_initialize_rabbitmq_logging(self, mock_from_env, mock_logger):
        """Test that proper logging occurs during initialization."""
        mock_messenger = Mock(spec=MQMessenger)
        mock_messenger.test_connection.return_value = True
        mock_from_env.return_value = mock_messenger
        
        result = initialize_rabbitmq()
        
        # Verify logging calls
        mock_logger.info.assert_any_call("Initializing RabbitMQ connection...")
        mock_logger.info.assert_any_call("RabbitMQ connection validated successfully")
        
        assert result == mock_messenger
    
    @patch("main.logger")
    @patch("main.MQMessenger.from_env")
    def test_initialize_rabbitmq_error_logging(self, mock_from_env, mock_logger):
        """Test error logging when initialization fails."""
        error_message = "Connection refused"
        mock_from_env.side_effect = Exception(error_message)
        
        with pytest.raises(SystemExit):
            initialize_rabbitmq()
        
        # Verify error logging
        mock_logger.error.assert_called_once_with(
            "Failed to establish RabbitMQ connection at startup",
            error=error_message
        )
    
    @patch("main.logger")
    @patch("main.MQMessenger.from_env")
    def test_initialize_rabbitmq_test_failure_logging(self, mock_from_env, mock_logger):
        """Test logging when connection test fails."""
        mock_messenger = Mock(spec=MQMessenger)
        mock_messenger.test_connection.return_value = False
        mock_from_env.return_value = mock_messenger
        
        with pytest.raises(SystemExit):
            initialize_rabbitmq()
        
        # Verify specific error logging for test failure
        mock_logger.error.assert_any_call("RabbitMQ connection test failed - shutting down")
        mock_logger.error.assert_any_call(
            "Failed to establish RabbitMQ connection at startup",
            error="RabbitMQ connection validation failed"
        )