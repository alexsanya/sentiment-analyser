"""Integration tests for tweet handler with transformation pipeline."""

import pytest
from unittest.mock import Mock, patch
from src.handlers.tweet import handle_tweet_event, publish_tweet_event
from src.core.mq_messenger import MQMessenger
from src.models.schemas import TweetOutput, DataSource
from src.core.transformation import map_tweet_data


class TestTweetHandlerIntegration:
    """Integration tests for tweet handler with transformation pipeline."""
    
    def test_handle_tweet_event_with_valid_tweets(self):
        """Test handling tweet events with valid tweet data."""
        mock_mq_messenger = Mock(spec=MQMessenger)
        mock_mq_messenger.publish.return_value = True
        
        tweet_event_data = {
            "tweets": [
                {
                    "createdAt": "Mon Jan 01 12:00:00 +0000 2024",
                    "text": "Test tweet content",
                    "isReply": False,
                    "author": {
                        "userName": "testuser",
                        "id": "123456789"
                    },
                    "extendedEntities": {
                        "media": [
                            {"media_url_https": "https://example.com/image.jpg"}
                        ]
                    },
                    "entities": {
                        "urls": [
                            {"expanded_url": "https://example.com/article"}
                        ]
                    }
                }
            ]
        }
        
        # Call the handler
        handle_tweet_event(tweet_event_data, mock_mq_messenger)
        
        # Verify publish was called
        mock_mq_messenger.publish.assert_called_once()
        
        # Verify the published data structure
        published_data = mock_mq_messenger.publish.call_args[0][0]
        assert isinstance(published_data, TweetOutput)
        assert published_data.data_source.name == "Twitter"
        assert published_data.data_source.author_name == "testuser"
        assert published_data.data_source.author_id == "123456789"
        assert published_data.createdAt == 1704110400
        assert published_data.text == "Test tweet content"
        assert published_data.media == ["https://example.com/image.jpg"]
        assert published_data.links == ["https://example.com/article"]
    
    def test_handle_tweet_event_skips_replies(self):
        """Test that reply tweets are skipped."""
        mock_mq_messenger = Mock(spec=MQMessenger)
        
        tweet_event_data = {
            "tweets": [
                {
                    "createdAt": "Mon Jan 01 12:00:00 +0000 2024",
                    "text": "@someone This is a reply",
                    "isReply": True,  # This should be skipped
                    "author": {
                        "userName": "testuser",
                        "id": "123456789"
                    }
                }
            ]
        }
        
        # Call the handler
        handle_tweet_event(tweet_event_data, mock_mq_messenger)
        
        # Verify publish was not called
        mock_mq_messenger.publish.assert_not_called()
    
    def test_handle_tweet_event_with_malicious_urls(self):
        """Test that malicious URLs are filtered out during processing."""
        mock_mq_messenger = Mock(spec=MQMessenger)
        mock_mq_messenger.publish.return_value = True
        
        tweet_event_data = {
            "tweets": [
                {
                    "createdAt": "Mon Jan 01 12:00:00 +0000 2024",
                    "text": "Check out these malicious links",
                    "isReply": False,
                    "author": {
                        "userName": "testuser",
                        "id": "123456789"
                    },
                    "extendedEntities": {
                        "media": [
                            {"media_url_https": "https://safe-image.com/pic.jpg"},
                            {"media_url_https": "javascript:alert('xss')"},
                            {"media_url_https": "data:image/png;base64,malicious"}
                        ]
                    },
                    "entities": {
                        "urls": [
                            {"expanded_url": "https://safe-link.com"},
                            {"expanded_url": "[Link](javascript:alert('xss'))"},
                            {"expanded_url": "[File](file:///etc/passwd)"}
                        ]
                    }
                }
            ]
        }
        
        # Call the handler
        handle_tweet_event(tweet_event_data, mock_mq_messenger)
        
        # Verify publish was called
        mock_mq_messenger.publish.assert_called_once()
        
        # Verify malicious URLs were filtered out
        published_data = mock_mq_messenger.publish.call_args[0][0]
        assert len(published_data.media) == 1
        assert "https://safe-image.com/pic.jpg" in published_data.media
        assert len([url for url in published_data.media if "javascript:" in url]) == 0
        assert len([url for url in published_data.media if "data:" in url]) == 0
        
        assert len(published_data.links) == 1
        assert "https://safe-link.com" in published_data.links
        assert len([url for url in published_data.links if "javascript:" in url]) == 0
        assert len([url for url in published_data.links if "file:" in url]) == 0
    
    def test_handle_tweet_event_with_multiple_tweets(self):
        """Test handling multiple tweets in a single event."""
        mock_mq_messenger = Mock(spec=MQMessenger)
        mock_mq_messenger.publish.return_value = True
        
        tweet_event_data = {
            "tweets": [
                {
                    "createdAt": "Mon Jan 01 12:00:00 +0000 2024",
                    "text": "First tweet",
                    "isReply": False,
                    "author": {"userName": "user1", "id": "111"}
                },
                {
                    "createdAt": "Mon Jan 01 13:00:00 +0000 2024", 
                    "text": "Second tweet",
                    "isReply": False,
                    "author": {"userName": "user2", "id": "222"}
                },
                {
                    "createdAt": "Mon Jan 01 14:00:00 +0000 2024",
                    "text": "Reply tweet",
                    "isReply": True,  # Should be skipped
                    "author": {"userName": "user3", "id": "333"}
                }
            ]
        }
        
        # Call the handler
        handle_tweet_event(tweet_event_data, mock_mq_messenger)
        
        # Verify publish was called twice (not for the reply)
        assert mock_mq_messenger.publish.call_count == 2
        
        # Verify the correct tweets were published
        call_args_list = mock_mq_messenger.publish.call_args_list
        first_tweet = call_args_list[0][0][0]
        second_tweet = call_args_list[1][0][0]
        
        assert first_tweet.text == "First tweet"
        assert first_tweet.data_source.author_name == "user1"
        assert second_tweet.text == "Second tweet"
        assert second_tweet.data_source.author_name == "user2" 
    
    def test_handle_tweet_event_with_malformed_data(self):
        """Test handling malformed tweet data gracefully."""
        mock_mq_messenger = Mock(spec=MQMessenger)
        mock_mq_messenger.publish.return_value = True
        
        tweet_event_data = {
            "tweets": [
                {
                    # Missing createdAt
                    "text": "Malformed tweet",
                    "isReply": False,
                    "author": "not_a_dict",  # Should be a dict
                    "extendedEntities": "also_not_a_dict"  # Should be a dict
                }
            ]
        }
        
        # Call the handler - should not raise exceptions
        handle_tweet_event(tweet_event_data, mock_mq_messenger)
        
        # Verify publish was called with fallback values
        mock_mq_messenger.publish.assert_called_once()
        
        published_data = mock_mq_messenger.publish.call_args[0][0]
        assert published_data.text == "Malformed tweet"
        assert published_data.createdAt == 0  # Fallback for missing/invalid createdAt
        assert published_data.data_source.author_name == ""  # Fallback for malformed author
        assert published_data.media == []  # Fallback for malformed extendedEntities
        assert published_data.links == []
    
    def test_publish_tweet_event_success(self):
        """Test successful tweet event publishing."""
        mock_mq_messenger = Mock(spec=MQMessenger)
        mock_mq_messenger.publish.return_value = True
        
        tweet_data = TweetOutput(
            data_source=DataSource(
                name="Twitter",
                author_name="testuser",
                author_id="123"
            ),
            createdAt=1704110400,
            text="Test tweet",
            media=["https://example.com/image.jpg"],
            links=["https://example.com/article"]
        )
        
        # Call publish function
        publish_tweet_event(tweet_data, mock_mq_messenger)
        
        # Verify publish was called with correct data
        mock_mq_messenger.publish.assert_called_once_with(tweet_data)
    
    def test_publish_tweet_event_failure(self):
        """Test handling of publish failures."""
        mock_mq_messenger = Mock(spec=MQMessenger)
        mock_mq_messenger.publish.return_value = False  # Simulate failure
        
        tweet_data = TweetOutput(
            data_source=DataSource(name="Twitter", author_name="testuser", author_id="123"),
            createdAt=1704110400,
            text="Test tweet"
        )
        
        # Call publish function - should not raise exceptions
        publish_tweet_event(tweet_data, mock_mq_messenger)
        
        # Verify publish was called
        mock_mq_messenger.publish.assert_called_once_with(tweet_data)
    
    def test_publish_tweet_event_exception(self):
        """Test handling of exceptions during publishing."""
        mock_mq_messenger = Mock(spec=MQMessenger)
        mock_mq_messenger.publish.side_effect = Exception("Publishing failed")
        
        tweet_data = TweetOutput(
            data_source=DataSource(name="Twitter", author_name="testuser", author_id="123"),
            createdAt=1704110400,
            text="Test tweet"
        )
        
        # Call publish function - should not raise exceptions
        publish_tweet_event(tweet_data, mock_mq_messenger)
        
        # Verify publish was attempted
        mock_mq_messenger.publish.assert_called_once_with(tweet_data)
    
    def test_empty_tweets_list(self):
        """Test handling of empty tweets list."""
        mock_mq_messenger = Mock(spec=MQMessenger)
        
        tweet_event_data = {
            "tweets": []
        }
        
        # Call the handler
        handle_tweet_event(tweet_event_data, mock_mq_messenger)
        
        # Verify publish was not called
        mock_mq_messenger.publish.assert_not_called()
    
    def test_missing_tweets_key(self):
        """Test handling of missing tweets key."""
        mock_mq_messenger = Mock(spec=MQMessenger)
        
        tweet_event_data = {}  # Missing tweets key
        
        # Call the handler - should not raise exceptions
        handle_tweet_event(tweet_event_data, mock_mq_messenger)
        
        # Verify publish was not called
        mock_mq_messenger.publish.assert_not_called()


