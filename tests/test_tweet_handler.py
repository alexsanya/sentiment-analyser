"""Unit tests for tweet handler."""

import pytest
from unittest.mock import patch, AsyncMock
from src.handlers.tweet import handle_tweet_event
from src.models.schemas import TweetOutput, DataSource, NoTokenFound, AnalysisResult, TweetProcessingResult


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
            with patch('src.handlers.tweet.analyze_tweet_with_priority', new_callable=AsyncMock) as mock_analysis:
                mock_transform.return_value = expected_tweet_output
                mock_analysis.return_value = AnalysisResult.token_detection(NoTokenFound())  # Return AnalysisResult
                
                processing_result = handle_tweet_event(tweet_data)
                result = processing_result.tweet_output  # Extract TweetOutput from result
                analysis = processing_result.analysis  # Extract AnalysisResult
                
                # Verify transformation was called
                mock_transform.assert_called_once_with(tweet_data)
                
                # Verify analysis was called
                mock_analysis.assert_called_once_with(expected_tweet_output)
                
                # Verify returned data
                assert isinstance(processing_result, TweetProcessingResult)
                assert result.createdAt == 1674549890
                assert result.text == "Bitcoin is rising!"
                assert result.data_source.author_name == "user1"
                assert isinstance(result.sentiment_analysis, NoTokenFound)
                assert analysis.analysis_type == "no_analysis"
                assert not analysis.has_actionable_result
    
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
            "author_name": "user1",
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
            with patch('src.handlers.tweet.analyze_tweet_with_priority', new_callable=AsyncMock) as mock_analysis:
                with patch('src.handlers.tweet.logger') as mock_logger:
                    mock_transform.return_value = expected_tweet_output
                    mock_analysis.return_value = AnalysisResult.token_detection(NoTokenFound())
                    
                    processing_result = handle_tweet_event(tweet_data)
                    result = processing_result.tweet_output  # Extract TweetOutput
                    
                    # Verify logging was called
                    mock_logger.info.assert_called_with(
                        "Tweet processed successfully with topic-priority analysis",
                        tweet_id="123",
                        author="user1",  # Gets author_name from tweet_data
                        sentiment_result_type="NoTokenFound",
                        has_alignment_data=False,
                        alignment_score=None
                    )
    
    def test_handle_tweet_event_with_tsunami_warning_data(self):
        """Test tweet handler with real tsunami warning tweet data."""
        tweet_data = {
            "data_source": {
                "name": "Twitter", 
                "author_name": "realDonaldTrump", 
                "author_id": "25073877"
            }, 
            "createdAt": 1753841779, 
            "text": "Due to a massive earthquake that occurred in the Pacific Ocean, a Tsunami Warning is in effect for those living in Hawaii. A Tsunami Watch is in effect for Alaska and the Pacific Coast of the United States. Japan is also in the way. Please visit https://t.co/V5RZFDxYzl for the latest information. STAY STRONG AND STAY SAFE!", 
            "media": ["https://pbs.twimg.com/media/GhivrlDWAAA7Ex3?format=jpg&name=medium"], 
            "links": ["https://tsunami.gov/"]
        }
        
        expected_tweet_output = TweetOutput(
            data_source=DataSource(
                name="Twitter",
                author_name="realDonaldTrump",
                author_id="25073877"
            ),
            createdAt=1753841779,
            text="Due to a massive earthquake that occurred in the Pacific Ocean, a Tsunami Warning is in effect for those living in Hawaii. A Tsunami Watch is in effect for Alaska and the Pacific Coast of the United States. Japan is also in the way. Please visit https://t.co/V5RZFDxYzl for the latest information. STAY STRONG AND STAY SAFE!",
            media=["https://pbs.twimg.com/media/GhivrlDWAAA7Ex3?format=jpg&name=medium"],
            links=["https://tsunami.gov/"]
        )
        
        with patch('src.handlers.tweet.map_tweet_data') as mock_transform:
            with patch('src.handlers.tweet.analyze_tweet_with_priority', new_callable=AsyncMock) as mock_analysis:
                mock_transform.return_value = expected_tweet_output
                mock_analysis.return_value = AnalysisResult.token_detection(NoTokenFound())
                
                processing_result = handle_tweet_event(tweet_data)
                result = processing_result.tweet_output  # Extract TweetOutput
                analysis = processing_result.analysis  # Extract AnalysisResult
                
                # Verify transformation was called
                mock_transform.assert_called_once_with(tweet_data)
                
                # Verify analysis was called
                mock_analysis.assert_called_once_with(expected_tweet_output)
                
                # Verify returned data matches expected output
                assert result.createdAt == 1753841779
                assert result.text == expected_tweet_output.text
                assert result.data_source.author_name == "realDonaldTrump"
                assert result.data_source.author_id == "25073877"
                assert result.media == ["https://pbs.twimg.com/media/GhivrlDWAAA7Ex3?format=jpg&name=medium"]
                assert result.links == ["https://tsunami.gov/"]
                assert isinstance(result.sentiment_analysis, NoTokenFound)
    
    def test_handle_tweet_event_with_mocked_sentiment_analysis(self):
        """Test tweet handler with mocked sentiment analysis using tsunami warning data."""
        tweet_data = {
            "data_source": {
                "name": "Twitter", 
                "author_name": "realDonaldTrump", 
                "author_id": "25073877"
            }, 
            "createdAt": 1753841779, 
            "text": "Due to a massive earthquake that occurred in the Pacific Ocean, a Tsunami Warning is in effect for those living in Hawaii. A Tsunami Watch is in effect for Alaska and the Pacific Coast of the United States. Japan is also in the way. Please visit https://t.co/V5RZFDxYzl for the latest information. STAY STRONG AND STAY SAFE!", 
            "media": [], 
            "links": ["https://tsunami.gov/"]
        }
        
        with patch('src.handlers.tweet.analyze_tweet_with_priority', new_callable=AsyncMock) as mock_analysis:
            mock_analysis.return_value = AnalysisResult.token_detection(NoTokenFound())
            
            processing_result = handle_tweet_event(tweet_data)
            result = processing_result.tweet_output  # Extract TweetOutput
            analysis = processing_result.analysis  # Extract AnalysisResult
            
            # Verify analysis was called with the transformed data
            mock_analysis.assert_called_once()
            called_tweet_output = mock_analysis.call_args[0][0]
            
            # Check that the tweet output passed to analysis has correct structure
            assert isinstance(called_tweet_output, TweetOutput)
            assert called_tweet_output.data_source.name == "Twitter"
            assert called_tweet_output.data_source.author_name == "realDonaldTrump"
            assert called_tweet_output.data_source.author_id == "25073877"
            assert called_tweet_output.createdAt == 1753841779
            assert "Tsunami Warning" in called_tweet_output.text
            assert called_tweet_output.media == []
            assert called_tweet_output.links == ["https://tsunami.gov/"]
            
            # Verify the final result includes analysis results
            assert result.createdAt == 1753841779
            assert result.data_source.author_name == "realDonaldTrump"
            assert result.data_source.author_id == "25073877"
            assert "Tsunami Warning" in result.text
            assert result.media == []
            assert result.links == ["https://tsunami.gov/"]
            assert isinstance(result.sentiment_analysis, NoTokenFound)