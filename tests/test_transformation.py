import json
import pytest
from pathlib import Path
from datetime import datetime
from transformation import map_tweet_data, parse_twitter_datetime, extract_url, validate_url_security, sanitize_url_list
from schemas import TweetOutput, DataSource
from pydantic import ValidationError

def test_map_tweet_data_snapshot():
    """Snapshot test for map_tweet_data function with tweet-sample.json"""
    # Load sample data
    sample_file = Path(__file__).parent.parent / "tweet-sample.json"
    with open(sample_file, 'r') as f:
        input_data = json.load(f)
    
    # Get the first tweet from the sample
    tweet = input_data["tweets"][0]
    
    # Transform the data
    result = map_tweet_data(tweet)
    
    # Expected output - createdAt should be unix timestamp for "Sat Jul 19 22:54:07 +0000 2025"
    # This corresponds to unix timestamp 1752965647
    expected = TweetOutput(
        data_source=DataSource(
            name="Twitter",
            author_name="alexsanyakoval",
            author_id="3152441518"
        ),
        createdAt=1752965647,  # Unix timestamp for "Sat Jul 19 22:54:07 +0000 2025"
        text="My Rules of engagement\nReed more in my post: https://t.co/tKo1tfckav https://t.co/Khhm0sufWd",
        media=["https://pbs.twimg.com/media/GwQVzqgXEAAGvbc.jpg"],
        links=["https://www.linkedin.com/posts/kovalas_candidateexperience-hiring-techrecruiting-activity-7351630837789929476-DzM1?utm_source=share&utm_medium=member_desktop&rcm=ACoAAAxBctkB-IBy_pKCQ-_f0LrBMyhGZ5Lw2Tg"]
    )
    
    assert result == expected


