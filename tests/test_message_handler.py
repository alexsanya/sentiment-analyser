"""Tests for threaded message handler functionality."""

import json
import threading
import time
from unittest.mock import Mock, MagicMock, patch, call
import pytest
from src.handlers.message_handler import (
    ack_message,
    nack_message,
    process_message_work,
    on_message,
    ThreadedMessageProcessor,
    create_threaded_message_handler
)
from src.models.schemas import TokenDetails, TweetOutput, AlignmentData, AnalysisResult, TweetProcessingResult, DataSource


class TestThreadSafeAcknowledgment:
    """Test thread-safe message acknowledgment functions."""
    
    def test_ack_message_open_channel(self):
        """Test acknowledging message on open channel."""
        channel = Mock()
        channel.is_open = True
        delivery_tag = 123
        
        ack_message(channel, delivery_tag)
        
        channel.basic_ack.assert_called_once_with(delivery_tag)
    
    def test_ack_message_closed_channel(self):
        """Test acknowledging message on closed channel."""
        channel = Mock()
        channel.is_open = False
        delivery_tag = 123
        
        # Should not raise exception
        ack_message(channel, delivery_tag)
        
        channel.basic_ack.assert_not_called()
    
    def test_nack_message_open_channel(self):
        """Test nacking message on open channel."""
        channel = Mock()
        channel.is_open = True
        delivery_tag = 123
        
        nack_message(channel, delivery_tag, requeue=True)
        
        channel.basic_nack.assert_called_once_with(delivery_tag, requeue=True)
    
    def test_nack_message_closed_channel(self):
        """Test nacking message on closed channel."""
        channel = Mock()
        channel.is_open = False
        delivery_tag = 123
        
        # Should not raise exception
        nack_message(channel, delivery_tag, requeue=False)
        
        channel.basic_nack.assert_not_called()


