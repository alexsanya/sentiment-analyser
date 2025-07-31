"""Sentiment analysis module for tweet token detection.

This module provides AI-powered agents for analyzing tweets to detect 
cryptocurrency token announcements in text, images, and linked URLs.
"""

import asyncio
import re
import os
from typing import List, Optional, Dict, Any, Union
from datetime import datetime
from enum import Enum

# Import order is important to avoid conflicts
import base58
import nest_asyncio
from pydantic import BaseModel, field_validator, ValidationError
from pydantic import Field as PydanticField  # Alias to avoid conflicts
from pydantic import HttpUrl

# Then import PydanticAI components
from pydantic_ai import Agent, ImageUrl
from pydantic_ai.mcp import MCPServerSSE

from ..models.schemas import TokenDetails, NoTokenFound, RelseaseAnnouncementWithoutDetails, SentimentAnalysisResult
from ..config.logging_config import get_logger

logger = get_logger(__name__)

# Apply nest_asyncio for Jupyter compatibility
nest_asyncio.apply()


def is_valid_solana_address(address: str) -> bool:
    """
    Verify if a string is a valid Solana address (token or otherwise).
    
    Args:
        address (str): The address string to validate
        
    Returns:
        bool: True if valid Solana address, False otherwise
    """
    if not isinstance(address, str):
        return False
    
    # Check length (Solana addresses are typically 32-44 characters)
    if len(address) < 32 or len(address) > 44:
        return False
    
    # Check if it contains only valid base58 characters
    # Base58 alphabet: 123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz
    base58_pattern = r'^[1-9A-HJ-NP-Za-km-z]+$'
    if not re.match(base58_pattern, address):
        return False
    
    try:
        # Attempt to decode the base58 string
        decoded = base58.b58decode(address)
        
        # Solana addresses should decode to exactly 32 bytes
        if len(decoded) != 32:
            return False
            
        return True
    except Exception:
        return False


def is_valid_evm_address(address: str) -> bool:
    """
    Validates if the given address is a valid EVM blockchain address.
    
    Args:
        address (str): The address string to validate
        
    Returns:
        bool: True if the address is valid, False otherwise
        
    Examples:
        >>> is_valid_evm_address("0x742d35Cc6765C0532575f5A2c0a078Df8a2D4e5e")
        True
        >>> is_valid_evm_address("0xinvalid")
        False
        >>> is_valid_evm_address("742d35Cc6765C0532575f5A2c0a078Df8a2D4e5e")
        False
    """
    if not isinstance(address, str):
        return False
    
    # EVM address pattern: 0x followed by exactly 40 hexadecimal characters
    pattern = r'^0x[a-fA-F0-9]{40}$'
    
    return bool(re.match(pattern, address))


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


class TextSearchAgent:
    """
    A PydanticAI agent that analyzes text and searches for new token release announcements 
    """
    
    def __init__(self, model_name: str = "openai:gpt-4o"):
        """
        Initialize the agent
        
        Args:
            model_name: The LLM model to use (default: gpt-4o)
        """
        self.agent = Agent[None, SentimentAnalysisResult](
            model=model_name,
            output_type=SentimentAnalysisResult,
            retries=4,
            system_prompt=(
                "Your task is scan given text and search for announcement of a new token/coin release.",
                "Parse the token address using Regex Pattern and blockchain it deployed to.",
                "If blockchain is not found, determine it based on address Regex Pattern (EVM/Solana).",
                CHAIN_IDS_LIST,
                CONTRACT_ADDRESS_PATTERNS
            )
        )
    
    async def run(self, text: str) -> SentimentAnalysisResult:
        """
        Process text to detect token announcements
        Args:
            text: The given text
            
        Returns:
            The token data if found
        """
        try:
            result = await self.agent.run(text)
            logger.info("TextSearchAgent completed analysis", text_length=len(text))
            return result.output
        except Exception as e:
            logger.error("TextSearchAgent failed", error=str(e), text_length=len(text))
            return NoTokenFound()


