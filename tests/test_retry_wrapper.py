"""Tests for the AgentRetryWrapper functionality."""

import pytest
import asyncio
from unittest.mock import AsyncMock, Mock, patch
from src.core.agents.retry_wrapper import AgentRetryWrapper
from src.models.schemas import TokenDetails, NoTokenFound, RelseaseAnnouncementWithoutDetails


class TestAgentRetryWrapper:
    """Test cases for AgentRetryWrapper class."""

    def test_init_default_values(self):
        """Test initialization with default values."""
        wrapper = AgentRetryWrapper()
        
        assert wrapper.max_retries == 3  # DEFAULT_AGENT_RETRIES
        assert wrapper.initial_delay == 1.0

    def test_init_custom_values(self):
        """Test initialization with custom values."""
        wrapper = AgentRetryWrapper(max_retries=3, initial_delay=0.5)
        
        assert wrapper.max_retries == 3
        assert wrapper.initial_delay == 0.5

    @pytest.mark.asyncio
    async def test_success_on_first_attempt_token_details(self):
        """Test successful completion on first attempt with TokenDetails."""
        # Arrange
        wrapper = AgentRetryWrapper(max_retries=3, initial_delay=0.1)
        token_details = TokenDetails(token_address="0x123", chain_id=1, chain_name="Ethereum")
        
        mock_agent_func = AsyncMock(return_value=token_details)
        
        # Act
        result = await wrapper.run_with_retry(mock_agent_func, "test_agent", "test_input")
        
        # Assert
        assert isinstance(result, TokenDetails)
        assert result.token_address == "0x123"
        assert mock_agent_func.call_count == 1
        mock_agent_func.assert_called_with("test_input")

    @pytest.mark.asyncio
    async def test_retry_on_no_token_found_until_success(self):
        """Test retrying on NoTokenFound until TokenDetails is returned."""
        # Arrange
        wrapper = AgentRetryWrapper(max_retries=3, initial_delay=0.01)
        token_details = TokenDetails(token_address="0x456", chain_id=56, chain_name="BSC")
        
        # Mock agent function that fails twice then succeeds
        mock_agent_func = AsyncMock(side_effect=[
            NoTokenFound(),  # First attempt
            NoTokenFound(),  # Second attempt
            token_details    # Third attempt - success
        ])
        
        # Act
        result = await wrapper.run_with_retry(mock_agent_func, "test_agent", "test_input")
        
        # Assert
        assert isinstance(result, TokenDetails)
        assert result.token_address == "0x456"
        assert mock_agent_func.call_count == 3

    @pytest.mark.asyncio
    async def test_retry_on_release_announcement_until_success(self):
        """Test retrying on RelseaseAnnouncementWithoutDetails until TokenDetails is returned."""
        # Arrange
        wrapper = AgentRetryWrapper(max_retries=2, initial_delay=0.01)
        token_details = TokenDetails(token_address="0x789", chain_id=137, chain_name="Polygon")
        
        # Mock agent function that returns announcement then succeeds
        mock_agent_func = AsyncMock(side_effect=[
            RelseaseAnnouncementWithoutDetails(),  # First attempt
            token_details                          # Second attempt - success
        ])
        
        # Act
        result = await wrapper.run_with_retry(mock_agent_func, "test_agent", "test_input")
        
        # Assert
        assert isinstance(result, TokenDetails)
        assert result.token_address == "0x789"
        assert mock_agent_func.call_count == 2

    @pytest.mark.asyncio
    async def test_exhaust_retries_with_no_token_found(self):
        """Test exhausting all retries and returning last NoTokenFound result."""
        # Arrange
        wrapper = AgentRetryWrapper(max_retries=2, initial_delay=0.01)
        
        # Mock agent function that always fails
        mock_agent_func = AsyncMock(return_value=NoTokenFound())
        
        # Act
        result = await wrapper.run_with_retry(mock_agent_func, "test_agent", "test_input")
        
        # Assert
        assert isinstance(result, NoTokenFound)
        assert mock_agent_func.call_count == 3  # Initial attempt + 2 retries

    @pytest.mark.asyncio
    async def test_exhaust_retries_with_release_announcement(self):
        """Test exhausting all retries and returning last RelseaseAnnouncementWithoutDetails result."""
        # Arrange
        wrapper = AgentRetryWrapper(max_retries=2, initial_delay=0.01)
        
        # Mock agent function that always returns release announcement
        mock_agent_func = AsyncMock(return_value=RelseaseAnnouncementWithoutDetails())
        
        # Act
        result = await wrapper.run_with_retry(mock_agent_func, "test_agent", "test_input")
        
        # Assert
        assert isinstance(result, RelseaseAnnouncementWithoutDetails)
        assert mock_agent_func.call_count == 3  # Initial attempt + 2 retries

    @pytest.mark.asyncio
    async def test_exception_propagation(self):
        """Test that exceptions from agent function are properly propagated."""
        # Arrange
        wrapper = AgentRetryWrapper(max_retries=2, initial_delay=0.01)
        
        # Mock agent function that raises an exception
        mock_agent_func = AsyncMock(side_effect=ValueError("Test error"))
        
        # Act & Assert
        with pytest.raises(ValueError, match="Test error"):
            await wrapper.run_with_retry(mock_agent_func, "test_agent", "test_input")
        
        assert mock_agent_func.call_count == 1

    @pytest.mark.asyncio
    async def test_zero_initial_delay(self):
        """Test retry wrapper with zero initial delay (no delays between retries)."""
        # Arrange
        wrapper = AgentRetryWrapper(max_retries=2, initial_delay=0.0)
        token_details = TokenDetails(token_address="0xABC", chain_id=1)
        
        # Mock agent function that fails once then succeeds
        mock_agent_func = AsyncMock(side_effect=[NoTokenFound(), token_details])
        
        # Act
        start_time = asyncio.get_event_loop().time()
        result = await wrapper.run_with_retry(mock_agent_func, "test_agent", "test_input")
        end_time = asyncio.get_event_loop().time()
        
        # Assert
        assert isinstance(result, TokenDetails)
        assert mock_agent_func.call_count == 2
        # Should complete quickly with zero delay
        assert (end_time - start_time) < 0.1

    @pytest.mark.asyncio
    async def test_progressive_exponential_backoff_delays(self):
        """Test that delays follow exponential backoff pattern: 1s, 2s, 4s, 8s."""
        # Arrange
        wrapper = AgentRetryWrapper(max_retries=4, initial_delay=0.1)  # Use 0.1s for faster testing
        
        # Mock agent function that always returns NoTokenFound to trigger all retries
        mock_agent_func = AsyncMock(return_value=NoTokenFound())
        
        # Track sleep calls to verify delay progression
        sleep_calls = []
        original_sleep = asyncio.sleep
        
        async def mock_sleep(delay):
            sleep_calls.append(delay)
            # Don't actually sleep during test, just record the delay
            await original_sleep(0.001)  # Very brief delay for async
        
        # Act
        with patch('asyncio.sleep', side_effect=mock_sleep):
            result = await wrapper.run_with_retry(mock_agent_func, "test_agent", "test_input")
        
        # Assert
        assert isinstance(result, NoTokenFound)
        assert mock_agent_func.call_count == 5  # Initial + 4 retries
        
        # Verify exponential backoff delays: 0.1s, 0.2s, 0.4s, 0.8s
        expected_delays = [0.1, 0.2, 0.4, 0.8]
        assert len(sleep_calls) == 4  # 4 delays between 5 attempts
        for i, expected_delay in enumerate(expected_delays):
            assert abs(sleep_calls[i] - expected_delay) < 0.001, f"Delay {i+1} should be {expected_delay}s, got {sleep_calls[i]}s"

    @pytest.mark.asyncio
    async def test_multiple_arguments_passed_correctly(self):
        """Test that multiple arguments and kwargs are passed correctly to agent function."""
        # Arrange
        wrapper = AgentRetryWrapper(max_retries=1, initial_delay=0.01)
        token_details = TokenDetails(token_address="0xDEF", chain_id=42161)
        
        mock_agent_func = AsyncMock(return_value=token_details)
        
        # Act
        result = await wrapper.run_with_retry(
            mock_agent_func, 
            "test_agent", 
            "arg1", 
            "arg2", 
            kwarg1="value1", 
            kwarg2="value2"
        )
        
        # Assert
        assert isinstance(result, TokenDetails)
        mock_agent_func.assert_called_with("arg1", "arg2", kwarg1="value1", kwarg2="value2")

    @pytest.mark.asyncio
    @patch('src.core.agents.retry_wrapper.log_agent_metrics')
    async def test_logging_metrics_on_success(self, mock_log_metrics):
        """Test that success metrics are logged correctly."""
        # Arrange
        wrapper = AgentRetryWrapper(max_retries=2, initial_delay=0.01)
        token_details = TokenDetails(token_address="0x111")
        
        mock_agent_func = AsyncMock(side_effect=[NoTokenFound(), token_details])
        
        # Act
        result = await wrapper.run_with_retry(mock_agent_func, "test_agent", "test_input")
        
        # Assert
        assert isinstance(result, TokenDetails)
        mock_log_metrics.assert_called()
        
        # Check the final success call
        success_call = mock_log_metrics.call_args
        assert success_call[1]['agent_type'] == "test_agent_retry"
        assert success_call[1]['success'] is True
        assert success_call[1]['retry_attempts'] == 2

    @pytest.mark.asyncio
    @patch('src.core.agents.retry_wrapper.log_agent_metrics')
    async def test_logging_metrics_on_failure(self, mock_log_metrics):
        """Test that failure metrics are logged correctly."""
        # Arrange
        wrapper = AgentRetryWrapper(max_retries=1, initial_delay=0.01)
        
        mock_agent_func = AsyncMock(return_value=NoTokenFound())
        
        # Act
        result = await wrapper.run_with_retry(mock_agent_func, "test_agent", "test_input")
        
        # Assert
        assert isinstance(result, NoTokenFound)
        mock_log_metrics.assert_called()
        
        # Check the final failure call
        failure_call = mock_log_metrics.call_args
        assert failure_call[1]['agent_type'] == "test_agent_retry"
        assert failure_call[1]['success'] is False
        assert failure_call[1]['retry_attempts'] == 2  # Initial + 1 retry

    @pytest.mark.asyncio
    async def test_max_retries_zero(self):
        """Test behavior when max_retries is set to 0."""
        # Arrange
        wrapper = AgentRetryWrapper(max_retries=0, initial_delay=0.01)
        
        mock_agent_func = AsyncMock(return_value=NoTokenFound())
        
        # Act
        result = await wrapper.run_with_retry(mock_agent_func, "test_agent", "test_input")
        
        # Assert
        assert isinstance(result, NoTokenFound)
        assert mock_agent_func.call_count == 1  # Only initial attempt, no retries

    @pytest.mark.asyncio
    async def test_mixed_result_types_retry_pattern(self):
        """Test retry behavior with mixed non-TokenDetails result types."""
        # Arrange
        wrapper = AgentRetryWrapper(max_retries=3, initial_delay=0.01)
        token_details = TokenDetails(token_address="0x999")
        
        # Mock agent function with mixed failure types
        mock_agent_func = AsyncMock(side_effect=[
            NoTokenFound(),                         # First attempt
            RelseaseAnnouncementWithoutDetails(),   # Second attempt  
            NoTokenFound(),                         # Third attempt
            token_details                           # Fourth attempt - success
        ])
        
        # Act
        result = await wrapper.run_with_retry(mock_agent_func, "test_agent", "test_input")
        
        # Assert
        assert isinstance(result, TokenDetails)
        assert result.token_address == "0x999"
        assert mock_agent_func.call_count == 4