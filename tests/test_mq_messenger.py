"""Unit tests for MQMessenger class."""

import json
import pytest
from unittest.mock import Mock, patch, MagicMock
import pika
from mq_messenger import MQMessenger


class TestMQMessengerInitialization:
    """Test MQMessenger initialization and configuration."""
    
    def test_init_with_default_parameters(self):
        messenger = MQMessenger()
        assert messenger.host == "localhost"
        assert messenger.port == 5672
        assert messenger.queue_name == "tweet_events"
        assert messenger.username is None
        assert messenger.password is None
    
    def test_init_with_custom_parameters(self):
        messenger = MQMessenger(
            host="test.rabbitmq.com",
            port=5673,
            queue_name="custom_queue",
            username="test_user",
            password="test_pass"
        )
        assert messenger.host == "test.rabbitmq.com"
        assert messenger.port == 5673
        assert messenger.queue_name == "custom_queue"
        assert messenger.username == "test_user"
        assert messenger.password == "test_pass"
    
    @patch("pika.BlockingConnection")
    def test_init_with_connect_on_init(self, mock_connection):
        mock_conn = Mock()
        mock_channel = Mock()
        mock_conn.channel.return_value = mock_channel
        mock_connection.return_value = mock_conn
        
        messenger = MQMessenger(connect_on_init=True)
        
        mock_connection.assert_called_once()
        mock_channel.queue_declare.assert_called_once_with(queue="tweet_events", durable=True)
        assert messenger._connection == mock_conn
        assert messenger._channel == mock_channel
    
    @patch.dict("os.environ", {
        "RABBITMQ_HOST": "env.rabbitmq.com",
        "RABBITMQ_PORT": "5674",
        "RABBITMQ_QUEUE": "env_queue",
        "RABBITMQ_USERNAME": "env_user",
        "RABBITMQ_PASSWORD": "env_pass"
    })
    def test_from_env(self):
        messenger = MQMessenger.from_env()
        assert messenger.host == "env.rabbitmq.com"
        assert messenger.port == 5674
        assert messenger.queue_name == "env_queue"
        assert messenger.username == "env_user"
        assert messenger.password == "env_pass"
    
    @patch.dict("os.environ", {}, clear=True)
    def test_from_env_with_defaults(self):
        messenger = MQMessenger.from_env()
        assert messenger.host == "localhost"
        assert messenger.port == 5672
        assert messenger.queue_name == "tweet_events"
        assert messenger.username is None
        assert messenger.password is None
    
    @patch("pika.BlockingConnection")
    @patch.dict("os.environ", {"RABBITMQ_HOST": "test.host"})
    def test_from_env_with_connect_on_init(self, mock_connection):
        mock_conn = Mock()
        mock_channel = Mock()
        mock_conn.channel.return_value = mock_channel
        mock_connection.return_value = mock_conn
        
        messenger = MQMessenger.from_env(connect_on_init=True)
        
        assert messenger.host == "test.host"
        mock_connection.assert_called_once()
        mock_channel.queue_declare.assert_called_once()


