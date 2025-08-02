"""Unit tests for MQSubscriber class."""

import json
import pytest
from unittest.mock import Mock, patch, MagicMock
import pika
from src.core.mq_subscriber import MQSubscriber
from src.core.message_buffer import MessageBuffer


class TestMQSubscriberInitialization:
    """Test MQSubscriber initialization and configuration."""
    
    def test_init_with_default_parameters(self):
        messenger = MQSubscriber()
        assert messenger.host == "localhost"
        assert messenger.port == 5672
        assert messenger.queue_name == "tweet_events"
        assert messenger.username is None
        assert messenger.password is None
    
    def test_init_with_custom_parameters(self):
        messenger = MQSubscriber(
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
        
        messenger = MQSubscriber(connect_on_init=True)
        
        mock_connection.assert_called_once()
        mock_channel.queue_declare.assert_called_once_with(queue="tweet_events", durable=True)
        assert messenger._publisher_connection == mock_conn
        assert messenger._publisher_channel == mock_channel
    
    @patch.dict("os.environ", {
        "RABBITMQ_HOST": "env.rabbitmq.com",
        "RABBITMQ_PORT": "5674",
        "RABBITMQ_QUEUE": "env_queue",
        "RABBITMQ_USERNAME": "env_user",
        "RABBITMQ_PASSWORD": "env_pass"
    })
    def test_from_env(self):
        messenger = MQSubscriber.from_env()
        assert messenger.host == "env.rabbitmq.com"
        assert messenger.port == 5674
        assert messenger.queue_name == "env_queue"
        assert messenger.username == "env_user"
        assert messenger.password == "env_pass"
    
    @patch.dict("os.environ", {}, clear=True)
    def test_from_env_with_defaults(self):
        messenger = MQSubscriber.from_env()
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
        
        messenger = MQSubscriber.from_env(connect_on_init=True)
        
        assert messenger.host == "test.host"
        mock_connection.assert_called_once()
        mock_channel.queue_declare.assert_called_once()


class TestMQSubscriberConnection:
    """Test MQSubscriber connection management."""
    
    @patch("pika.BlockingConnection")
    def test_create_connection_without_auth(self, mock_connection):
        mock_conn = Mock()
        mock_channel = Mock()
        mock_conn.channel.return_value = mock_channel
        mock_connection.return_value = mock_conn
        
        messenger = MQSubscriber()
        messenger._create_publisher_connection()
        
        mock_connection.assert_called_once()
        mock_conn.channel.assert_called_once()
        mock_channel.queue_declare.assert_called_once_with(queue="tweet_events", durable=True)
        assert messenger._publisher_connection == mock_conn
        assert messenger._publisher_channel == mock_channel
    
    @patch("pika.BlockingConnection") 
    def test_create_connection_with_auth(self, mock_connection):
        mock_conn = Mock()
        mock_channel = Mock()
        mock_conn.channel.return_value = mock_channel
        mock_connection.return_value = mock_conn
        
        messenger = MQSubscriber(username="user", password="pass")
        messenger._create_publisher_connection()
        
        # Verify connection was created with proper parameters
        mock_connection.assert_called_once()
        assert messenger._publisher_connection == mock_conn
        assert messenger._publisher_channel == mock_channel
    
    @patch("pika.BlockingConnection")
    def test_create_connection_failure(self, mock_connection):
        mock_connection.side_effect = Exception("Connection failed")
        
        messenger = MQSubscriber()
        with pytest.raises(Exception, match="Connection failed"):
            messenger._create_publisher_connection()
        
        assert messenger._publisher_connection is None
        assert messenger._publisher_channel is None
    
    def test_cleanup_connection(self):
        messenger = MQSubscriber()
        # Mock publisher connection
        mock_pub_channel = Mock()
        mock_pub_connection = Mock()
        mock_pub_channel.is_closed = False
        mock_pub_connection.is_closed = False
        
        # Mock consumer connection
        mock_cons_channel = Mock()  
        mock_cons_connection = Mock()
        mock_cons_channel.is_closed = False
        mock_cons_connection.is_closed = False
        
        messenger._publisher_channel = mock_pub_channel
        messenger._publisher_connection = mock_pub_connection
        messenger._consumer_channel = mock_cons_channel
        messenger._consumer_connection = mock_cons_connection
        
        messenger._cleanup_connection()
        
        # Verify both connections are cleaned up
        mock_pub_channel.close.assert_called_once()
        mock_pub_connection.close.assert_called_once()
        mock_cons_channel.close.assert_called_once()
        mock_cons_connection.close.assert_called_once()
        assert messenger._publisher_channel is None
        assert messenger._publisher_connection is None
        assert messenger._consumer_channel is None
        assert messenger._consumer_connection is None
    
    def test_cleanup_connection_with_closed_resources(self):
        messenger = MQSubscriber()
        # Mock already closed connections
        mock_pub_channel = Mock()
        mock_pub_connection = Mock()
        mock_pub_channel.is_closed = True
        mock_pub_connection.is_closed = True
        
        mock_cons_channel = Mock()
        mock_cons_connection = Mock()
        mock_cons_channel.is_closed = True
        mock_cons_connection.is_closed = True
        
        messenger._publisher_channel = mock_pub_channel
        messenger._publisher_connection = mock_pub_connection
        messenger._consumer_channel = mock_cons_channel
        messenger._consumer_connection = mock_cons_connection
        
        messenger._cleanup_connection()
        
        # Verify close is not called on already closed connections
        mock_pub_channel.close.assert_not_called()
        mock_pub_connection.close.assert_not_called()
        mock_cons_channel.close.assert_not_called()
        mock_cons_connection.close.assert_not_called()
        assert messenger._publisher_channel is None
        assert messenger._publisher_connection is None
        assert messenger._consumer_channel is None
        assert messenger._consumer_connection is None


class TestMQSubscriberPublish:
    """Test MQSubscriber message publishing functionality."""
    
    @patch("pika.BlockingConnection")
    def test_publish_success(self, mock_connection):
        mock_conn = Mock()
        mock_channel = Mock()
        mock_conn.channel.return_value = mock_channel
        mock_conn.is_closed = False
        mock_channel.is_closed = False
        mock_connection.return_value = mock_conn
        
        messenger = MQSubscriber()
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
            "links": [],
            "sentiment_analysis": None
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
        
        messenger = MQSubscriber()
        test_message = {"text": "test tweet", "timestamp": 1234567890}
        result = messenger.publish(test_message)
        
        assert result is True
        mock_connection.assert_called_once()
        mock_channel.queue_declare.assert_called_once_with(queue="tweet_events", durable=True)
        mock_channel.basic_publish.assert_called_once()
    
    @patch("pika.BlockingConnection")
    def test_publish_failure(self, mock_connection):
        mock_connection.side_effect = Exception("Publish failed")
        
        messenger = MQSubscriber()
        test_message = {"text": "test tweet", "timestamp": 1234567890}
        result = messenger.publish(test_message)
        
        assert result is False
    
    def test_is_connected_true(self):
        messenger = MQSubscriber()
        mock_conn = Mock()
        mock_channel = Mock()
        mock_conn.is_closed = False
        mock_channel.is_closed = False
        
        messenger._publisher_connection = mock_conn
        messenger._publisher_channel = mock_channel
        
        assert messenger.is_connected() is True
    
    def test_is_connected_false_no_connection(self):
        messenger = MQSubscriber()
        assert messenger.is_connected() is False
    
    def test_is_connected_false_closed_connection(self):
        messenger = MQSubscriber()
        mock_conn = Mock()
        mock_channel = Mock()
        mock_conn.is_closed = True
        mock_channel.is_closed = False
        
        messenger._publisher_connection = mock_conn
        messenger._publisher_channel = mock_channel
        
        assert messenger.is_connected() is False
    
    def test_publish_validation_invalid_type(self):
        """Test publish raises ValueError for non-dict message."""
        messenger = MQSubscriber()
        
        with pytest.raises(ValueError, match="Message must be a dictionary"):
            messenger.publish("not a dict")
        
        with pytest.raises(ValueError, match="Message must be a dictionary"):
            messenger.publish(123)
        
        with pytest.raises(ValueError, match="Message must be a dictionary"):
            messenger.publish(None)
    
    def test_publish_validation_empty_message(self):
        """Test publish raises ValueError for empty message."""
        messenger = MQSubscriber()
        
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
        
        messenger = MQSubscriber()
        
        # Create a message that's too large (> 1MB)
        large_data = "x" * (1024 * 1024 + 1)  # Just over 1MB
        large_message = {"text": large_data, "timestamp": 1234567890}
        
        with pytest.raises(ValueError, match="Message too large"):
            messenger.publish(large_message)
    
    def test_publish_validation_schema_error(self):
        """Test publish raises ValueError for message that doesn't match schema."""
        messenger = MQSubscriber()
        
        # Message with invalid field that can't be coerced (missing required structure)
        invalid_message = {"createdAt": "not_a_number"}  # This should fail int conversion
        
        with pytest.raises(ValueError, match="Message does not match expected schema"):
            messenger.publish(invalid_message)
    
    @patch("pika.BlockingConnection")
    def test_publish_with_tweetoutput_object(self, mock_connection):
        """Test publish accepts TweetOutput objects and converts them to dictionaries."""
        from src.models.schemas import TweetOutput
        
        mock_conn = Mock()
        mock_channel = Mock()
        mock_conn.channel.return_value = mock_channel
        mock_conn.is_closed = False
        mock_channel.is_closed = False
        mock_connection.return_value = mock_conn
        
        messenger = MQSubscriber()
        
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


class TestMQSubscriberContextManager:
    """Test MQSubscriber context manager functionality."""
    
    def test_context_manager(self):
        with patch.object(MQSubscriber, 'close') as mock_close:
            with MQSubscriber() as messenger:
                assert isinstance(messenger, MQSubscriber)
            mock_close.assert_called_once()
    
    def test_close_calls_cleanup(self):
        messenger = MQSubscriber()
        with patch.object(messenger, '_cleanup_connection') as mock_cleanup:
            messenger.close()
            mock_cleanup.assert_called_once()


class TestMQSubscriberConnectionMethods:
    """Test new connection methods."""
    
    @patch("pika.BlockingConnection")
    def test_connect_method(self, mock_connection):
        mock_conn = Mock()
        mock_channel = Mock()
        mock_conn.channel.return_value = mock_channel
        mock_conn.is_closed = False
        mock_channel.is_closed = False
        mock_connection.return_value = mock_conn
        
        messenger = MQSubscriber()
        messenger.connect()
        
        mock_connection.assert_called_once()
        mock_channel.queue_declare.assert_called_once_with(queue="tweet_events", durable=True)
        assert messenger._publisher_connection == mock_conn
        assert messenger._publisher_channel == mock_channel
    
    @patch("pika.BlockingConnection")
    def test_test_connection_success(self, mock_connection):
        mock_conn = Mock()
        mock_channel = Mock()
        mock_conn.channel.return_value = mock_channel
        mock_conn.is_closed = False
        mock_channel.is_closed = False
        mock_connection.return_value = mock_conn
        
        messenger = MQSubscriber()
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
        
        messenger = MQSubscriber()
        result = messenger.test_connection()
        
        assert result is False


class TestMQSubscriberBufferIntegration:
    """Test MQSubscriber integration with MessageBuffer."""
    
    def test_initialization_with_default_buffer(self):
        """Test MQSubscriber initializes with default MessageBuffer."""
        with patch('src.core.message_buffer.MessageBuffer.from_env') as mock_from_env:
            mock_buffer = Mock()
            mock_from_env.return_value = mock_buffer
            
            messenger = MQSubscriber()
            
            mock_from_env.assert_called_once()
            assert messenger.message_buffer == mock_buffer
    
    def test_initialization_with_custom_buffer(self):
        """Test MQSubscriber initializes with custom MessageBuffer."""
        custom_buffer = MessageBuffer(max_size=5, enabled=False)
        
        # Test that custom buffer is used correctly
        messenger = MQSubscriber(message_buffer=custom_buffer)
        
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
        messenger = MQSubscriber(message_buffer=mock_buffer)
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
        
        messenger = MQSubscriber(message_buffer=mock_buffer)
        test_message = {"text": "test tweet", "timestamp": 1234567890}
        result = messenger.publish(test_message)
        
        assert result is False
        # Schema validation transforms the message before buffering
        expected_message = {
            "data_source": {"name": "", "author_name": "", "author_id": ""},
            "createdAt": 0,  # timestamp gets converted to createdAt and defaults to 0 if not provided
            "text": "test tweet", 
            "media": [], 
            "links": [],
            "sentiment_analysis": None
        }
        mock_buffer.add_message.assert_called_once_with(expected_message)
    
    @patch("pika.BlockingConnection")
    def test_publish_failure_buffer_disabled(self, mock_connection):
        """Test failed publish with disabled buffer."""
        mock_connection.side_effect = Exception("Connection failed")
        
        mock_buffer = Mock()
        mock_buffer.add_message.return_value = False
        mock_buffer.enabled = False
        
        messenger = MQSubscriber(message_buffer=mock_buffer)
        test_message = {"text": "test tweet", "timestamp": 1234567890}
        result = messenger.publish(test_message)
        
        assert result is False
        # Schema validation transforms the message before buffering
        expected_message = {
            "data_source": {"name": "", "author_name": "", "author_id": ""},
            "createdAt": 0,  # timestamp gets converted to createdAt and defaults to 0 if not provided
            "text": "test tweet", 
            "media": [], 
            "links": [],
            "sentiment_analysis": None
        }
        mock_buffer.add_message.assert_called_once_with(expected_message)
    
    def test_get_buffer_status(self):
        """Test get_buffer_status method delegates to buffer."""
        mock_buffer = Mock()
        mock_status = {"current_size": 3, "max_size": 10, "is_full": False}
        mock_buffer.get_status.return_value = mock_status
        
        messenger = MQSubscriber(message_buffer=mock_buffer)
        status = messenger.get_buffer_status()
        
        assert status == mock_status
        mock_buffer.get_status.assert_called_once()
    
    @patch("pika.BlockingConnection")
    def test_flush_buffer_empty(self, mock_connection):
        """Test flush_buffer with empty buffer."""
        mock_buffer = Mock()
        mock_buffer.is_empty.return_value = True
        
        messenger = MQSubscriber(message_buffer=mock_buffer)
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
        
        messenger = MQSubscriber(message_buffer=buffer)
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
        
        messenger = MQSubscriber(message_buffer=mock_buffer)
        
        with patch('src.core.mq_subscriber.deque') as mock_deque_class:
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
        
        messenger = MQSubscriber(message_buffer=mock_buffer)
        
        with patch('src.core.mq_subscriber.deque') as mock_deque_class:
            mock_temp_buffer = Mock()
            mock_deque_class.return_value = mock_temp_buffer
            
            result = messenger.flush_buffer()
        
        assert result == 0  # No messages flushed due to connection failure
        mock_buffer.pop_message.assert_called_once()


class TestMQSubscriberReconnection:
    """Test MQSubscriber reconnection functionality with buffer integration."""
    
    @patch("pika.BlockingConnection")
    def test_reconnect_method(self, mock_connection):
        """Test reconnect method functionality."""
        mock_conn = Mock()
        mock_channel = Mock()
        mock_conn.channel.return_value = mock_channel
        mock_conn.is_closed = False
        mock_channel.is_closed = False
        mock_connection.return_value = mock_conn
        
        messenger = MQSubscriber()
        
        # Mock existing connection for cleanup
        old_mock_conn = Mock()
        old_mock_channel = Mock()
        messenger._publisher_connection = old_mock_conn
        messenger._publisher_channel = old_mock_channel
        
        with patch.object(messenger, '_cleanup_connection') as mock_cleanup:
            result = messenger.reconnect()
        
        assert result is True
        mock_cleanup.assert_called_once()
        mock_connection.assert_called_once()
        assert messenger._publisher_connection == mock_conn
        assert messenger._publisher_channel == mock_channel
    
    @patch("pika.BlockingConnection")
    def test_reconnect_failure(self, mock_connection):
        """Test reconnect method handles failures gracefully."""
        mock_connection.side_effect = Exception("Reconnection failed")
        
        messenger = MQSubscriber()
        result = messenger.reconnect()
        
        assert result is False
        assert messenger._publisher_connection is None
        assert messenger._publisher_channel is None


class TestMQSubscriberConsumerRestart:
    """Test MQSubscriber consumer restart functionality after reconnection."""
    
    @patch("pika.BlockingConnection")
    def test_reconnect_restarts_consumer_when_was_consuming(self, mock_connection):
        """Test that reconnect restarts consumer if it was running before."""
        mock_conn = Mock()
        mock_channel = Mock()
        mock_conn.channel.return_value = mock_channel
        mock_conn.is_closed = False
        mock_channel.is_closed = False
        mock_connection.return_value = mock_conn
        
        messenger = MQSubscriber()
        messenger.set_message_handler(Mock())
        
        # Mock consumer as running before reconnection
        with patch.object(messenger, 'is_consuming', side_effect=[True, True]) as mock_is_consuming:
            with patch.object(messenger, 'stop_consuming') as mock_stop:
                with patch.object(messenger, 'start_consuming') as mock_start:
                    result = messenger.reconnect()
        
        assert result is True
        mock_stop.assert_called_once()
        mock_start.assert_called_once()
    
    @patch("pika.BlockingConnection")
    def test_reconnect_does_not_restart_consumer_when_not_consuming(self, mock_connection):
        """Test that reconnect doesn't restart consumer if it wasn't running."""
        mock_conn = Mock()
        mock_channel = Mock()
        mock_conn.channel.return_value = mock_channel
        mock_conn.is_closed = False
        mock_channel.is_closed = False
        mock_connection.return_value = mock_conn
        
        messenger = MQSubscriber()
        
        # Mock consumer as not running before reconnection
        with patch.object(messenger, 'is_consuming', return_value=False):
            with patch.object(messenger, 'stop_consuming') as mock_stop:
                with patch.object(messenger, 'start_consuming') as mock_start:
                    result = messenger.reconnect()
        
        assert result is True
        mock_stop.assert_not_called()
        mock_start.assert_not_called()
    
    @patch("pika.BlockingConnection")
    def test_reconnect_handles_consumer_restart_failure(self, mock_connection):
        """Test that reconnect handles consumer restart failures gracefully."""
        mock_conn = Mock()
        mock_channel = Mock()
        mock_conn.channel.return_value = mock_channel
        mock_conn.is_closed = False
        mock_channel.is_closed = False
        mock_connection.return_value = mock_conn
        
        messenger = MQSubscriber()
        messenger.set_message_handler(Mock())
        
        # Mock consumer as running before reconnection, but start_consuming fails
        with patch.object(messenger, 'is_consuming', side_effect=[True, False]) as mock_is_consuming:
            with patch.object(messenger, 'stop_consuming') as mock_stop:
                with patch.object(messenger, 'start_consuming', side_effect=Exception("Consumer start failed")) as mock_start:
                    result = messenger.reconnect()
        
        assert result is False
        mock_stop.assert_called_once()
        mock_start.assert_called_once()
    
    @patch("pika.BlockingConnection")
    def test_reconnect_without_message_handler_skips_consumer_restart(self, mock_connection):
        """Test that reconnect skips consumer restart if no message handler is set."""
        mock_conn = Mock()
        mock_channel = Mock()
        mock_conn.channel.return_value = mock_channel
        mock_conn.is_closed = False
        mock_channel.is_closed = False
        mock_connection.return_value = mock_conn
        
        messenger = MQSubscriber()
        # No message handler set
        
        # Mock consumer as running before reconnection
        with patch.object(messenger, 'is_consuming', return_value=True):
            with patch.object(messenger, 'stop_consuming') as mock_stop:
                with patch.object(messenger, 'start_consuming') as mock_start:
                    result = messenger.reconnect()
        
        assert result is True
        mock_stop.assert_called_once()
        mock_start.assert_not_called()  # Should not restart without handler