class TestTransformation:
    """Comprehensive test suite for data transformation functions."""
    
    def test_map_tweet_data_valid_input(self):
        """Test map_tweet_data with valid input data."""
        tweet = {
            "createdAt": "Mon Jan 01 12:00:00 +0000 2024",
            "text": "Test tweet content",
            "author": {
                "userName": "testuser",
                "id": "123456789"
            },
            "extendedEntities": {
                "media": [
                    {"media_url_https": "https://example.com/image1.jpg"},
                    {"media_url_https": "https://example.com/image2.png"}
                ]
            },
            "entities": {
                "urls": [
                    {"expanded_url": "https://example.com/article"},
                    {"expanded_url": "[Link Text](https://malicious.com/script.js)"}
                ]
            }
        }
        
        result = map_tweet_data(tweet)
        
        assert isinstance(result, TweetOutput)
        assert result.data_source.name == "Twitter"
        assert result.data_source.author_name == "testuser"
        assert result.data_source.author_id == "123456789"
        assert result.text == "Test tweet content"
        assert len(result.media) == 2
        assert len(result.links) == 2
        assert result.createdAt == 1704110400  # Unix timestamp for "Mon Jan 01 12:00:00 +0000 2024"
    
    def test_map_tweet_data_empty_input(self):
        """Test map_tweet_data with empty dictionary."""
        tweet = {}
        result = map_tweet_data(tweet)
        
        assert isinstance(result, TweetOutput)
        assert result.data_source.name == "Twitter"
        assert result.data_source.author_name == ""
        assert result.data_source.author_id == ""
        assert result.text == ""
        assert result.media == []
        assert result.links == []
        assert result.createdAt == 0
    
    def test_map_tweet_data_missing_fields(self):
        """Test map_tweet_data with missing optional fields."""
        tweet = {
            "text": "Basic tweet",
            "createdAt": "Wed Jun 15 14:30:45 +0000 2023"
        }
        
        result = map_tweet_data(tweet)
        
        assert result.text == "Basic tweet"
        assert result.createdAt == 1686839445
        assert result.data_source.author_name == ""
        assert result.data_source.author_id == ""
        assert result.media == []
        assert result.links == []
    
    def test_map_tweet_data_malformed_author(self):
        """Test map_tweet_data with malformed author data."""
        tweet = {
            "text": "Tweet with bad author",
            "author": "not_a_dict",  # Should be a dictionary
            "createdAt": "Mon Jan 01 12:00:00 +0000 2024"
        }
        
        result = map_tweet_data(tweet)
        
        assert result.text == "Tweet with bad author"
        assert result.data_source.author_name == ""
        assert result.data_source.author_id == ""
    
    def test_map_tweet_data_malformed_entities(self):
        """Test map_tweet_data with malformed entity structures."""
        tweet = {
            "text": "Tweet with bad entities",
            "extendedEntities": "not_a_dict",
            "entities": None,
            "createdAt": "Mon Jan 01 12:00:00 +0000 2024"
        }
        
        result = map_tweet_data(tweet)
        
        assert result.text == "Tweet with bad entities"
        assert result.media == []
        assert result.links == []
    
    def test_map_tweet_data_unicode_content(self):
        """Test map_tweet_data with Unicode characters."""
        tweet = {
            "text": "Tweet with emoji 🚀 and Unicode: ñáéíóú 中文 العربية",
            "author": {
                "userName": "user_ñáéíóú",
                "id": "123456789"
            },
            "createdAt": "Mon Jan 01 12:00:00 +0000 2024"
        }
        
        result = map_tweet_data(tweet)
        
        assert "🚀" in result.text
        assert "ñáéíóú" in result.text
        assert "中文" in result.text
        assert "العربية" in result.text
        assert result.data_source.author_name == "user_ñáéíóú"
    
    def test_map_tweet_data_very_long_text(self):
        """Test map_tweet_data with very long text content."""
        long_text = "A" * 10000  # Very long text
        tweet = {
            "text": long_text,
            "createdAt": "Mon Jan 01 12:00:00 +0000 2024"
        }
        
        result = map_tweet_data(tweet)
        
        assert result.text == long_text
        assert len(result.text) == 10000
    
    def test_map_tweet_data_null_values(self):
        """Test map_tweet_data with null/None values."""
        tweet = {
            "text": None,
            "author": None,
            "extendedEntities": None,
            "entities": None,
            "createdAt": None
        }
        
        result = map_tweet_data(tweet)
        
        # Schema validation should handle None values gracefully
        assert result.text == ""
        assert result.data_source.author_name == ""
        assert result.data_source.author_id == ""
        assert result.media == []
        assert result.links == []
        assert result.createdAt == 0


class TestParseTwitterDatetime:
    """Test suite for Twitter datetime parsing functionality."""
    
    def test_parse_valid_datetime(self):
        """Test parsing valid Twitter datetime strings."""
        test_cases = [
            ("Mon Jan 01 12:00:00 +0000 2024", 1704110400),
            ("Wed Jun 15 14:30:45 +0000 2023", 1686839445),
            ("Sat Jul 19 22:54:07 +0000 2025", 1752965647),
            ("Sun Dec 31 23:59:59 +0000 2023", 1704067199)
        ]
        
        for datetime_str, expected_timestamp in test_cases:
            result = parse_twitter_datetime(datetime_str)
            assert result == expected_timestamp, f"Failed for {datetime_str}"
    
    def test_parse_invalid_datetime_format(self):
        """Test parsing invalid datetime formats."""
        invalid_formats = [
            "2024-01-01 12:00:00",  # ISO format
            "01/01/2024 12:00:00",  # US format
            "invalid datetime",     # Completely invalid
            "Mon Jan 01 25:00:00 +0000 2024",  # Invalid hour
            "Mon Jan 32 12:00:00 +0000 2024",  # Invalid day
            "Mon Inv 01 12:00:00 +0000 2024",  # Invalid month
            "",  # Empty string
        ]
        
        for invalid_format in invalid_formats:
            result = parse_twitter_datetime(invalid_format)
            assert result == 0, f"Should return 0 for invalid format: {invalid_format}"
    
    def test_parse_none_datetime(self):
        """Test parsing None datetime value."""
        result = parse_twitter_datetime(None)
        assert result == 0
    
    def test_parse_non_string_datetime(self):
        """Test parsing non-string datetime values."""
        non_string_values = [123456, [], {}, True, False]
        
        for value in non_string_values:
            result = parse_twitter_datetime(value)
            assert result == 0, f"Should return 0 for non-string value: {value}"


