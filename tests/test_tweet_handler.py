"""Unit tests for tweet handler."""

import pytest
from unittest.mock import Mock, patch
from handlers.tweet import handle_tweet_event
from mq_messenger import MQMessenger


class TestTweetHandler:
    """Test tweet handler functionality."""
    
    def test_handle_tweet_event_with_mq_messenger(self):
        """Test tweet handler with MQMessenger parameter."""
        mock_messenger = Mock(spec=MQMessenger)
        mock_messenger.publish.return_value = True
        
        tweet_data = {
            "event_type": "tweet",
            "rule_id": "test_rule_123",
            "rule_tag": "bitcoin",
            "timestamp": 1674567890000,
            "tweets": [
                {"id": "123", "text": "Bitcoin is rising!", "author": "user1"},
                {"id": "124", "text": "Crypto market update", "author": "user2"}
            ]
        }
        
        handle_tweet_event(tweet_data, mock_messenger)
        
        # Verify publish was called
        mock_messenger.publish.assert_called_once()
        
        # Verify the message payload
        call_args = mock_messenger.publish.call_args[0][0]
        assert call_args["event_type"] == "tweet"
        assert call_args["rule_id"] == "test_rule_123"
        assert call_args["rule_tag"] == "bitcoin"
        assert call_args["tweet_count"] == 2
        assert call_args["tweets"] == tweet_data["tweets"]
        assert call_args["timestamp"] == 1674567890000
        assert "processing_timestamp" in call_args
        assert "time_difference_ms" in call_args
        assert "time_difference_formatted" in call_args
    
    def test_handle_tweet_event_publish_success(self):
        """Test successful tweet publishing."""
        mock_messenger = Mock(spec=MQMessenger)
        mock_messenger.publish.return_value = True
        
        tweet_data = {
            "event_type": "tweet",
            "rule_id": "success_rule",
            "rule_tag": "ethereum",
            "timestamp": 1674567890000,
            "tweets": [{"id": "789", "text": "ETH update", "author": "crypto_user"}]
        }
        
        with patch('handlers.tweet.logger') as mock_logger:
            handle_tweet_event(tweet_data, mock_messenger)
            
            # Verify success logging
            mock_logger.info.assert_any_call(
                "Tweet event published to RabbitMQ",
                rule_id="success_rule",
                tweet_count=1
            )
    
    def test_handle_tweet_event_publish_failure(self):
        """Test failed tweet publishing."""
        mock_messenger = Mock(spec=MQMessenger)
        mock_messenger.publish.return_value = False
        
        tweet_data = {
            "event_type": "tweet",
            "rule_id": "fail_rule",
            "rule_tag": "dogecoin",
            "timestamp": 1674567890000,
            "tweets": [{"id": "456", "text": "DOGE to the moon", "author": "doge_fan"}]
        }
        
        with patch('handlers.tweet.logger') as mock_logger:
            handle_tweet_event(tweet_data, mock_messenger)
            
            # Verify failure logging
            mock_logger.warning.assert_called_once_with(
                "Failed to publish tweet event to RabbitMQ",
                rule_id="fail_rule"
            )
    
    def test_handle_tweet_event_exception_handling(self):
        """Test exception handling during publishing."""
        mock_messenger = Mock(spec=MQMessenger)
        mock_messenger.publish.side_effect = Exception("Connection error")
        
        tweet_data = {
            "event_type": "tweet",
            "rule_id": "error_rule",
            "rule_tag": "litecoin",
            "timestamp": 1674567890000,
            "tweets": [{"id": "999", "text": "LTC update", "author": "ltc_trader"}]
        }
        
        with patch('handlers.tweet.logger') as mock_logger:
            # Should not raise exception
            handle_tweet_event(tweet_data, mock_messenger)
            
            # Verify error logging
            mock_logger.error.assert_called_once_with(
                "Error publishing tweet event to RabbitMQ",
                error="Connection error",
                rule_id="error_rule",
                tweet_count=1
            )
    
    def test_handle_tweet_event_time_calculations(self):
        """Test time difference calculations."""
        mock_messenger = Mock(spec=MQMessenger)
        mock_messenger.publish.return_value = True
        
        # Use a fixed timestamp for predictable time calculations
        test_timestamp = 1674567890000  # 2023-01-24 08:44:50 UTC
        
        tweet_data = {
            "event_type": "tweet",
            "rule_id": "time_rule",
            "rule_tag": "timing",
            "timestamp": test_timestamp,
            "tweets": [{"id": "time1", "text": "Time test", "author": "timer"}]
        }
        
        with patch('time.time', return_value=test_timestamp / 1000 + 300):  # 5 minutes later
            handle_tweet_event(tweet_data, mock_messenger)
            
            call_args = mock_messenger.publish.call_args[0][0]
            
            # Verify time calculations
            assert call_args["timestamp"] == test_timestamp
            assert call_args["time_difference_ms"] == 300000  # 5 minutes in ms
            assert "5min0sec" in call_args["time_difference_formatted"]
    
    def test_handle_tweet_event_empty_tweets(self):
        """Test handling of empty tweets list."""
        mock_messenger = Mock(spec=MQMessenger)
        mock_messenger.publish.return_value = True
        
        tweet_data = {
            "event_type": "tweet",
            "rule_id": "empty_rule",
            "rule_tag": "empty",
            "timestamp": 1674567890000,
            "tweets": []
        }
        
        handle_tweet_event(tweet_data, mock_messenger)
        
        call_args = mock_messenger.publish.call_args[0][0]
        assert call_args["tweet_count"] == 0
        assert call_args["tweets"] == []