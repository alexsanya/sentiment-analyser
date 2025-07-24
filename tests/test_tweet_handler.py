"""Unit tests for tweet handler."""

import pytest
from unittest.mock import Mock, patch
from src.handlers.tweet import handle_tweet_event
from src.core.mq_messenger import MQMessenger


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
                {
                    "id": "123", 
                    "text": "Bitcoin is rising!", 
                    "createdAt": "Tue Jan 24 08:44:50 +0000 2023",
                    "author": {"userName": "user1", "id": "user1_id"}
                },
                {
                    "id": "124", 
                    "text": "Crypto market update", 
                    "createdAt": "Tue Jan 24 08:44:50 +0000 2023",
                    "author": {"userName": "user2", "id": "user2_id"}
                }
            ]
        }
        
        handle_tweet_event(tweet_data, mock_messenger)
        
        # Verify publish was called twice (once for each tweet)
        assert mock_messenger.publish.call_count == 2
        
        # Verify the first tweet's message payload
        first_call_args = mock_messenger.publish.call_args_list[0][0][0]
        assert first_call_args.createdAt == 1674549890  # Unix timestamp
        assert first_call_args.text == "Bitcoin is rising!"
        assert first_call_args.media == []
        assert first_call_args.links == []
        assert first_call_args.data_source.author_name == "user1"
        assert first_call_args.data_source.author_id == "user1_id"
    
    def test_handle_tweet_event_publish_success(self):
        """Test successful tweet publishing."""
        mock_messenger = Mock(spec=MQMessenger)
        mock_messenger.publish.return_value = True
        
        tweet_data = {
            "event_type": "tweet",
            "rule_id": "success_rule",
            "rule_tag": "ethereum",
            "timestamp": 1674567890000,
            "tweets": [{
                "id": "789", 
                "text": "ETH update", 
                "createdAt": "Tue Jan 24 08:44:50 +0000 2023",
                "author": {"userName": "crypto_user", "id": "crypto_user_id"}
            }]
        }
        
        with patch('src.handlers.tweet.logger') as mock_logger:
            handle_tweet_event(tweet_data, mock_messenger)
            
            # Verify success logging (first the tweet received log, then publish success)
            mock_logger.info.assert_any_call(
                "Tweet event published to RabbitMQ",
                tweet_data=mock_messenger.publish.call_args[0][0]
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
            "tweets": [{
                "id": "456", 
                "text": "DOGE to the moon", 
                "createdAt": "Tue Jan 24 08:44:50 +0000 2023",
                "author": {"userName": "doge_fan", "id": "doge_fan_id"}
            }]
        }
        
        with patch('src.handlers.tweet.logger') as mock_logger:
            handle_tweet_event(tweet_data, mock_messenger)
            
            # Verify failure logging
            mock_logger.warning.assert_called_once_with(
                "Failed to publish tweet event to RabbitMQ",
                tweet_data=mock_messenger.publish.call_args[0][0]
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
            "tweets": [{
                "id": "999", 
                "text": "LTC update", 
                "createdAt": "Tue Jan 24 08:44:50 +0000 2023",
                "author": {"userName": "ltc_trader", "id": "ltc_trader_id"}
            }]
        }
        
        with patch('src.handlers.tweet.logger') as mock_logger:
            # Should not raise exception
            handle_tweet_event(tweet_data, mock_messenger)
            
            # Verify error logging
            mock_logger.error.assert_called_once_with(
                "Error publishing tweet event to RabbitMQ",
                error="Connection error",
                tweet_data=mock_messenger.publish.call_args[0][0]
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
            "tweets": [{
                "id": "time1", 
                "text": "Time test", 
                "createdAt": "Tue Jan 24 08:44:50 +0000 2023",
                "author": {"userName": "timer", "id": "timer_id"}
            }]
        }
        
        with patch('time.time', return_value=test_timestamp / 1000 + 300):  # 5 minutes later
            handle_tweet_event(tweet_data, mock_messenger)
            
            call_args = mock_messenger.publish.call_args[0][0]
            
            # Verify TweetOutput object contains expected data
            assert call_args.createdAt == 1674549890  # Unix timestamp converted from createdAt string
            assert call_args.text == "Time test"
            assert call_args.media == []
            assert call_args.links == []
            assert call_args.data_source.author_name == "timer"
    
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
        
        # With empty tweets list, the handler simply doesn't iterate
        handle_tweet_event(tweet_data, mock_messenger)
        
        # Should not call publish due to empty tweets list
        mock_messenger.publish.assert_not_called()