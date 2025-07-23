import json
import re
from schemas import TweetOutput

def extract_url(text) -> str:
    match = re.search(r'\[.*?\]\((.*?)\)', text)
    if match:
        url = match.group(1)
        return url
    else:
        return text

def map_tweet_data(data) -> TweetOutput:
    tweet = data["tweets"][0]

    # Extract timestamp
    timestamp = data.get("timestamp")

    # Extract text
    text = tweet.get("text", "")

    # Extract media URLs from extendedEntities
    media_entities = tweet.get("extendedEntities", {}).get("media", [])
    media = [item["expanded_url"] for item in media_entities]

    # Extract display names from entities.urls
    url_entities = tweet.get("entities", {}).get("urls", [])
    links = [extract_url(item["expanded_url"]) for item in url_entities if "expanded_url" in item]

    return TweetOutput(
        timestamp=timestamp,
        text=text,
        media=media,
        links=links
    )
