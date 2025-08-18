"""Token detection step for cryptocurrency analysis."""

from typing import List

from ...models.schemas import SentimentAnalysisResult, NoTokenFound
from ..agents import TextSearchAgent, ImageSearchAgent, FirecrawlAgent
from .utils import AgentType, merge_agent_results
from ...config.logging_config import get_logger
from .state import WorkflowState

logger = get_logger(__name__)


async def run_token_detection_step(state: WorkflowState) -> SentimentAnalysisResult:
    """Run token detection agents on text, images, and links."""
    agent_results = []
    
    # Text analysis
    if state.text.strip():
        text_agent = TextSearchAgent(state.config.model_name)
        text_result = await text_agent.run(state.text)
        agent_results.append((AgentType.TEXT, text_result))
    
    # Image analysis
    for image_url in state.images:
        if image_url.strip():
            image_agent = ImageSearchAgent(state.config.model_name)
            image_result = await image_agent.run(image_url)
            agent_results.append((AgentType.IMAGE, image_result))
    
    # Link analysis
    for link_url in state.links:
        if link_url.strip():
            firecrawl_agent = FirecrawlAgent(state.config.model_name, state.config.firecrawl_mcp_server_url)
            firecrawl_result = await firecrawl_agent.run(link_url)
            agent_results.append((AgentType.FIRECRAWL, firecrawl_result))
    
    # Merge token detection results
    if agent_results:
        merged_result = merge_agent_results(agent_results)
        logger.debug(
            "Token detection completed",
            result_type=type(merged_result).__name__,
            agent_count=len(agent_results)
        )
        return merged_result
    else:
        logger.debug("No token detection agents were run")
        return NoTokenFound()