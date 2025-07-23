"""Unit tests for MQMessenger class."""

import json
import pytest
from unittest.mock import Mock, patch, MagicMock
import pika
from mq_messenger import MQMessenger
from message_buffer import MessageBuffer


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
        
        test_message = {"text": "test tweet", "timestamp": 1234567890}
        result = messenger.publish(test_message)
        
        assert result is True
        mock_channel.basic_publish.assert_called_once()
        call_args = mock_channel.basic_publish.call_args
        assert call_args[1]["exchange"] == ""
        assert call_args[1]["routing_key"] == "tweet_events"
        # Schema validation transforms the message before publishing
        expected_message = {
            "data_source": {"name": "", "author_name": "", "author_id": ""},
            "createdAt": 0,  # timestamp gets converted to createdAt and defaults to 0 if not provided
            "text": "test tweet", 
            "media": [], 
            "links": []
        }
        assert json.loads(call_args[1]["body"]) == expected_message
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
        test_message = {"text": "test tweet", "timestamp": 1234567890}
        result = messenger.publish(test_message)
        
        assert result is True
        mock_connection.assert_called_once()
        mock_channel.queue_declare.assert_called_once_with(queue="tweet_events", durable=True)
        mock_channel.basic_publish.assert_called_once()
    
    @patch("pika.BlockingConnection")
    def test_publish_failure(self, mock_connection):
        mock_connection.side_effect = Exception("Publish failed")
        
        messenger = MQMessenger()
        test_message = {"text": "test tweet", "timestamp": 1234567890}
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
        large_message = {"text": large_data, "timestamp": 1234567890}
        
        with pytest.raises(ValueError, match="Message too large"):
            messenger.publish(large_message)
    
    def test_publish_validation_schema_error(self):
        """Test publish raises ValueError for message that doesn't match schema."""
        messenger = MQMessenger()
        
        # Message with invalid field type (text should be string)
        invalid_message = {"text": 123, "timestamp": "invalid"}
        
        with pytest.raises(ValueError, match="Message does not match expected schema"):
            messenger.publish(invalid_message)
    
    @patch("pika.BlockingConnection")
    def test_publish_with_tweetoutput_object(self, mock_connection):
        """Test publish accepts TweetOutput objects and converts them to dictionaries."""
        from schemas import TweetOutput
        
        mock_conn = Mock()
        mock_channel = Mock()
        mock_conn.channel.return_value = mock_channel
        mock_conn.is_closed = False
        mock_channel.is_closed = False
        mock_connection.return_value = mock_conn
        
        messenger = MQMessenger()
        
        # Create a TweetOutput object
        tweet_output = TweetOutput(
            createdAt=1642743600,
            text="Test tweet content",
            media=["https://example.com/image.jpg"],
            links=["https://example.com/article"]
        )
        
        # Should successfully publish without validation errors
        result = messenger.publish(tweet_output)
        
        assert result is True
        mock_channel.basic_publish.assert_called_once()
        
        # Verify the published message was converted to dictionary format
        call_args = mock_channel.basic_publish.call_args
        published_body = call_args[1]['body']
        import json
        published_data = json.loads(published_body)
        
        assert published_data['createdAt'] == 1642743600
        assert published_data['text'] == "Test tweet content"
        assert published_data['media'] == ["https://example.com/image.jpg"]
        assert published_data['links'] == ["https://example.com/article"]
        # Also verify data_source field is present
        assert 'data_source' in published_data
        assert published_data['data_source'] == {"name": "", "author_name": "", "author_id": ""}


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
        # Verify that connection_events queue is declared
        mock_channel.queue_declare.assert_any_call(queue="connection_events", durable=True)
        mock_channel.basic_publish.assert_called_once()
        call_args = mock_channel.basic_publish.call_args
        assert call_args[1]["routing_key"] == "connection_events"
        assert '"_test": "connection_validation"' in call_args[1]["body"]
    
    @patch("pika.BlockingConnection")
    def test_test_connection_failure(self, mock_connection):
        mock_connection.side_effect = Exception("Connection failed")
        
        messenger = MQMessenger()
        result = messenger.test_connection()
        
        assert result is False


