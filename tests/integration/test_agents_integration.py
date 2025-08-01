"""Integration tests for PydanticAI agents with real OpenAI API calls.

These tests make real API calls to OpenAI and use snapshot testing to verify
the structured responses from each agent. Requires OPENAI_API_KEY environment variable.
"""

import os
import pytest
import asyncio
from syrupy import SnapshotAssertion

from src.config.logfire_config import initialize_logfire
from src.core.agents.text_search_agent import TextSearchAgent
from src.core.agents.image_search_agent import ImageSearchAgent
from src.core.agents.firecrawl_agent import FirecrawlAgent
from src.models.schemas import SentimentAnalysisResult, TokenDetails
from dotenv import load_dotenv
from src.config.logging_config import setup_logging, get_logger

# Initialize Logfire for integration tests
load_dotenv()
initialize_logfire()

setup_logging("development")  # Auto-detects environment
logger = get_logger(__name__)

from .test_data import (
    TEXT_SAMPLES, 
    TEXT_SAMPLE_DESCRIPTIONS,
    IMAGE_URLS,
    IMAGE_DESCRIPTIONS, 
    WEB_URLS,
    WEB_DESCRIPTIONS
)


def serialize_for_snapshot(result):
    """Serialize agent result for snapshot testing, excluding variable fields.
    
    Excludes the 'definition_fragment' field from TokenDetails to ensure
    stable snapshots since this field contains variable text snippets.
    """
    if hasattr(result, 'model_dump'):
        if isinstance(result, TokenDetails):
            return result.model_dump(exclude={'definition_fragment'})
        return result.model_dump()
    else:
        # Fallback for older Pydantic versions
        if hasattr(result, '__class__') and result.__class__.__name__ == 'TokenDetails':
            return result.dict(exclude={'definition_fragment'})
        return result.dict()


# Mark all tests in this module as integration tests
pytestmark = pytest.mark.integration


class TestEnvironmentSetup:
    """Test environment setup and requirements."""
    
    def test_openai_api_key_required(self):
        """Verify OpenAI API key is available."""
        api_key = os.getenv('OPENAI_API_KEY')
        assert api_key is not None, "OPENAI_API_KEY environment variable is required for integration tests"
        assert len(api_key.strip()) > 0, "OPENAI_API_KEY cannot be empty"


@pytest.fixture
def text_search_agent():
    """Create TextSearchAgent instance."""
    return TextSearchAgent()


@pytest.fixture 
def image_search_agent():
    """Create ImageSearchAgent instance."""
    return ImageSearchAgent()


@pytest.fixture
def firecrawl_agent():
    """Create FirecrawlAgent instance."""
    return FirecrawlAgent()


class TestTextSearchAgent:
    """Integration tests for TextSearchAgent with real OpenAI API calls."""
    
    @pytest.mark.asyncio
    @pytest.mark.parametrize("text_sample,description", zip(TEXT_SAMPLES, TEXT_SAMPLE_DESCRIPTIONS))
    async def test_text_analysis(self, text_search_agent: TextSearchAgent, text_sample: str, description: str, snapshot: SnapshotAssertion):
        """Test TextSearchAgent analysis with various text samples."""
        result = await text_search_agent.run(text_sample)
        
        # Verify result is one of the expected types
        assert isinstance(result, SentimentAnalysisResult.__args__)
        
        # Serialize to dict for snapshot comparison (excluding variable fields)
        result_json = serialize_for_snapshot(result)
            
        # Use description in snapshot name for clarity
        assert result_json == snapshot(name=f"text_search_{description}")


class TestImageSearchAgent:
    """Integration tests for ImageSearchAgent with real OpenAI API calls."""
    
    @pytest.mark.asyncio
    @pytest.mark.parametrize("image_url,description", zip(IMAGE_URLS, IMAGE_DESCRIPTIONS))
    async def test_image_analysis(self, image_search_agent: ImageSearchAgent, image_url: str, description: str, snapshot: SnapshotAssertion):
        """Test ImageSearchAgent analysis with various image URLs."""
        result = await image_search_agent.run(image_url)
        
        # Verify result is one of the expected types
        assert isinstance(result, SentimentAnalysisResult.__args__)
        
        # Serialize to dict for snapshot comparison (excluding variable fields)
        result_json = serialize_for_snapshot(result)
            
        # Use description in snapshot name for clarity
        assert result_json == snapshot(name=f"image_search_{description}")


class TestFirecrawlAgent:
    """Integration tests for FirecrawlAgent with real OpenAI API calls.
    
    Note: These tests require a running Firecrawl MCP server at localhost:3000/sse
    """
    
    @pytest.mark.asyncio
    @pytest.mark.parametrize("web_url,description", zip(WEB_URLS, WEB_DESCRIPTIONS))
    async def test_web_scraping_analysis(self, firecrawl_agent: FirecrawlAgent, web_url: str, description: str, snapshot: SnapshotAssertion):
        """Test FirecrawlAgent analysis with web URLs."""
        result = await firecrawl_agent.run(web_url)
        
        # Verify result is one of the expected types
        assert isinstance(result, SentimentAnalysisResult.__args__)
        
        # Serialize to dict for snapshot comparison (excluding variable fields)
        result_json = serialize_for_snapshot(result)
            
        # Use description in snapshot name for clarity
        assert result_json == snapshot(name=f"firecrawl_{description}")