class ImageSearchAgent:
    """
    A PydanticAI agent that analyzes images and searches for new token release announcements 
    """
    
    def __init__(self, model_name: str = "openai:gpt-4o"):
        """
        Initialize the agent
        
        Args:
            model_name: The LLM model to use (default: gpt-4o)
        """
        self.agent = Agent[None, SentimentAnalysisResult](
            model=model_name,
            output_type=SentimentAnalysisResult,
            retries=4,
            system_prompt=(
                "You are text pattern recognition agent that works with images",
                "Your task is to scan every text you found in given image and search for announcement of a new token/coin release.",
                "Parse the token address using Regex Pattern and blockchain it deployed to.",
                "If blockchain is not found, determine it based on address Regex Pattern (EVM/Solana).",
                CHAIN_IDS_LIST,
                CONTRACT_ADDRESS_PATTERNS
            )
        )
    
    async def run(self, image_url: str) -> SentimentAnalysisResult:
        """
        Process image to detect token announcements
        Args:
            image_url: The url of an image
            
        Returns:
            The token data if found
        """
        try:
            result = await self.agent.run([ImageUrl(url=image_url)])
            logger.info("ImageSearchAgent completed analysis", image_url=image_url)
            return result.output
        except Exception as e:
            logger.error("ImageSearchAgent failed", error=str(e), image_url=image_url)
            return NoTokenFound()


class FirecrawlAgent:
    """
    A PydanticAI agent that uses Firecrawl MCP server for web scraping capabilities
    """
    
    def __init__(self, model_name: str = "openai:gpt-4o", firecrawl_url: str = "http://localhost:3000/sse"):
        """
        Initialize the agent with Firecrawl MCP server connection.
        
        Args:
            model_name: The LLM model to use (default: gpt-4o)
            firecrawl_url: The Firecrawl MCP server URL
        """
        # Create MCP server connection to Firecrawl running in SSE mode
        self.firecrawl_server = MCPServerSSE(
            url=firecrawl_url,  # Configurable SSE endpoint for Firecrawl MCP
            tool_prefix='firecrawl'  # Optional: prefix tools to avoid naming conflicts
        )
        
        # Initialize the agent with the MCP server
        self.agent = Agent[None, SentimentAnalysisResult](
            model=model_name,
            output_type=SentimentAnalysisResult,
            retries=4,
            system_prompt=(
                "You are a web scraping assistant powered by Firecrawl. ",
                "Your task is to scrape provided webpage and search if it contain an announcement of a new token/coin release.",
                "Parse the token address and blockchain it deployed to",
                "If blockchain is not found determine it based on address fromat(EVM/Solana).",
                CHAIN_IDS_LIST,
                CONTRACT_ADDRESS_PATTERNS
            ),
            mcp_servers=[self.firecrawl_server]
        )
    
    async def run(self, url: str) -> SentimentAnalysisResult:
        """
        Process a URL using the agent with Firecrawl capabilities.
        
        Args:
            url: The url to crawl
            
        Returns:
            The token data if found
        """
        try:
            async with self.agent.run_mcp_servers():
                result = await self.agent.run(url)
                logger.info("FirecrawlAgent completed analysis", url=url)
                return result.output
        except Exception as e:
            logger.error("FirecrawlAgent failed", error=str(e), url=url)
            return NoTokenFound()


def merge_agent_results(results: List[SentimentAnalysisResult]) -> SentimentAnalysisResult:
    """
    Merge multiple agent analysis results into a single result.
    
    Args:
        results: List of analysis results from different agents
        
    Returns:
        Single merged result
        
    Note:
        This function is currently empty as requested - implementation will be added later
    """
    # TODO: Implement result merging logic
    # Priority: TokenDetails > RelseaseAnnouncementWithoutDetails > NoTokenFound
    # Combine multiple TokenDetails if found
    # Return most confident/complete result
    
    # For now, return first non-NoTokenFound result or NoTokenFound if all are NoTokenFound
    for result in results:
        if not isinstance(result, NoTokenFound):
            return result
    
    return NoTokenFound()


def get_sentiment_analyzer_config() -> Dict[str, Any]:
    """
    Get sentiment analyzer configuration from environment variables.
    
    Returns:
        Configuration dictionary
    """
    return {
        'ai_model_name': os.getenv('AI_MODEL_NAME', 'openai:gpt-4o'),
        'firecrawl_mcp_server_url': os.getenv('FIRECRAWL_MCP_SERVER_URL', 'http://localhost:3000/sse'),
        'max_concurrent_analysis': int(os.getenv('MAX_CONCURRENT_ANALYSIS', '5'))
    }