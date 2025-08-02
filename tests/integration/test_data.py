"""Test data extracted from sentiment-analyze.ipynb notebook."""

# Text samples from the notebook for TextSearchAgent testing
TEXT_SAMPLES = [
    # Test case 0: Explicit chain info (Polygon), EVM address
    'My new token on Polygon blockchain: 0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48. Buy it now!',
    
    # Test case 1: No chain info, EVM address (should infer Ethereum)
    'My new token is live: 0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48. Happpy trading!',
    
    # Test case 2: Explicit chain info (Solana), Solana address
    'My new token is live on Solana Blockchain: Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB. Buy now!',
    
    # Test case 3: No chain info, Solana address (should infer Solana)
    'My new token is live: Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB. Buy now!',
    
    # Test case 4: No announcement, no token
    'Join my webinar tomorrow!',
    
    # Test case 5: No announcement, Solana address (purchase, not release)
    'Just bought a bad of Trump coin (6p6xgHyF7AeE6TZkSmFsko444wqoP15icUSqi2jfGiPN)',
    
    # Test case 6: No announcement, Solana address with explicit chain mention
    'Just bought a bad of Trump coin on solana: (6p6xgHyF7AeE6TZkSmFsko444wqoP15icUSqi2jfGiPN)',
    
    # Test case 7: Duplicate of case 6 (same text from notebook)
    'Just bought a bad of Trump coin on solana: (6p6xgHyF7AeE6TZkSmFsko444wqoP15icUSqi2jfGiPN)',
    
    # Test case 8: No announcement, EVM address (accumulating, not release)
    'Accumulationg Bonk: 0x1151CB3d861920e07a38e03eEAd12C32178567F6',
    
    # Test case 9: No announcement, EVM address with explicit ETH mainnet mention
    'Accumulationg Bonk on ETH mainnet: 0x1151CB3d861920e07a38e03eEAd12C32178567F6',
    
    # Test case 10: Release announcement without token details
    'My new token just released - follow the link to buy!'
]

# Image URLs from the notebook for ImageSearchAgent testing
IMAGE_URLS = [
    # Trump token announcement image
    "https://pbs.twimg.com/media/GhivrlDWAAA7Ex3?format=jpg&name=medium",
    
    # Melania token announcement image
    "https://lh7-rt.googleusercontent.com/docsz/AD_4nXcNy9kHtzbuH-N-F9B8zy7oqkUobYkzXWhAKqI4qXP7JSIihBNHhJJfz-1gmvJDnxYiTPHRinIe8wBQ3VMBZU0aGxyb6U8k6SWGU5NleZg2AVGyxI7WuyJGcUJ73oG_THgfF_bX?key=qxx7aSSAQfwoulEynZFGQMDH",
    
    # Non-announcement image
    "https://bitcoinworld.co.in/wp-content/uploads/Melania-Trumps-Meme-Coin-MELANIA-B.jpg"
]

# Web URLs from the notebook for FirecrawlAgent testing
WEB_URLS = [
    # Token announcement website
    "https://flockerz.com/",
    
    # Another token announcement website
    "https://gettrumpmemes.com/"
]

# Test case descriptions for better test naming
TEXT_SAMPLE_DESCRIPTIONS = [
    "polygon_explicit_chain_evm_address",
    "no_chain_evm_address_infer_ethereum", 
    "solana_explicit_chain_solana_address",
    "no_chain_solana_address_infer_solana",
    "no_announcement_no_token",
    "purchase_not_release_solana_address",
    "purchase_explicit_solana_chain",
    "purchase_explicit_solana_chain_duplicate",
    "accumulating_not_release_evm_address",
    "accumulating_explicit_eth_mainnet",
    "release_announcement_no_details"
]

IMAGE_DESCRIPTIONS = [
    "trump_token_announcement",
    "melania_token_announcement", 
    "non_announcement_image"
]

WEB_DESCRIPTIONS = [
    "flockerz_token_website",
    "trump_memes_website"
]