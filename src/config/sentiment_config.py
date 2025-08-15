"""Configuration for sentiment analysis and token detection."""

import os
from dataclasses import dataclass
from typing import Tuple


# Agent retry configuration
DEFAULT_AGENT_RETRIES = 3

# Default configuration values
DEFAULT_MODEL_NAME = "openai:gpt-4o"
DEFAULT_FIRECRAWL_URL = "http://localhost:3000/sse"
DEFAULT_MAX_CONCURRENT = 5

# Workflow control defaults
DEFAULT_TOPIC_ANALYSIS_ENABLED = True
DEFAULT_TOKEN_DETECTION_ENABLED = True
DEFAULT_PEACE_TALKS_TOPIC_ENABLED = True

# Chain IDs and patterns for blockchain identification
CHAIN_IDS_LIST = """
Here's a markdown table with chain IDs and names for the most popular public blockchains:

| Chain ID | Chain Name |
|----------|------------|
| 1 | Ethereum Mainnet |
| 56 | BNB Smart Chain (BSC) |
| 137 | Polygon |
| 43114 | Avalanche C-Chain |
| 250 | Fantom Opera |
| 42161 | Arbitrum One |
| 10 | Optimism |
| 25 | Cronos |
| 100 | Gnosis Chain (xDai) |
| 1284 | Moonbeam |
| 1285 | Moonriver |
| 42220 | Celo |
| 128 | Huobi ECO Chain (HECO) |
| 66 | OKExChain |
| 321 | KuCoin Community Chain (KCC) |
| 1666600000 | Harmony One Shard 0 |
| 288 | Boba Network |
| 1313161554 | Aurora |
| 8217 | Klaytn Cypress |
| 82 | Meter |
| 1088 | Metis Andromeda |
| 199 | BitTorrent Chain |
| 324 | zkSync Era |
| 5000 | Mantle |
| 59144 | Linea |
| 534352 | Scroll |
| 8453 | Base |

These are the most commonly used public blockchains with their respective chain IDs as defined in the EIP-155 standard for Ethereum-compatible networks.
"""

CONTRACT_ADDRESS_PATTERNS = """
| Blockchain Type                    | Address Format | Regex Pattern                   | Description                                      |
| ---------------------------------- | -------------- | ------------------------------- | ------------------------------------------------ |
| EVM (Ethereum, BSC, Polygon, etc.) | Hexadecimal    | `^0x[a-fA-F0-9]{40}$`           | 20-byte hex string with "0x" prefix              |
| EVM (Case-insensitive)             | Hexadecimal    | `^0x[a-fA-F0-9]{40}$`           | Standard EVM address format                      |
| EVM (Checksummed)                  | Mixed Case     | `^0x[a-fA-F0-9]{40}$`           | EIP-55 checksummed (case matters for validation) |
| Solana                             | Base58         | `^[1-9A-HJ-NP-Za-km-z]{32,44}$` | Base58 encoded, 32-44 characters                 |
| Solana (Strict)                    | Base58         | `^[1-9A-HJ-NP-Za-km-z]{43,44}$` | More precise length range                        |
| Solana (Most Common)               | Base58         | `^[1-9A-HJ-NP-Za-km-z]{44}$`    | Exactly 44 characters (most common)              |
"""

# System prompts for different agent types
TEXT_SEARCH_PROMPT: Tuple[str, ...] = (
    "Your task is scan given text and search for announcement of a new token/coin release.",
    "Parse the token address using Regex Pattern and blockchain it deployed to.",
    "If blockchain is not found, determine it based on address Regex Pattern (EVM/Solana).",
    CHAIN_IDS_LIST,
    CONTRACT_ADDRESS_PATTERNS
)

IMAGE_SEARCH_PROMPT: Tuple[str, ...] = (
    "You are text pattern recognition agent that works with images",
    "Your task is to scan every text you found in given image and search for announcement of a new token/coin release.",
    "Parse the token address using Regex Pattern and blockchain it deployed to.",
    "If blockchain is not found, determine it based on address Regex Pattern (EVM/Solana).",
    CHAIN_IDS_LIST,
    CONTRACT_ADDRESS_PATTERNS
)

FIRECRAWL_SEARCH_PROMPT: Tuple[str, ...] = (
    "You are a web scraping assistant powered by Firecrawl. ",
    "Your task is to scrape provided webpage and search if it contain an announcement of a new token/coin release.",
    "Parse the token address and blockchain it deployed to",
    "If blockchain is not found determine it based on address fromat(EVM/Solana).",
    CHAIN_IDS_LIST,
    CONTRACT_ADDRESS_PATTERNS
)


@dataclass
class SentimentAnalysisConfig:
    """Configuration for sentiment analysis and topic analysis."""
    model_name: str = DEFAULT_MODEL_NAME
    firecrawl_mcp_server_url: str = DEFAULT_FIRECRAWL_URL
    max_concurrent_analysis: int = DEFAULT_MAX_CONCURRENT
    agent_retries: int = DEFAULT_AGENT_RETRIES
    
    # Workflow control settings
    topic_analysis_enabled: bool = DEFAULT_TOPIC_ANALYSIS_ENABLED
    token_detection_enabled: bool = DEFAULT_TOKEN_DETECTION_ENABLED
    peace_talks_topic_enabled: bool = DEFAULT_PEACE_TALKS_TOPIC_ENABLED


def get_sentiment_config() -> SentimentAnalysisConfig:
    """
    Get sentiment analyzer configuration from environment variables.
    
    Returns:
        Configuration object with values from environment variables or defaults
    """
    def str_to_bool(value: str) -> bool:
        """Convert string environment variable to boolean."""
        return value.lower() in ('true', '1', 'yes', 'on')
    
    return SentimentAnalysisConfig(
        model_name=os.getenv("SENTIMENT_MODEL_NAME", DEFAULT_MODEL_NAME),
        firecrawl_mcp_server_url=os.getenv("FIRECRAWL_MCP_SERVER_URL", DEFAULT_FIRECRAWL_URL),
        max_concurrent_analysis=int(os.getenv("MAX_CONCURRENT_ANALYSIS", str(DEFAULT_MAX_CONCURRENT))),
        agent_retries=int(os.getenv("AGENT_RETRIES", str(DEFAULT_AGENT_RETRIES))),
        
        # Workflow control from environment variables
        topic_analysis_enabled=str_to_bool(os.getenv("TOPIC_ANALYSIS_ENABLED", str(DEFAULT_TOPIC_ANALYSIS_ENABLED))),
        token_detection_enabled=str_to_bool(os.getenv("TOKEN_DETECTION_ENABLED", str(DEFAULT_TOKEN_DETECTION_ENABLED))),
        peace_talks_topic_enabled=str_to_bool(os.getenv("PEACE_TALKS_TOPIC_ENABLED", str(DEFAULT_PEACE_TALKS_TOPIC_ENABLED)))
    )