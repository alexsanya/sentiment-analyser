import json
import pytest
from pathlib import Path
from transformation import map_tweet_data
from schemas import TweetOutput, DataSource

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