class TestAgentReliability:
    """Tests for agent reliability and error handling."""
    
    @pytest.mark.asyncio
    async def test_text_agent_empty_input(self, text_search_agent: TextSearchAgent, snapshot: SnapshotAssertion):
        """Test TextSearchAgent with empty input."""
        result = await text_search_agent.run("")
        
        result_json = serialize_for_snapshot(result)
            
        assert result_json == snapshot(name="text_search_empty_input")
    
    @pytest.mark.asyncio
    async def test_text_agent_very_long_input(self, text_search_agent: TextSearchAgent, snapshot: SnapshotAssertion):
        """Test TextSearchAgent with very long input."""
        long_text = "This is a test message. " * 100 + "My new token: 0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"
        result = await text_search_agent.run(long_text)
        
        result_json = serialize_for_snapshot(result)
            
        assert result_json == snapshot(name="text_search_very_long_input")


# Individual test methods for easier debugging
class TestIndividualTextCases:
    """Individual test methods for each text case for easier debugging and snapshot management."""
    
    @pytest.mark.asyncio
    async def test_polygon_explicit_chain_evm_address(self, text_search_agent: TextSearchAgent, snapshot: SnapshotAssertion):
        """Test case 0: Explicit Polygon chain with EVM address."""
        text = TEXT_SAMPLES[0]
        result = await text_search_agent.run(text)
        result_json = serialize_for_snapshot(result)
        assert result_json == snapshot
        
    @pytest.mark.asyncio
    async def test_no_chain_evm_address_infer_ethereum(self, text_search_agent: TextSearchAgent, snapshot: SnapshotAssertion):
        """Test case 1: No chain info, EVM address (should infer Ethereum)."""
        text = TEXT_SAMPLES[1]
        result = await text_search_agent.run(text)
        result_json = serialize_for_snapshot(result)
        assert result_json == snapshot
        
    @pytest.mark.asyncio
    async def test_solana_explicit_chain_solana_address(self, text_search_agent: TextSearchAgent, snapshot: SnapshotAssertion):
        """Test case 2: Explicit Solana chain with Solana address."""
        text = TEXT_SAMPLES[2]
        result = await text_search_agent.run(text)
        result_json = serialize_for_snapshot(result)
        assert result_json == snapshot
        
    @pytest.mark.asyncio
    async def test_no_chain_solana_address_infer_solana(self, text_search_agent: TextSearchAgent, snapshot: SnapshotAssertion):
        """Test case 3: No chain info, Solana address (should infer Solana)."""
        text = TEXT_SAMPLES[3]
        result = await text_search_agent.run(text)
        result_json = serialize_for_snapshot(result)
        assert result_json == snapshot
        
    @pytest.mark.asyncio
    async def test_no_announcement_no_token(self, text_search_agent: TextSearchAgent, snapshot: SnapshotAssertion):
        """Test case 4: No announcement, no token."""
        text = TEXT_SAMPLES[4]
        result = await text_search_agent.run(text)
        result_json = serialize_for_snapshot(result)
        assert result_json == snapshot
        
    @pytest.mark.asyncio
    async def test_purchase_not_release_solana_address(self, text_search_agent: TextSearchAgent, snapshot: SnapshotAssertion):
        """Test case 5: Purchase mention, not release (Solana address)."""
        text = TEXT_SAMPLES[5]
        result = await text_search_agent.run(text)
        result_json = serialize_for_snapshot(result)
        assert result_json == snapshot


# Additional individual tests for remaining cases...
class TestIndividualImageCases:
    """Individual test methods for each image case."""
    
    @pytest.mark.asyncio
    async def test_trump_token_announcement(self, image_search_agent: ImageSearchAgent, snapshot: SnapshotAssertion):
        """Test Trump token announcement image."""
        image_url = IMAGE_URLS[0]
        result = await image_search_agent.run(image_url)
        result_json = serialize_for_snapshot(result)
        assert result_json == snapshot
        
    @pytest.mark.asyncio
    async def test_melania_token_announcement(self, image_search_agent: ImageSearchAgent, snapshot: SnapshotAssertion):
        """Test Melania token announcement image."""
        image_url = IMAGE_URLS[1]
        result = await image_search_agent.run(image_url)
        result_json = serialize_for_snapshot(result)
        assert result_json == snapshot
        
    @pytest.mark.asyncio
    async def test_non_announcement_image(self, image_search_agent: ImageSearchAgent, snapshot: SnapshotAssertion):
        """Test non-announcement image."""
        image_url = IMAGE_URLS[2]
        result = await image_search_agent.run(image_url)
        result_json = serialize_for_snapshot(result)
        assert result_json == snapshot


class TestIndividualWebCases:
    """Individual test methods for each web case."""
    
    @pytest.mark.asyncio
    async def test_flockerz_token_website(self, firecrawl_agent: FirecrawlAgent, snapshot: SnapshotAssertion):
        """Test Flockerz token website."""
        web_url = WEB_URLS[0]
        result = await firecrawl_agent.run(web_url)
        result_json = serialize_for_snapshot(result)
        assert result_json == snapshot
        
    @pytest.mark.asyncio
    async def test_trump_memes_website(self, firecrawl_agent: FirecrawlAgent, snapshot: SnapshotAssertion):
        """Test Trump memes website."""
        web_url = WEB_URLS[1]
        result = await firecrawl_agent.run(web_url)
        result_json = serialize_for_snapshot(result)
        assert result_json == snapshot