class TestMQMessengerConnection:
    """Test MQMessenger connection management."""
    
    @patch("pika.BlockingConnection")
    def test_create_connection_without_auth(self, mock_connection):
        mock_conn = Mock()
        mock_channel = Mock()
        mock_conn.channel.return_value = mock_channel
        mock_connection.return_value = mock_conn
        
        messenger = MQMessenger()
        messenger._create_connection()
        
        mock_connection.assert_called_once()
        mock_conn.channel.assert_called_once()
        mock_channel.queue_declare.assert_called_once_with(queue="tweet_events", durable=True)
        assert messenger._connection == mock_conn
        assert messenger._channel == mock_channel
    
    @patch("pika.BlockingConnection")
    @patch("pika.PlainCredentials")
    @patch("pika.ConnectionParameters")
    def test_create_connection_with_auth(self, mock_connection_params, mock_credentials, mock_connection):
        mock_conn = Mock()
        mock_channel = Mock()
        mock_conn.channel.return_value = mock_channel
        mock_connection.return_value = mock_conn
        mock_creds = Mock()
        mock_credentials.return_value = mock_creds
        mock_params = Mock()
        mock_connection_params.return_value = mock_params
        
        messenger = MQMessenger(username="user", password="pass")
        messenger._create_connection()
        
        mock_credentials.assert_called_once_with("user", "pass")
        mock_connection_params.assert_called_once_with(
            host="localhost",
            port=5672,
            credentials=mock_creds
        )
        mock_connection.assert_called_once_with(mock_params)
        assert messenger._connection == mock_conn
        assert messenger._channel == mock_channel
    
    @patch("pika.BlockingConnection")
    def test_create_connection_failure(self, mock_connection):
        mock_connection.side_effect = Exception("Connection failed")
        
        messenger = MQMessenger()
        with pytest.raises(Exception, match="Connection failed"):
            messenger._create_connection()
        
        assert messenger._connection is None
        assert messenger._channel is None
    
    def test_cleanup_connection(self):
        messenger = MQMessenger()
        mock_channel = Mock()
        mock_connection = Mock()
        mock_channel.is_closed = False
        mock_connection.is_closed = False
        
        messenger._channel = mock_channel
        messenger._connection = mock_connection
        
        messenger._cleanup_connection()
        
        mock_channel.close.assert_called_once()
        mock_connection.close.assert_called_once()
        assert messenger._channel is None
        assert messenger._connection is None
    
    def test_cleanup_connection_with_closed_resources(self):
        messenger = MQMessenger()
        mock_channel = Mock()
        mock_connection = Mock()
        mock_channel.is_closed = True
        mock_connection.is_closed = True
        
        messenger._channel = mock_channel
        messenger._connection = mock_connection
        
        messenger._cleanup_connection()
        
        mock_channel.close.assert_not_called()
        mock_connection.close.assert_not_called()
        assert messenger._channel is None
        assert messenger._connection is None


class TestMQMessengerPublish:
    """Test MQMessenger message publishing functionality."""
    
    @patch("pika.BlockingConnection")
    def test_publish_success(self, mock_connection):
        mock_conn = Mock()
        mock_channel = Mock()
        mock_conn.channel.return_value = mock_channel
        mock_conn.is_closed = False
        mock_channel.is_closed = False
        mock_connection.return_value = mock_conn
        
        messenger = MQMessenger()
        messenger._connection = mock_conn
        messenger._channel = mock_channel
        
        test_message = {"event_type": "tweet", "data": "test"}
        result = messenger.publish(test_message)
        
        assert result is True
        mock_channel.basic_publish.assert_called_once()
        call_args = mock_channel.basic_publish.call_args
        assert call_args[1]["exchange"] == ""
        assert call_args[1]["routing_key"] == "tweet_events"
        assert json.loads(call_args[1]["body"]) == test_message
        assert call_args[1]["properties"].delivery_mode == 2
    
    @patch("pika.BlockingConnection")
    def test_publish_with_connection_creation(self, mock_connection):
        mock_conn = Mock()
        mock_channel = Mock()
        mock_conn.channel.return_value = mock_channel
        mock_conn.is_closed = False
        mock_channel.is_closed = False
        mock_connection.return_value = mock_conn
        
        messenger = MQMessenger()
        test_message = {"event_type": "tweet", "data": "test"}
        result = messenger.publish(test_message)
        
        assert result is True
        mock_connection.assert_called_once()
        mock_channel.queue_declare.assert_called_once_with(queue="tweet_events", durable=True)
        mock_channel.basic_publish.assert_called_once()
    
    @patch("pika.BlockingConnection")
    def test_publish_failure(self, mock_connection):
        mock_connection.side_effect = Exception("Publish failed")
        
        messenger = MQMessenger()
        test_message = {"event_type": "tweet", "data": "test"}
        result = messenger.publish(test_message)
        
        assert result is False
    
    def test_is_connected_true(self):
        messenger = MQMessenger()
        mock_conn = Mock()
        mock_channel = Mock()
        mock_conn.is_closed = False
        mock_channel.is_closed = False
        
        messenger._connection = mock_conn
        messenger._channel = mock_channel
        
        assert messenger.is_connected() is True
    
    def test_is_connected_false_no_connection(self):
        messenger = MQMessenger()
        assert messenger.is_connected() is False
    
    def test_is_connected_false_closed_connection(self):
        messenger = MQMessenger()
        mock_conn = Mock()
        mock_channel = Mock()
        mock_conn.is_closed = True
        mock_channel.is_closed = False
        
        messenger._connection = mock_conn
        messenger._channel = mock_channel
        
        assert messenger.is_connected() is False
    
    def test_publish_validation_invalid_type(self):
        """Test publish raises ValueError for non-dict message."""
        messenger = MQMessenger()
        
        with pytest.raises(ValueError, match="Message must be a dictionary"):
            messenger.publish("not a dict")
        
        with pytest.raises(ValueError, match="Message must be a dictionary"):
            messenger.publish(123)
        
        with pytest.raises(ValueError, match="Message must be a dictionary"):
            messenger.publish(None)
    
    def test_publish_validation_empty_message(self):
        """Test publish raises ValueError for empty message."""
        messenger = MQMessenger()
        
        with pytest.raises(ValueError, match="Message cannot be empty"):
            messenger.publish({})
    
    @patch("pika.BlockingConnection")
    def test_publish_validation_message_too_large(self, mock_connection):
        """Test publish raises ValueError for message exceeding size limit."""
        mock_conn = Mock()
        mock_channel = Mock()
        mock_conn.channel.return_value = mock_channel
        mock_conn.is_closed = False
        mock_channel.is_closed = False
        mock_connection.return_value = mock_conn
        
        messenger = MQMessenger()
        
        # Create a message that's too large (> 1MB)
        large_data = "x" * (1024 * 1024 + 1)  # Just over 1MB
        large_message = {"data": large_data}
        
        with pytest.raises(ValueError, match="Message too large"):
            messenger.publish(large_message)