class TestMQMessengerBufferIntegration:
    """Test MQMessenger integration with MessageBuffer."""
    
    def test_initialization_with_default_buffer(self):
        """Test MQMessenger initializes with default MessageBuffer."""
        with patch('message_buffer.MessageBuffer.from_env') as mock_from_env:
            mock_buffer = Mock()
            mock_from_env.return_value = mock_buffer
            
            messenger = MQMessenger()
            
            mock_from_env.assert_called_once()
            assert messenger.message_buffer == mock_buffer
    
    def test_initialization_with_custom_buffer(self):
        """Test MQMessenger initializes with custom MessageBuffer."""
        custom_buffer = MessageBuffer(max_size=5, enabled=False)
        
        # Test that custom buffer is used correctly
        messenger = MQMessenger(message_buffer=custom_buffer)
        
        assert messenger.message_buffer == custom_buffer
        assert messenger.message_buffer.max_size == 5
        assert messenger.message_buffer.enabled is False
    
    @patch("pika.BlockingConnection")
    def test_publish_success_no_buffering(self, mock_connection):
        """Test successful publish doesn't use buffer."""
        mock_conn = Mock()
        mock_channel = Mock()
        mock_conn.channel.return_value = mock_channel
        mock_conn.is_closed = False
        mock_channel.is_closed = False
        mock_connection.return_value = mock_conn
        
        mock_buffer = Mock()
        messenger = MQMessenger(message_buffer=mock_buffer)
        messenger._connection = mock_conn
        messenger._channel = mock_channel
        
        test_message = {"text": "test tweet", "timestamp": 1234567890}
        result = messenger.publish(test_message)
        
        assert result is True
        mock_channel.basic_publish.assert_called_once()
        mock_buffer.add_message.assert_not_called()
    
    @patch("pika.BlockingConnection")
    def test_publish_failure_buffers_message(self, mock_connection):
        """Test failed publish attempts to buffer message."""
        mock_connection.side_effect = Exception("Connection failed")
        
        mock_buffer = Mock()
        mock_buffer.add_message.return_value = True
        mock_buffer.size.return_value = 1
        mock_buffer.max_size = 10
        
        messenger = MQMessenger(message_buffer=mock_buffer)
        test_message = {"text": "test tweet", "timestamp": 1234567890}
        result = messenger.publish(test_message)
        
        assert result is False
        # Schema validation transforms the message before buffering
        expected_message = {
            "data_source": {"name": "", "author_name": "", "author_id": ""},
            "createdAt": 0,  # timestamp gets converted to createdAt and defaults to 0 if not provided
            "text": "test tweet", 
            "media": [], 
            "links": []
        }
        mock_buffer.add_message.assert_called_once_with(expected_message)
    
    @patch("pika.BlockingConnection")
    def test_publish_failure_buffer_disabled(self, mock_connection):
        """Test failed publish with disabled buffer."""
        mock_connection.side_effect = Exception("Connection failed")
        
        mock_buffer = Mock()
        mock_buffer.add_message.return_value = False
        mock_buffer.enabled = False
        
        messenger = MQMessenger(message_buffer=mock_buffer)
        test_message = {"text": "test tweet", "timestamp": 1234567890}
        result = messenger.publish(test_message)
        
        assert result is False
        # Schema validation transforms the message before buffering
        expected_message = {
            "data_source": {"name": "", "author_name": "", "author_id": ""},
            "createdAt": 0,  # timestamp gets converted to createdAt and defaults to 0 if not provided
            "text": "test tweet", 
            "media": [], 
            "links": []
        }
        mock_buffer.add_message.assert_called_once_with(expected_message)
    
    def test_get_buffer_status(self):
        """Test get_buffer_status method delegates to buffer."""
        mock_buffer = Mock()
        mock_status = {"current_size": 3, "max_size": 10, "is_full": False}
        mock_buffer.get_status.return_value = mock_status
        
        messenger = MQMessenger(message_buffer=mock_buffer)
        status = messenger.get_buffer_status()
        
        assert status == mock_status
        mock_buffer.get_status.assert_called_once()
    
    @patch("pika.BlockingConnection")
    def test_flush_buffer_empty(self, mock_connection):
        """Test flush_buffer with empty buffer."""
        mock_buffer = Mock()
        mock_buffer.is_empty.return_value = True
        
        messenger = MQMessenger(message_buffer=mock_buffer)
        result = messenger.flush_buffer()
        
        assert result == 0
        mock_buffer.is_empty.assert_called_once()
        mock_buffer.pop_message.assert_not_called()
    
    @patch("pika.BlockingConnection")
    def test_flush_buffer_success(self, mock_connection):
        """Test successful buffer flush."""
        mock_conn = Mock()
        mock_channel = Mock()
        mock_conn.channel.return_value = mock_channel
        mock_conn.is_closed = False
        mock_channel.is_closed = False
        mock_connection.return_value = mock_conn
        
        # Use a real MessageBuffer with actual messages for more accurate testing
        buffer = MessageBuffer(max_size=10, enabled=True)
        message1 = {"event_type": "tweet", "id": 1}
        message2 = {"event_type": "tweet", "id": 2}
        
        # Add messages to buffer
        buffer.add_message(message1)
        buffer.add_message(message2)
        
        messenger = MQMessenger(message_buffer=buffer)
        result = messenger.flush_buffer()
        
        assert result == 2
        assert mock_channel.basic_publish.call_count == 2
        assert buffer.is_empty() is True
    
    @patch("pika.BlockingConnection")
    def test_flush_buffer_partial_failure(self, mock_connection):
        """Test buffer flush with partial failure."""
        # First message succeeds, second fails
        mock_conn = Mock()
        mock_channel = Mock()
        mock_conn.channel.return_value = mock_channel
        mock_conn.is_closed = False
        mock_channel.is_closed = False
        mock_connection.return_value = mock_conn
        
        # Make second publish fail
        mock_channel.basic_publish.side_effect = [None, Exception("Publish failed")]
        
        mock_buffer = Mock()
        mock_buffer.is_empty.side_effect = [False, False, False]  # Never becomes empty in this test
        mock_buffer.size.return_value = 2
        mock_buffer._buffer = Mock()  # Mock the internal buffer for re-adding failed message
        
        message1 = {"message": {"id": 1}, "timestamp": 1234567890.0, "buffer_sequence": 1}
        message2 = {"message": {"id": 2}, "timestamp": 1234567891.0, "buffer_sequence": 2}
        mock_buffer.pop_message.side_effect = [message1, message2]
        
        messenger = MQMessenger(message_buffer=mock_buffer)
        
        with patch('mq_messenger.deque') as mock_deque_class:
            mock_temp_buffer = Mock()
            mock_deque_class.return_value = mock_temp_buffer
            
            result = messenger.flush_buffer()
        
        assert result == 1  # Only first message flushed successfully
        assert mock_channel.basic_publish.call_count == 2
        assert mock_buffer.pop_message.call_count == 2
    
    @patch("pika.BlockingConnection") 
    def test_flush_buffer_connection_failure(self, mock_connection):
        """Test flush_buffer handles connection failures gracefully."""
        mock_connection.side_effect = Exception("Connection failed")
        
        mock_buffer = Mock()
        mock_buffer.is_empty.return_value = False
        mock_buffer.size.return_value = 1
        mock_buffer.pop_message.return_value = {
            "message": {"id": 1}, 
            "timestamp": 1234567890.0, 
            "buffer_sequence": 1
        }
        mock_buffer._buffer = Mock()
        
        messenger = MQMessenger(message_buffer=mock_buffer)
        
        with patch('mq_messenger.deque') as mock_deque_class:
            mock_temp_buffer = Mock()
            mock_deque_class.return_value = mock_temp_buffer
            
            result = messenger.flush_buffer()
        
        assert result == 0  # No messages flushed due to connection failure
        mock_buffer.pop_message.assert_called_once()


