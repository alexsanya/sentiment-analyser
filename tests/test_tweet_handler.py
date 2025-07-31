"""Unit tests for tweet handler."""

import pytest
from unittest.mock import patch, AsyncMock
from src.handlers.tweet import handle_tweet_event
from src.models.schemas import TweetOutput, DataSource, NoTokenFound


class TestTweetHandler:
    """Test tweet handler functionality."""
    
    def test_handle_tweet_event_processing(self):
        """Test tweet handler processing single tweet."""
        tweet_data = {
            "id": "123", 
            "text": "Bitcoin is rising!", 
            "createdAt": "Tue Jan 24 08:44:50 +0000 2023",
            "author": {"username": "user1", "id": "user1_id"},
            "entities": {"urls": []},
            "extended_entities": {}
        }
        
        expected_tweet_output = TweetOutput(
            data_source=DataSource(
                name="Twitter",
                author_name="user1",
                author_id="user1_id"
            ),
            createdAt=1674549890,
            text="Bitcoin is rising!",
            media=[],
            links=[]
        )
        
        with patch('src.handlers.tweet.map_tweet_data') as mock_transform:
            with patch('src.handlers.tweet.analyze_tweet_sentiment', new_callable=AsyncMock) as mock_sentiment:
                mock_transform.return_value = expected_tweet_output
                mock_sentiment.return_value = NoTokenFound()
                
                result = handle_tweet_event(tweet_data)
                
                # Verify transformation was called
                mock_transform.assert_called_once_with(tweet_data)
                
                # Verify sentiment analysis was called
                mock_sentiment.assert_called_once_with(expected_tweet_output)
                
                # Verify returned data
                assert result.createdAt == 1674549890
                assert result.text == "Bitcoin is rising!"
                assert result.data_source.author_name == "user1"
                assert isinstance(result.sentiment_analysis, NoTokenFound)
    
    def test_handle_tweet_event_exception_handling(self):
        """Test tweet handler exception handling."""
        tweet_data = {
            "id": "123", 
            "text": "Bitcoin is rising!", 
            "createdAt": "Invalid date format"
        }
        
        with patch('src.handlers.tweet.map_tweet_data') as mock_transform:
            mock_transform.side_effect = Exception("Transformation failed")
            
            with pytest.raises(Exception, match="Transformation failed"):
                handle_tweet_event(tweet_data)
            
            # Should be called twice - once in async function, once in fallback
            assert mock_transform.call_count == 2
            mock_transform.assert_called_with(tweet_data)
    
    def test_handle_tweet_event_logging(self):
        """Test tweet handler logging."""
        tweet_data = {
            "id": "123", 
            "text": "Bitcoin is rising!", 
            "createdAt": "Tue Jan 24 08:44:50 +0000 2023",
            "author": {"username": "user1", "id": "user1_id"}
        }
        
        expected_tweet_output = TweetOutput(
            data_source=DataSource(
                name="Twitter",
                author_name="user1",
                author_id="user1_id"
            ),
            createdAt=1674549890,
            text="Bitcoin is rising!",
            media=[],
            links=[]
        )
        
        with patch('src.handlers.tweet.map_tweet_data') as mock_transform:
            with patch('src.handlers.tweet.analyze_tweet_sentiment', new_callable=AsyncMock) as mock_sentiment:
                with patch('src.handlers.tweet.logger') as mock_logger:
                    mock_transform.return_value = expected_tweet_output
                    mock_sentiment.return_value = NoTokenFound()
                    
                    result = handle_tweet_event(tweet_data)
                    
                    # Verify logging was called
                    mock_logger.info.assert_called_with(
                        "Tweet processed successfully with sentiment analysis",
                        tweet_id="123",
                        author="user1",
                        sentiment_result_type="NoTokenFound"
                    )