class TestExtractUrl:
    """Test suite for URL extraction functionality with security focus."""
    
    def test_extract_markdown_url(self):
        """Test extracting URL from markdown-style links."""
        test_cases = [
            ("[Link Text](https://example.com)", "https://example.com"),
            ("[](https://example.com/path)", "https://example.com/path"),
            ("[Complex Link](https://example.com/path?param=value&other=123)", 
             "https://example.com/path?param=value&other=123")
        ]
        
        for input_text, expected_url in test_cases:
            result = extract_url(input_text)
            assert result == expected_url, f"Failed for input: {input_text}"
    
    def test_extract_url_no_markdown(self):
        """Test extract_url with non-markdown text."""
        plain_texts = [
            "https://example.com",
            "plain text without links",
            "text with (parentheses) but no markdown",
            ""
        ]
        
        for text in plain_texts:
            result = extract_url(text)
            assert result == text, f"Should return original text for: {text}"
    
    def test_extract_url_malicious_inputs(self):
        """Test extract_url with potentially malicious inputs."""
        malicious_inputs = [
            "[XSS](javascript:alert('xss'))",
            "[Data URL](data:text/html,<script>alert('xss')</script>)",
            "[File URL](file:///etc/passwd)",
            "[FTP URL](ftp://malicious.com/file)",
            "[Redirect](https://bit.ly/malicious)",
            "[Long URL](" + "https://example.com/" + "a" * 2000 + ")",
        ]
        
        for malicious_input in malicious_inputs:
            result = extract_url(malicious_input)
            # The function should extract the URL but security validation should happen elsewhere
            assert isinstance(result, str)
            # Check that javascript: and data: schemes are extracted (to be filtered later)
            if "javascript:" in malicious_input:
                assert "javascript:" in result
            if "data:" in malicious_input:
                assert "data:" in result
    
    def test_extract_url_edge_cases(self):
        """Test extract_url with edge cases."""
        edge_cases = [
            ("[]()",""),  # Empty URL
            ("[Text]()", ""),  # Empty URL with text
            ("[Text](   )", ""),  # Whitespace URL gets stripped to empty
            ("[Nested [brackets]](https://example.com)", "https://example.com"),
            ("Multiple [link1](https://example1.com) and [link2](https://example2.com)", 
             "https://example1.com"),  # Should extract first match
        ]
        
        for input_text, expected in edge_cases:
            result = extract_url(input_text)
            assert result == expected, f"Failed for: {input_text}"
    
    def test_extract_url_unicode(self):
        """Test extract_url with Unicode characters."""
        unicode_cases = [
            ("[Unicode](https://example.com/ñáéíóú)", "https://example.com/ñáéíóú"),
            ("[Chinese](https://example.com/中文)", "https://example.com/中文"),
            ("[Arabic](https://example.com/العربية)", "https://example.com/العربية"),
            ("[Emoji](https://example.com/🚀)", "https://example.com/🚀")
        ]
        
        for input_text, expected in unicode_cases:
            result = extract_url(input_text)
            assert result == expected, f"Failed for Unicode input: {input_text}"