class TestMQMessengerReconnection:
    """Test MQMessenger reconnection functionality with buffer integration."""
    
    @patch("pika.BlockingConnection")
    def test_reconnect_method(self, mock_connection):
        """Test reconnect method functionality."""
        mock_conn = Mock()
        mock_channel = Mock()
        mock_conn.channel.return_value = mock_channel
        mock_conn.is_closed = False
        mock_channel.is_closed = False
        mock_connection.return_value = mock_conn
        
        messenger = MQMessenger()
        
        # Mock existing connection for cleanup
        old_mock_conn = Mock()
        old_mock_channel = Mock()
        messenger._connection = old_mock_conn
        messenger._channel = old_mock_channel
        
        with patch.object(messenger, '_cleanup_connection') as mock_cleanup:
            result = messenger.reconnect()
        
        assert result is True
        mock_cleanup.assert_called_once()
        mock_connection.assert_called_once()
        assert messenger._connection == mock_conn
        assert messenger._channel == mock_channel
    
    @patch("pika.BlockingConnection")
    def test_reconnect_failure(self, mock_connection):
        """Test reconnect method handles failures gracefully."""
        mock_connection.side_effect = Exception("Reconnection failed")
        
        messenger = MQMessenger()
        result = messenger.reconnect()
        
        assert result is False
        assert messenger._connection is None
        assert messenger._channel is None