class TestTweetTransformationPipeline:
    """End-to-end tests for tweet transformation pipeline."""
    
    def test_complete_pipeline_with_sample_data(self):
        """Test complete pipeline using sample tweet data."""
        import json
        from pathlib import Path
        
        # Load sample data
        sample_file = Path(__file__).parent.parent / "examples" / "tweet-sample.json"
        with open(sample_file, 'r') as f:
            sample_data = json.load(f)
        
        mock_mq_messenger = Mock(spec=MQMessenger)
        mock_mq_messenger.publish.return_value = True
        
        # Process the sample data through the handler
        handle_tweet_event(sample_data, mock_mq_messenger)
        
        # Verify processing was successful
        mock_mq_messenger.publish.assert_called_once()
        
        # Verify the transformation was applied correctly
        published_data = mock_mq_messenger.publish.call_args[0][0]
        assert isinstance(published_data, TweetOutput)
        assert published_data.data_source.name == "Twitter"
        assert published_data.data_source.author_name == "alexsanyakoval"
        assert published_data.data_source.author_id == "3152441518"
        assert published_data.createdAt == 1752965647
        assert "My Rules of engagement" in published_data.text
        assert len(published_data.media) == 1
        assert "https://pbs.twimg.com/media/GwQVzqgXEAAGvbc.jpg" in published_data.media
        assert len(published_data.links) == 1
        # The LinkedIn URL should be extracted from the markdown-style link
        linkedin_url = "https://www.linkedin.com/posts/kovalas_candidateexperience-hiring-techrecruiting-activity-7351630837789929476-DzM1?utm_source=share&utm_medium=member_desktop&rcm=ACoAAAxBctkB-IBy_pKCQ-_f0LrBMyhGZ5Lw2Tg"
        assert linkedin_url in published_data.links
    
    def test_pipeline_performance_with_large_dataset(self):
        """Test pipeline performance with large dataset."""
        mock_mq_messenger = Mock(spec=MQMessenger)
        mock_mq_messenger.publish.return_value = True
        
        # Create a large dataset with 100 tweets
        large_tweet_event = {
            "tweets": [
                {
                    "createdAt": "Mon Jan 01 12:00:00 +0000 2024",
                    "text": f"Tweet number {i} with some content",
                    "isReply": False,
                    "author": {
                        "userName": f"user{i}",
                        "id": str(1000 + i)
                    },
                    "extendedEntities": {
                        "media": [
                            {"media_url_https": f"https://example.com/image{i}.jpg"}
                        ]
                    },
                    "entities": {
                        "urls": [
                            {"expanded_url": f"https://example.com/article{i}"}
                        ]
                    }
                }
                for i in range(100)
            ]
        }
        
        import time
        start_time = time.time()
        
        # Process the large dataset
        handle_tweet_event(large_tweet_event, mock_mq_messenger)
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        # Verify all tweets were processed
        assert mock_mq_messenger.publish.call_count == 100
        
        # Verify reasonable performance (should process 100 tweets in under 1 second)
        assert processing_time < 1.0, f"Processing took too long: {processing_time} seconds"
        
        # Verify data integrity for a few random tweets
        call_args_list = mock_mq_messenger.publish.call_args_list
        first_tweet = call_args_list[0][0][0]
        last_tweet = call_args_list[99][0][0]
        
        assert first_tweet.text == "Tweet number 0 with some content"
        assert first_tweet.data_source.author_name == "user0"
        assert last_tweet.text == "Tweet number 99 with some content"
        assert last_tweet.data_source.author_name == "user99"