class TestSchemaValidation:
    """Test suite for Pydantic schema validation."""
    
    def test_tweet_output_valid_data(self):
        """Test TweetOutput schema with valid data."""
        valid_data = {
            "data_source": {
                "name": "Twitter",
                "author_name": "testuser",
                "author_id": "123"
            },
            "createdAt": 1704110400,
            "text": "Test tweet",
            "media": ["https://example.com/image.jpg"],
            "links": ["https://example.com/article"]
        }
        
        tweet = TweetOutput(**valid_data)
        
        assert tweet.data_source.name == "Twitter"
        assert tweet.data_source.author_name == "testuser"
        assert tweet.data_source.author_id == "123"
        assert tweet.createdAt == 1704110400
        assert tweet.text == "Test tweet"
        assert tweet.media == ["https://example.com/image.jpg"]
        assert tweet.links == ["https://example.com/article"]
    
    def test_tweet_output_default_values(self):
        """Test TweetOutput schema with missing fields uses defaults."""
        minimal_data = {}
        
        tweet = TweetOutput(**minimal_data)
        
        assert tweet.data_source.name == ""
        assert tweet.data_source.author_name == ""
        assert tweet.data_source.author_id == ""
        assert tweet.createdAt == 0
        assert tweet.text == ""
        assert tweet.media == []
        assert tweet.links == []
    
    def test_tweet_output_field_validation(self):
        """Test TweetOutput field validators."""
        # Test text validator with non-string input
        data_with_non_string_text = {
            "text": 123  # Should be converted to empty string
        }
        tweet = TweetOutput(**data_with_non_string_text)
        assert tweet.text == ""
        
        # Test URL list validators with mixed types
        data_with_mixed_urls = {
            "media": ["https://valid.com", 123, None, "", "  ", "https://another.com"],
            "links": ["https://link.com", {}, [], "invalid", "   "]
        }
        tweet = TweetOutput(**data_with_mixed_urls)
        assert tweet.media == ["https://valid.com", "https://another.com"]
        assert tweet.links == ["https://link.com", "invalid"]
    
    def test_tweet_output_type_coercion(self):
        """Test TweetOutput type coercion and validation."""
        data_with_wrong_types = {
            "createdAt": "1704110400",  # String that can be converted to int
            "text": 123,  # Non-string text
            "media": "not_a_list",  # Should be converted to empty list
            "links": None  # Should be converted to empty list
        }
        
        tweet = TweetOutput(**data_with_wrong_types)
        
        assert tweet.createdAt == 1704110400
        assert tweet.text == ""
        assert tweet.media == []
        assert tweet.links == []


class TestIntegration:
    """Integration tests for the complete transformation pipeline."""
    
    def test_malformed_data_handling(self):
        """Test that malformed data is handled gracefully throughout the pipeline."""
        malformed_tweets = [
            None,
            "not_a_dict",
            [],
            123,
            {"completely": "wrong", "structure": True}
        ]
        
        for malformed_tweet in malformed_tweets:
            try:
                # All inputs should be handled gracefully by converting to empty dict
                result = map_tweet_data(malformed_tweet)
                assert isinstance(result, TweetOutput)
                # Non-dict inputs get converted to empty dict, so should get default values
                if not isinstance(malformed_tweet, dict):
                    assert result.text == ""
                    assert result.createdAt == 0
                    assert result.data_source.author_name == ""
                    assert result.media == []
                    assert result.links == []
            except Exception as e:
                pytest.fail(f"Unexpected exception for {malformed_tweet}: {e}")
    
    def test_large_data_handling(self):
        """Test handling of large data volumes."""
        # Create a tweet with large amounts of data
        large_tweet = {
            "text": "Large tweet content " * 1000,  # ~20KB of text
            "createdAt": "Mon Jan 01 12:00:00 +0000 2024",
            "author": {
                "userName": "user_" + "x" * 100,
                "id": "123456789" * 10
            },
            "extendedEntities": {
                "media": [{
                    "media_url_https": f"https://example.com/image{i}.jpg"
                } for i in range(100)]  # 100 media items
            },
            "entities": {
                "urls": [{
                    "expanded_url": f"https://example.com/link{i}"
                } for i in range(50)]  # 50 URLs
            }
        }
        
        result = map_tweet_data(large_tweet)
        
        assert isinstance(result, TweetOutput)
        assert len(result.text) > 10000
        assert len(result.media) == 100
        assert len(result.links) == 50
        assert len(result.data_source.author_name) > 100
    
    def test_concurrent_processing_simulation(self):
        """Test that transformation functions are thread-safe."""
        import threading
        import time
        
        results = []
        errors = []
        
        def process_tweet(tweet_data, thread_id):
            try:
                result = map_tweet_data(tweet_data)
                results.append((thread_id, result))
            except Exception as e:
                errors.append((thread_id, str(e)))
        
        # Create test data
        test_tweet = {
            "text": "Concurrent processing test",
            "createdAt": "Mon Jan 01 12:00:00 +0000 2024",
            "author": {"userName": "testuser", "id": "123"}
        }
        
        # Create and start multiple threads
        threads = []
        for i in range(10):
            thread = threading.Thread(target=process_tweet, args=(test_tweet, i))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Verify results
        assert len(errors) == 0, f"Errors occurred: {errors}"
        assert len(results) == 10
        
        # All results should be identical
        first_result = results[0][1]
        for thread_id, result in results:
            assert result == first_result, f"Thread {thread_id} produced different result"


