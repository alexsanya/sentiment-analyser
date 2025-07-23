import json
import re
from datetime import datetime
from schemas import TweetOutput, DataSource

def extract_url(text) -> str:
    match = re.search(r'\[.*?\]\((.*?)\)', text)
    if match:
        url = match.group(1)
        return url
    else:
        return text

def parse_twitter_datetime(datetime_str: str) -> int:
    """Convert Twitter datetime string to unix timestamp.
    
    Args:
        datetime_str: Twitter datetime in format 'Sat Jul 19 22:54:07 +0000 2025'
    
    Returns:
        Unix timestamp as integer
    """
    try:
        # Parse Twitter datetime format: "Sat Jul 19 22:54:07 +0000 2025"
        dt = datetime.strptime(datetime_str, "%a %b %d %H:%M:%S %z %Y")
        return int(dt.timestamp())
    except (ValueError, TypeError):
        # Return 0 if parsing fails
        return 0

def map_tweet_data(tweet: dict) -> TweetOutput:

    # Extract timestamp and convert to unix timestamp
    created_at_str = tweet.get("createdAt", "")
    createdAt = parse_twitter_datetime(created_at_str)

    # Extract text
    text = tweet.get("text", "")

    # Extract media URLs from extendedEntities
    media_entities = tweet.get("extendedEntities", {}).get("media", [])
    media = [item["media_url_https"] for item in media_entities]

    # Extract display names from entities.urls
    url_entities = tweet.get("entities", {}).get("urls", [])
    links = [extract_url(item["expanded_url"]) for item in url_entities if "expanded_url" in item]

    return TweetOutput(
        data_source=DataSource(
            name="Twitter",
            author_name=tweet.get("author", {}).get("userName", ""),
            author_id=tweet.get("author", {}).get("id", "")
        ),
        createdAt=createdAt,
        text=text,
        media=media,
        links=links
    )
