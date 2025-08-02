"""Firecrawl agent for token detection in web content."""

import time
from typing import cast
from pydantic_ai import Agent
from pydantic_ai.mcp import MCPServerSSE

from ...models.schemas import SentimentAnalysisResult, NoTokenFound
from ...config.logging_config import get_logger
from ...config.sentiment_config import FIRECRAWL_SEARCH_PROMPT, DEFAULT_AGENT_RETRIES
from ...config.logfire_config import create_logfire_span, log_agent_metrics

logger = get_logger(__name__)


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
        self.agent = Agent[None, SentimentAnalysisResult](  # type: ignore[call-overload]
            model=model_name,
            result_type=SentimentAnalysisResult,
            retries=DEFAULT_AGENT_RETRIES,
            system_prompt=FIRECRAWL_SEARCH_PROMPT,
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
        start_time = time.time()
        url_length = len(url)
        
        # Create Logfire span for tracing
        span = create_logfire_span(
            "firecrawl_agent.run",
            url=url,
            url_length=url_length,
            agent_type="firecrawl"
        )
        
        try:
            if span:
                with span:
                    async with self.agent.run_mcp_servers():
                        result = await self.agent.run(url)
            else:
                async with self.agent.run_mcp_servers():
                    result = await self.agent.run(url)
            
            execution_time = time.time() - start_time
            result_type = type(result.output).__name__
            
            # Log metrics to Logfire
            log_agent_metrics(
                agent_type="firecrawl",
                execution_time=execution_time,
                input_size=url_length,
                result_type=result_type,
                success=True,
                url=url
            )
            
            logger.info(
                "FirecrawlAgent completed analysis", 
                url=url,
                execution_time=execution_time,
                result_type=result_type
            )
            return cast(SentimentAnalysisResult, result.output)
            
        except Exception as e:
            execution_time = time.time() - start_time
            
            # Log failed metrics to Logfire
            log_agent_metrics(
                agent_type="firecrawl",
                execution_time=execution_time,
                input_size=url_length,
                result_type="NoTokenFound",
                success=False,
                error=str(e),
                url=url
            )
            
            logger.error(
                "FirecrawlAgent failed", 
                error=str(e), 
                url=url,
                execution_time=execution_time
            )
            return NoTokenFound()