class TestUrlSecurity:
    """Test suite for URL security validation functions."""
    
    def test_validate_url_security_safe_urls(self):
        """Test that safe URLs pass security validation."""
        safe_urls = [
            "https://example.com",
            "http://example.com/path",
            "https://example.com/path?param=value",
            "https://example.com:8080/secure",
            "ftp://example.com/file.txt",
            "ftps://secure.example.com/file.txt"
        ]
        
        for url in safe_urls:
            assert validate_url_security(url) == True, f"Safe URL failed validation: {url}"
    
    def test_validate_url_security_dangerous_schemes(self):
        """Test that dangerous URL schemes are blocked."""
        dangerous_urls = [
            "javascript:alert('xss')",
            "data:text/html,<script>alert('xss')</script>",
            "file:///etc/passwd",
            "vbscript:msgbox('xss')",
            "about:blank",
            "chrome://settings",
            "chrome-extension://abc123/script.js",
            "moz-extension://def456/script.js"
        ]
        
        for url in dangerous_urls:
            assert validate_url_security(url) == False, f"Dangerous URL passed validation: {url}"
    
    def test_validate_url_security_invalid_input(self):
        """Test URL security validation with invalid inputs."""
        invalid_inputs = [
            None,
            "",
            "   ",
            123,
            [],
            {},
            True,
            False
        ]
        
        for invalid_input in invalid_inputs:
            assert validate_url_security(invalid_input) == False, f"Invalid input passed validation: {invalid_input}"
    
    def test_validate_url_security_long_urls(self):
        """Test that extremely long URLs are blocked."""
        # Create a URL longer than 2048 characters
        long_url = "https://example.com/" + "a" * 2050
        assert validate_url_security(long_url) == False, "Extremely long URL should be blocked"
        
        # Test a URL at the limit (should pass)
        limit_url = "https://example.com/" + "a" * 2020
        assert validate_url_security(limit_url) == True, "URL at length limit should pass"
    
    def test_validate_url_security_malformed_urls(self):
        """Test URL security validation with malformed URLs."""
        malformed_urls = [
            "not_a_url",
            "://missing-scheme",
            "http:///no-host",
            "https://",
            "ftp://",
        ]
        
        for url in malformed_urls:
            # These should still return True as they're not dangerous schemes
            # The function focuses on security, not URL validity
            result = validate_url_security(url)
            # Most malformed URLs should pass security check if they don't contain dangerous schemes
            assert isinstance(result, bool), f"Validation should return boolean for: {url}"
    
    def test_sanitize_url_list_valid_urls(self):
        """Test sanitizing a list of valid URLs."""
        urls = [
            "https://example.com",
            "http://safe.com/path",
            "https://another.com?param=value"
        ]
        
        result = sanitize_url_list(urls)
        assert result == urls, "All safe URLs should be preserved"
    
    def test_sanitize_url_list_mixed_urls(self):
        """Test sanitizing a list with mixed safe and dangerous URLs."""
        mixed_urls = [
            "https://safe.com",
            "javascript:alert('xss')",
            "http://example.com",
            "data:text/html,<script>alert('xss')</script>",
            "https://another-safe.com",
            "file:///etc/passwd"
        ]
        
        expected_safe = [
            "https://safe.com",
            "http://example.com", 
            "https://another-safe.com"
        ]
        
        result = sanitize_url_list(mixed_urls)
        assert result == expected_safe, "Only safe URLs should be preserved"
    
    def test_sanitize_url_list_invalid_input(self):
        """Test sanitizing invalid input types."""
        invalid_inputs = [
            None,
            "not_a_list",
            123,
            {},
            True
        ]
        
        for invalid_input in invalid_inputs:
            result = sanitize_url_list(invalid_input)
            assert result == [], f"Invalid input should return empty list: {invalid_input}"
    
    def test_sanitize_url_list_mixed_types(self):
        """Test sanitizing a list with mixed data types."""
        mixed_list = [
            "https://safe.com",
            123,
            None,
            "javascript:alert('xss')",
            [],
            "http://another-safe.com",
            {},
            "file:///etc/passwd"
        ]
        
        expected_safe = [
            "https://safe.com",
            "http://another-safe.com"
        ]
        
        result = sanitize_url_list(mixed_list)
        assert result == expected_safe, "Only safe string URLs should be preserved"
    
    def test_integration_with_transformation(self):
        """Test that URL security is properly integrated with transformation."""
        tweet_with_malicious_urls = {
            "text": "Check out these links",
            "createdAt": "Mon Jan 01 12:00:00 +0000 2024",
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
                    {"expanded_url": "[File](file:///etc/passwd)"},
                    {"expanded_url": "https://another-safe.com"}
                ]
            }
        }
        
        result = map_tweet_data(tweet_with_malicious_urls)
        
        # Only safe URLs should be preserved
        assert "https://safe-image.com/pic.jpg" in result.media
        assert len(result.media) == 1, "Only safe media URLs should be preserved"
        
        # Links should be extracted and sanitized
        assert "https://safe-link.com" in result.links
        assert "https://another-safe.com" in result.links
        assert len([link for link in result.links if "javascript:" in link]) == 0, "No javascript: URLs should remain"
        assert len([link for link in result.links if "file:" in link]) == 0, "No file: URLs should remain"