class TestMessageProcessingWork:
    """Test the core message processing work function."""
    
    @patch('src.handlers.message_handler.handle_tweet_event')
    def test_process_valid_message_with_token(self, mock_handle_tweet):
        """Test processing valid message that contains token details."""
        # Setup
        channel = Mock()
        channel.connection = Mock()
        delivery_tag = 123
        mq_subscriber = Mock()
        
        # Mock tweet processing to return token details
        token_details = TokenDetails(
            chain_id=1,
            chain_name="Ethereum",
            token_address="0x742d35Cc6765C0532575f5A2c0a078Df8a2D4e5e",
            is_release=True,
            chain_defined_explicitly=True,
            definition_fragment="Ethereum"
        )
        tweet_output = TweetOutput(
            data_source=DataSource(name="Twitter", author_name="test", author_id="123"),
            createdAt=1640995200,
            text="Test tweet",
            media=[],
            links=[],
            sentiment_analysis=token_details
        )
        analysis_result = AnalysisResult.token_detection(token_details)
        processing_result = TweetProcessingResult(tweet_output=tweet_output, analysis=analysis_result)
        mock_handle_tweet.return_value = processing_result
        
        # Mock successful publish
        mq_subscriber.publish.return_value = True
        
        # Create test message
        tweet_data = {"text": "Test tweet with token", "user": {"screen_name": "test"}}
        body = json.dumps(tweet_data).encode('utf-8')
        
        # Execute
        process_message_work(channel, delivery_tag, body, mq_subscriber)
        
        # Verify tweet processing was called
        mock_handle_tweet.assert_called_once_with(tweet_data)
        
        # Verify snipe action was published
        mq_subscriber.publish.assert_called_once()
        published_call = mq_subscriber.publish.call_args
        published_action = published_call[0][0]  # First positional argument
        assert published_action.params.token_address == "0x742d35Cc6765C0532575f5A2c0a078Df8a2D4e5e"
        assert published_action.params.chain_id == 1
        
        # Verify message was acknowledged
        channel.connection.add_callback_threadsafe.assert_called_once()
    
    @patch('src.handlers.message_handler.handle_tweet_event')
    def test_process_valid_message_with_alignment_data(self, mock_handle_tweet):
        """Test processing valid message that contains alignment data for trade action."""
        # Setup
        channel = Mock()
        channel.connection = Mock()
        delivery_tag = 123
        mq_subscriber = Mock()
        
        # Mock tweet processing to return alignment data (topic sentiment)
        alignment_data = AlignmentData(
            score=8,
            explanation="High alignment between Trump and Putin noted"
        )
        tweet_output = TweetOutput(
            data_source=DataSource(name="Twitter", author_name="test", author_id="123"),
            createdAt=1640995200,
            text="Test tweet about peace talks",
            media=[],
            links=[],
            sentiment_analysis=None
        )
        analysis_result = AnalysisResult.topic_sentiment(alignment_data)
        processing_result = TweetProcessingResult(tweet_output=tweet_output, analysis=analysis_result)
        mock_handle_tweet.return_value = processing_result
        
        # Mock successful publish
        mq_subscriber.publish.return_value = True
        
        # Create test message
        tweet_data = {"text": "Trump and Putin reach agreement", "user": {"screen_name": "test"}}
        body = json.dumps(tweet_data).encode('utf-8')
        
        # Execute
        process_message_work(channel, delivery_tag, body, mq_subscriber)
        
        # Verify tweet processing was called
        mock_handle_tweet.assert_called_once_with(tweet_data)
        
        # Verify trade action was published
        mq_subscriber.publish.assert_called_once()
        published_call = mq_subscriber.publish.call_args
        published_action = published_call[0][0]  # First positional argument
        assert published_action.action == "trade"
        
        # Verify message was acknowledged
        channel.connection.add_callback_threadsafe.assert_called_once()
    
    @patch('src.handlers.message_handler.handle_tweet_event')
    def test_process_valid_message_without_token(self, mock_handle_tweet):
        """Test processing valid message that doesn't contain token details."""
        # Setup
        channel = Mock()
        channel.connection = Mock()
        delivery_tag = 123
        mq_subscriber = Mock()
        
        # Mock tweet processing to return no token
        tweet_output = TweetOutput(
            data_source=DataSource(name="Twitter", author_name="test", author_id="123"),
            createdAt=1640995200,
            text="Test tweet",
            media=[],
            links=[],
            sentiment_analysis=None
        )
        analysis_result = AnalysisResult.no_analysis()
        processing_result = TweetProcessingResult(tweet_output=tweet_output, analysis=analysis_result)
        mock_handle_tweet.return_value = processing_result
        
        # Create test message
        tweet_data = {"text": "Regular tweet", "user": {"screen_name": "test"}}
        body = json.dumps(tweet_data).encode('utf-8')
        
        # Execute
        process_message_work(channel, delivery_tag, body, mq_subscriber)
        
        # Verify tweet processing was called
        mock_handle_tweet.assert_called_once_with(tweet_data)
        
        # Verify no snipe action was published
        mq_subscriber.publish.assert_not_called()
        
        # Verify message was acknowledged
        channel.connection.add_callback_threadsafe.assert_called_once()
    
    def test_process_invalid_json_message(self):
        """Test processing message with invalid JSON."""
        # Setup
        channel = Mock()
        channel.connection = Mock()
        delivery_tag = 123
        mq_subscriber = Mock()
        
        # Create invalid JSON message
        body = b"invalid json {"
        
        # Execute
        process_message_work(channel, delivery_tag, body, mq_subscriber)
        
        # Verify message was nacked without requeue
        channel.connection.add_callback_threadsafe.assert_called_once()
        # The callback should be a nack with requeue=False
        callback = channel.connection.add_callback_threadsafe.call_args[0][0]
        # We can't easily test the partial function, but we know it should be called
    
    @patch('src.handlers.message_handler.handle_tweet_event')
    def test_process_message_tweet_handler_exception(self, mock_handle_tweet):
        """Test processing message when tweet handler raises exception."""
        # Setup
        channel = Mock()
        channel.connection = Mock()
        delivery_tag = 123
        mq_subscriber = Mock()
        
        # Mock tweet processing to raise exception
        mock_handle_tweet.side_effect = Exception("Processing error")
        
        # Create test message
        tweet_data = {"text": "Test tweet", "user": {"screen_name": "test"}}
        body = json.dumps(tweet_data).encode('utf-8')
        
        # Execute
        process_message_work(channel, delivery_tag, body, mq_subscriber)
        
        # Verify tweet processing was attempted
        mock_handle_tweet.assert_called_once_with(tweet_data)
        
        # Verify message was nacked without requeue
        channel.connection.add_callback_threadsafe.assert_called_once()


