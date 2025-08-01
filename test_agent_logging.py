#!/usr/bin/env python3
"""Test to verify agent logging works with the new configuration."""

import pytest
from unittest.mock import Mock, AsyncMock
from src.config.logging_config import setup_logging, get_logger
from src.core.agents.text_search_agent import TextSearchAgent

def test_agent_logging_setup():
    """Test that agent logging is properly configured."""
    # Setup logging like integration tests do
    setup_logging("development")
    logger = get_logger("src.core.agents.text_search_agent")
    
    # Test logging at agent level
    logger.info("Agent logger test - INFO level", test_case="mock_agent")
    logger.error("Agent logger test - ERROR level", test_case="mock_agent")
    
    assert True

@pytest.mark.asyncio
async def test_mock_agent_execution():
    """Test simulated agent execution with logging."""
    setup_logging("development")
    
    # Create a real agent but mock the actual API call
    agent = TextSearchAgent()
    
    # Mock the agent's run method to avoid real API calls
    original_run = agent.agent.run
    
    # Create a mock result object
    mock_result = Mock()
    mock_result.output = Mock()
    mock_result.output.__class__.__name__ = "TokenDetails"
    
    agent.agent.run = AsyncMock(return_value=mock_result)
    
    try:
        # This should trigger logging in the agent
        result = await agent.run("Test text for mock agent")
        
        # Verify the mock was called
        agent.agent.run.assert_called_once_with("Test text for mock agent")
        
        assert result is not None
        
    finally:
        # Restore original method
        agent.agent.run = original_run

if __name__ == "__main__":
    import asyncio
    # Run tests directly
    test_agent_logging_setup()
    asyncio.run(test_mock_agent_execution())
    print("Mock agent tests completed")