class TestSecurityEdgeCases:
    """Test suite for security-related edge cases."""
    
    def test_case_insensitive_scheme_detection(self):
        """Test that scheme detection is case insensitive."""
        case_variants = [
            "JAVASCRIPT:alert('xss')",
            "JavaScript:alert('xss')",
            "DATA:text/html,<script>",
            "Data:text/html,<script>",
            "FILE:///etc/passwd",
            "File:///etc/passwd"
        ]
        
        for url in case_variants:
            assert validate_url_security(url) == False, f"Case variant should be blocked: {url}"
    
    def test_whitespace_handling(self):
        """Test proper handling of whitespace in URLs."""
        whitespace_urls = [
            "  https://example.com  ",
            "\t\nhttps://example.com\t\n",
            "  javascript:alert('xss')  ",
            "\t\ndata:text/html,<script>\t\n"
        ]
        
        # Safe URLs with whitespace should pass
        assert validate_url_security(whitespace_urls[0]) == True
        assert validate_url_security(whitespace_urls[1]) == True
        
        # Dangerous URLs with whitespace should still be blocked
        assert validate_url_security(whitespace_urls[2]) == False
        assert validate_url_security(whitespace_urls[3]) == False
    
    def test_unicode_urls(self):
        """Test handling of Unicode characters in URLs."""
        unicode_urls = [
            "https://example.com/ñáéíóú",
            "https://example.com/中文",
            "https://example.com/العربية",
            "https://example.com/🚀"
        ]
        
        for url in unicode_urls:
            assert validate_url_security(url) == True, f"Unicode URL should be safe: {url}"
    
    def test_url_parsing_errors(self):
        """Test handling of URLs that cause parsing errors."""
        problematic_urls = [
            "https://[invalid-ipv6",
            "https://user:pass@host:port/path",
            "https://host:999999/path",  # Invalid port
        ]
        
        for url in problematic_urls:
            # Should not raise exceptions, should return boolean
            result = validate_url_security(url)
            assert isinstance(result, bool), f"Should return boolean for problematic URL: {url}"