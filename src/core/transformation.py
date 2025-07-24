"""Data transformation module for Twitter data processing.

This module provides functions to transform raw Twitter data into standardized
schema-validated objects, including datetime parsing, URL extraction, and
security validation.
"""

import json
import re
from datetime import datetime
from typing import Dict, Any, List, Union, Optional
from urllib.parse import urlparse
from ..models.schemas import TweetOutput, DataSource

def extract_url(text: str) -> str:
    """Extract URL from markdown-style links with security validation.
    
    Args:
        text: Input text that may contain markdown-style links [text](url)
        
    Returns:
        Extracted URL if markdown pattern found, otherwise original text
        
    Note:
        This function extracts URLs but does not validate them for security.
        URL validation should be performed by calling validate_url_security().
    """
    if not isinstance(text, str):
        return ""
    
    try:
        match = re.search(r'\[.*?\]\((.*?)\)', text)
        if match:
            url = match.group(1)
            return url.strip() if url else ""
        else:
            return text
    except (re.error, AttributeError) as e:
        # Log regex errors but return original text
        return text


def validate_url_security(url: str) -> bool:
    """Validate URL for security concerns.
    
    Args:
        url: URL string to validate
        
    Returns:
        True if URL appears safe, False if potentially malicious
        
    Security checks:
        - Blocks javascript: and data: schemes
        - Blocks file: protocol
        - Validates URL length
        - Checks for common malicious patterns
    """
    if not isinstance(url, str) or not url.strip():
        return False
    
    url = url.strip().lower()
    
    # Block dangerous schemes
    dangerous_schemes = [
        'javascript:',
        'data:',
        'file:',
        'vbscript:',
        'about:',
        'chrome:',
        'chrome-extension:',
        'moz-extension:'
    ]
    
    for scheme in dangerous_schemes:
        if url.startswith(scheme):
            return False
    
    # Check URL length (prevent extremely long URLs)
    if len(url) > 2048:  # Standard browser URL length limit
        return False
    
    # Basic URL structure validation
    try:
        parsed = urlparse(url)
        # Ensure scheme is http or https
        if parsed.scheme and parsed.scheme not in ['http', 'https', 'ftp', 'ftps']:
            return False
    except Exception:
        return False
    
    return True


def sanitize_url_list(urls: List[str]) -> List[str]:
    """Sanitize a list of URLs by filtering out potentially malicious ones.
    
    Args:
        urls: List of URL strings to sanitize
        
    Returns:
        List of URLs that passed security validation
    """
    if not isinstance(urls, list):
        return []
    
    sanitized = []
    for url in urls:
        if isinstance(url, str) and validate_url_security(url):
            sanitized.append(url)
    
    return sanitized

def parse_twitter_datetime(datetime_str: Union[str, None]) -> int:
    """Convert Twitter datetime string to unix timestamp.
    
    Args:
        datetime_str: Twitter datetime in format 'Sat Jul 19 22:54:07 +0000 2025'
                     Can be None or non-string type
    
    Returns:
        Unix timestamp as integer, or 0 if parsing fails
        
    Raises:
        No exceptions - all errors are handled gracefully
    """
    # Handle None or non-string input
    if not isinstance(datetime_str, str) or not datetime_str.strip():
        return 0
    
    try:
        # Parse Twitter datetime format: "Sat Jul 19 22:54:07 +0000 2025"
        dt = datetime.strptime(datetime_str.strip(), "%a %b %d %H:%M:%S %z %Y")
        return int(dt.timestamp())
    except (ValueError, TypeError, AttributeError) as e:
        # Return 0 if parsing fails for any reason
        return 0

def map_tweet_data(tweet: Dict[str, Any]) -> TweetOutput:
    """Transform raw tweet data into standardized TweetOutput schema.
    
    Args:
        tweet: Raw tweet data dictionary from Twitter API
        
    Returns:
        TweetOutput object with validated and transformed data
        
    Raises:
        No exceptions - all errors are handled gracefully with fallback values
        
    Note:
        This function applies security validation to extracted URLs and handles
        malformed input data gracefully by using default values.
    """
    # Validate input
    if not isinstance(tweet, dict):
        tweet = {}
    
    # Extract timestamp and convert to unix timestamp
    created_at_str = tweet.get("createdAt", "")
    createdAt = parse_twitter_datetime(created_at_str)

    # Extract and validate text content
    text = tweet.get("text", "")
    if not isinstance(text, str):
        text = ""

    # Extract media URLs from extendedEntities with error handling
    media = []
    try:
        extended_entities = tweet.get("extendedEntities", {})
        if isinstance(extended_entities, dict):
            media_entities = extended_entities.get("media", [])
            if isinstance(media_entities, list):
                raw_media = []
                for item in media_entities:
                    if isinstance(item, dict) and "media_url_https" in item:
                        media_url = item["media_url_https"]
                        if isinstance(media_url, str):
                            raw_media.append(media_url)
                # Apply security validation
                media = sanitize_url_list(raw_media)
    except (AttributeError, TypeError, KeyError):
        media = []

    # Extract URLs from entities with error handling and security validation
    links = []
    try:
        entities = tweet.get("entities", {})
        if isinstance(entities, dict):
            url_entities = entities.get("urls", [])
            if isinstance(url_entities, list):
                raw_links = []
                for item in url_entities:
                    if isinstance(item, dict) and "expanded_url" in item:
                        expanded_url = item["expanded_url"]
                        if isinstance(expanded_url, str):
                            extracted_url = extract_url(expanded_url)
                            raw_links.append(extracted_url)
                # Apply security validation
                links = sanitize_url_list(raw_links)
    except (AttributeError, TypeError, KeyError):
        links = []

    # Extract author information with error handling
    author_name = ""
    author_id = ""
    try:
        author = tweet.get("author", {})
        if isinstance(author, dict):
            author_name = author.get("userName", "")
            author_id = author.get("id", "")
            # Ensure author fields are strings
            if not isinstance(author_name, str):
                author_name = ""
            if not isinstance(author_id, str):
                author_id = ""
    except (AttributeError, TypeError):
        pass

    return TweetOutput(
        data_source=DataSource(
            name="Twitter",
            author_name=author_name,
            author_id=author_id
        ),
        createdAt=createdAt,
        text=text,
        media=media,
        links=links
    )