class TestMQMessengerContextManager:
    """Test MQMessenger context manager functionality."""
    
    def test_context_manager(self):
        with patch.object(MQMessenger, 'close') as mock_close:
            with MQMessenger() as messenger:
                assert isinstance(messenger, MQMessenger)
            mock_close.assert_called_once()
    
    def test_close_calls_cleanup(self):
        messenger = MQMessenger()
        with patch.object(messenger, '_cleanup_connection') as mock_cleanup:
            messenger.close()
            mock_cleanup.assert_called_once()


class TestMQMessengerConnectionMethods:
    """Test new connection methods."""
    
    @patch("pika.BlockingConnection")
    def test_connect_method(self, mock_connection):
        mock_conn = Mock()
        mock_channel = Mock()
        mock_conn.channel.return_value = mock_channel
        mock_conn.is_closed = False
        mock_channel.is_closed = False
        mock_connection.return_value = mock_conn
        
        messenger = MQMessenger()
        messenger.connect()
        
        mock_connection.assert_called_once()
        mock_channel.queue_declare.assert_called_once_with(queue="tweet_events", durable=True)
        assert messenger._connection == mock_conn
        assert messenger._channel == mock_channel
    
    @patch("pika.BlockingConnection")
    def test_test_connection_success(self, mock_connection):
        mock_conn = Mock()
        mock_channel = Mock()
        mock_conn.channel.return_value = mock_channel
        mock_conn.is_closed = False
        mock_channel.is_closed = False
        mock_connection.return_value = mock_conn
        
        messenger = MQMessenger()
        result = messenger.test_connection()
        
        assert result is True
        mock_channel.basic_publish.assert_called_once()
        call_args = mock_channel.basic_publish.call_args
        assert call_args[1]["routing_key"] == "tweet_events"
        assert '"_test": "connection_validation"' in call_args[1]["body"]
    
    @patch("pika.BlockingConnection")
    def test_test_connection_failure(self, mock_connection):
        mock_connection.side_effect = Exception("Connection failed")
        
        messenger = MQMessenger()
        result = messenger.test_connection()
        
        assert result is False