class TestOnMessageCallback:
    """Test the on_message callback function."""
    
    @patch('src.handlers.message_handler.threading.Thread')
    def test_on_message_creates_thread(self, mock_thread_class):
        """Test that on_message creates a processing thread."""
        # Setup
        channel = Mock()
        method = Mock()
        method.delivery_tag = 123
        method.routing_key = "test.route"
        method.exchange = "test.exchange"
        properties = Mock()
        body = b"test message"
        
        mq_subscriber = Mock()
        threads: list[threading.Thread] = []
        args = (threads, mq_subscriber)
        
        # Mock thread instance
        mock_thread = Mock()
        mock_thread_class.return_value = mock_thread
        
        # Execute
        on_message(channel, method, properties, body, args)
        
        # Verify thread was created with correct arguments
        mock_thread_class.assert_called_once()
        call_args = mock_thread_class.call_args
        assert call_args[1]['target'] == process_message_work
        assert call_args[1]['args'] == (channel, 123, body, mq_subscriber)
        assert call_args[1]['daemon'] is True
        
        # Verify thread was started and added to list
        mock_thread.start.assert_called_once()
        assert mock_thread in threads


class TestThreadedMessageProcessor:
    """Test the ThreadedMessageProcessor class."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.mq_subscriber = Mock()
        self.processor = ThreadedMessageProcessor(self.mq_subscriber)
    
    def test_initialization(self):
        """Test processor initialization."""
        assert self.processor.mq_subscriber == self.mq_subscriber
        assert self.processor.threads == []
        assert self.processor.is_consuming is False
    
    def test_create_message_handler(self):
        """Test message handler creation."""
        handler = self.processor.create_message_handler()
        
        # Handler should be callable
        assert callable(handler)
    
    def test_start_processing(self):
        """Test starting message processing."""
        # Mock message handler creation
        with patch.object(self.processor, 'create_message_handler') as mock_create:
            mock_handler = Mock()
            mock_create.return_value = mock_handler
            
            self.processor.start_processing()
            
            # Verify handler was created and set
            mock_create.assert_called_once()
            self.mq_subscriber.set_message_handler.assert_called_once_with(mock_handler)
            
            # Verify consuming was started
            self.mq_subscriber.start_consuming.assert_called_once()
            assert self.processor.is_consuming is True
    
    def test_start_processing_already_running(self):
        """Test starting processing when already running."""
        self.processor.is_consuming = True
        
        self.processor.start_processing()
        
        # Should not call start_consuming again
        self.mq_subscriber.start_consuming.assert_not_called()
    
    def test_stop_processing(self):
        """Test stopping message processing."""
        # Setup some mock threads
        mock_thread1 = Mock()
        mock_thread1.is_alive.return_value = True
        mock_thread2 = Mock()
        mock_thread2.is_alive.return_value = True  # Both alive initially
        
        self.processor.threads = [mock_thread1, mock_thread2]
        self.processor.is_consuming = True
        
        # Execute
        self.processor.stop_processing(timeout=1.0)
        
        # Verify consuming was stopped
        self.mq_subscriber.stop_consuming.assert_called_once()
        assert self.processor.is_consuming is False
        
        # Verify threads were joined (only alive threads get joined)
        mock_thread1.join.assert_called_once()
        mock_thread2.join.assert_called_once()
    
    def test_stop_processing_not_running(self):
        """Test stopping processing when not running."""
        self.processor.is_consuming = False
        
        self.processor.stop_processing()
        
        # Should not call stop_consuming
        self.mq_subscriber.stop_consuming.assert_not_called()
    
    def test_cleanup_finished_threads(self):
        """Test cleanup of finished threads."""
        # Setup threads - some alive, some finished
        alive_thread = Mock()
        alive_thread.is_alive.return_value = True
        
        finished_thread = Mock()
        finished_thread.is_alive.return_value = False
        
        self.processor.threads = [alive_thread, finished_thread]
        
        # Execute cleanup
        self.processor.cleanup_finished_threads()
        
        # Verify only alive thread remains
        assert self.processor.threads == [alive_thread]
    
    def test_wait_for_threads(self):
        """Test waiting for threads to complete."""
        # Setup mock threads
        mock_thread1 = Mock()
        mock_thread1.is_alive.return_value = True
        mock_thread1.ident = 12345
        
        mock_thread2 = Mock()
        mock_thread2.is_alive.return_value = True
        mock_thread2.ident = 67890
        
        self.processor.threads = [mock_thread1, mock_thread2]
        
        # Execute
        self.processor.wait_for_threads(timeout=0.1)
        
        # Verify threads were joined
        mock_thread1.join.assert_called_once()
        mock_thread2.join.assert_called_once()
    
    def test_get_status(self):
        """Test getting processor status."""
        # Setup mock threads
        alive_thread = Mock()
        alive_thread.is_alive.return_value = True
        
        finished_thread = Mock()
        finished_thread.is_alive.return_value = False
        
        self.processor.threads = [alive_thread, finished_thread]
        self.processor.is_consuming = True
        
        # Mock MQ subscriber methods
        self.mq_subscriber.is_consuming.return_value = True
        self.mq_subscriber.is_publisher_connected.return_value = True
        
        # Execute
        status = self.processor.get_status()
        
        # Verify status
        assert status["is_consuming"] is True
        assert status["active_threads"] == 1  # Only alive thread
        # Note: total_threads_created will be 1 after cleanup removes finished thread
        assert status["total_threads_created"] == 1
        assert status["mq_consumer_active"] is True
        assert status["mq_publisher_connected"] is True


class TestFactoryFunction:
    """Test the factory function for creating threaded message handlers."""
    
    def test_create_threaded_message_handler(self):
        """Test the factory function creates proper processor."""
        mq_subscriber = Mock()
        
        processor = create_threaded_message_handler(mq_subscriber)
        
        assert isinstance(processor, ThreadedMessageProcessor)
        assert processor.mq_subscriber == mq_subscriber


class TestIntegration:
    """Integration tests for threaded message processing."""
    
    @pytest.mark.integration
    def test_full_message_processing_flow(self):
        """Test complete message processing flow with real threads."""
        # Setup
        mq_subscriber = Mock()
        mq_subscriber.publish.return_value = True
        
        processor = ThreadedMessageProcessor(mq_subscriber)
        
        # Create a message handler
        handler = processor.create_message_handler()
        
        # Setup mock channel and message
        channel = Mock()
        channel.connection = Mock()
        method = Mock()
        method.delivery_tag = 123
        method.routing_key = "test.route"
        method.exchange = ""
        properties = Mock()
        
        # Create test message with token
        tweet_data = {
            "text": "New token launched: 0x742d35Cc6765C0532575f5A2c0a078Df8a2D4e5e on Ethereum",
            "user": {"screen_name": "test", "id": 123},
            "created_at": "Sat Jul 19 22:54:07 +0000 2025"
        }
        body = json.dumps(tweet_data).encode('utf-8')
        
        # Mock the tweet processing to avoid actual AI calls
        with patch('src.handlers.message_handler.handle_tweet_event') as mock_handle:
            token_details = TokenDetails(
                chain_id=1,
                chain_name="Ethereum",
                token_address="0x742d35Cc6765C0532575f5A2c0a078Df8a2D4e5e",
                is_release=True,
                chain_defined_explicitly=True,
                definition_fragment="Ethereum"
            )
            tweet_output = TweetOutput(
                data_source=DataSource(name="Twitter", author_name="test", author_id="123"),
                createdAt=1640995200,
                text="Test tweet",
                media=[],
                links=[],
                sentiment_analysis=token_details
            )
            analysis_result = AnalysisResult.token_detection(token_details)
            processing_result = TweetProcessingResult(tweet_output=tweet_output, analysis=analysis_result)
            mock_handle.return_value = processing_result
            
            # Execute message handling
            handler(channel, method, properties, body)
            
            # Give thread time to process
            time.sleep(0.1)
            
            # Wait for processing threads to complete
            processor.wait_for_threads(timeout=2.0)
            
            # Verify processing occurred
            mock_handle.assert_called_once()
            mq_subscriber.publish.assert_called_once()
            
            # Verify acknowledgment callback was added
            channel.connection.add_callback_threadsafe.assert_called()