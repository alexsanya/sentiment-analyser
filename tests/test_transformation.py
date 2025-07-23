import json
import pytest
from pathlib import Path
from transformation import map_tweet_data, TweetOutput

def test_map_tweet_data_snapshot():
    """Snapshot test for map_tweet_data function with tweet-sample.json"""
    # Load sample data
    sample_file = Path(__file__).parent.parent / "tweet-sample.json"
    with open(sample_file, 'r') as f:
        input_data = json.load(f)
    
    # Transform the data
    result = map_tweet_data(input_data)
    
    # Expected output
    expected = TweetOutput(
        timestamp=1752965652370,
        text="My Rules of engagement\nReed more in my post: https://t.co/tKo1tfckav https://t.co/Khhm0sufWd",
        media=["https://twitter.com/alexsanyakoval/status/1946705136438431748/photo/1"],
        links=["https://www.linkedin.com/posts/kovalas_candidateexperience-hiring-techrecruiting-activity-7351630837789929476-DzM1?utm_source=share&utm_medium=member_desktop&rcm=ACoAAAxBctkB-IBy_pKCQ-_f0LrBMyhGZ5Lw2Tg"]  # extract_url returns empty string for display_url format
    )
    
    assert result == expected