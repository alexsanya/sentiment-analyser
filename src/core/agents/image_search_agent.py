"""Image search agent for token detection in image content."""

from pydantic_ai import Agent, ImageUrl

from ...models.schemas import SentimentAnalysisResult, NoTokenFound
from ...config.logging_config import get_logger
from ...config.sentiment_config import IMAGE_SEARCH_PROMPT, DEFAULT_AGENT_RETRIES

logger = get_logger(__name__)


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
            retries=DEFAULT_AGENT_RETRIES,
            system_prompt=IMAGE_SEARCH_PROMPT
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