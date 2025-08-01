"""Text search agent for token detection in text content."""

from pydantic_ai import Agent

from ...models.schemas import SentimentAnalysisResult, NoTokenFound
from ...config.logging_config import get_logger
from ...config.sentiment_config import TEXT_SEARCH_PROMPT, DEFAULT_AGENT_RETRIES

logger = get_logger(__name__)


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
            retries=DEFAULT_AGENT_RETRIES,
            system_prompt=TEXT_SEARCH_PROMPT
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