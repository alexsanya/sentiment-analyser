# Unit Testing Strategy for Tweet Notification Service

## Overview
This document outlines the comprehensive unit testing strategy for the AI-powered sentiment analysis microservice. The testing approach focuses on ensuring robust coverage for RabbitMQ message processing, AI agent integration, workflow orchestration, and the threaded message handler pattern.

## Test Architecture

### Core Testing Framework
- **pytest** - Primary testing framework with fixtures and parametrized tests
- **pytest-mock** - Mocking capabilities for external dependencies  
- **pytest-asyncio** - Async test support for PydanticAI agents
- **pytest-cov** - Code coverage reporting
- **syrupy** - Snapshot testing for AI agent responses

### Test Organization
```
tests/
├── conftest.py                        # Shared test fixtures
├── integration/                       # Integration tests (require API keys)
│   ├── test_agents_integration.py    # Real AI agent testing with snapshots
│   ├── test_data.py                  # Test data for integration tests
│   └── __snapshots__/                # Snapshot test data
├── test_*.py                         # Unit test modules
└── __init__.py                       # Test package initialization
```

## Test Categories & Coverage

### 1. **Message Processing & RabbitMQ Integration**

**Files Covered:**
- `test_mq_subscriber.py` (43 tests)
- `test_mq_subscriber_reconnect.py` (reconnection behavior)
- `test_rabbitmq_monitor.py` (23 tests) 
- `test_message_buffer.py` (27 tests)

**Key Test Areas:**
- Connection establishment and health checks
- Message consumption and publishing 
- Buffer management during outages
- Automatic reconnection with exponential backoff
- Thread safety and concurrent operations
- Error handling and logging

### 2. **Threaded Message Handler Pattern**

**Files Covered:**
- `test_message_handler.py` (20 tests)
- `test_tweet_handler.py` (tweet processing)
- `test_main_rabbitmq.py` (main application integration)

**Key Test Areas:**
- Thread-per-message processing
- Factory pattern for handler creation
- Graceful shutdown and thread completion
- Message acknowledgment via `connection.add_callback_threadsafe()`
- QoS configuration and concurrency control
- Status monitoring and reporting

### 3. **AI Agent System & Workflow Orchestration**

**Files Covered:**
- `tests/integration/test_agents_integration.py` (live API testing)
- `test_retry_wrapper.py` (agent retry logic)
- Workflow orchestration testing (implicitly covered)

**Key Test Areas:**
- Text, image, and web content analysis agents
- Topic filtering and duplicate detection agents  
- Geopolitical expert analysis for Trump-Zelenskyy meetings
- Agent coordination and result merging
- Exponential backoff retry wrapper
- Snapshot testing of AI agent responses
- Error handling and fallback mechanisms

### 4. **Data Transformation & Validation**

**Files Covered:**
- `test_transformation.py` (27 tests)
- `test_address_validators.py` (blockchain validation)

**Key Test Areas:**
- Tweet data standardization pipeline
- DateTime parsing and URL extraction
- Pydantic schema validation
- Solana and EVM address validation
- Error handling and edge cases

### 5. **Trade Action Generation**

**Files Covered:**
- `test_get_trade_action.py` (score-based trading logic)

**Key Test Areas:**
- Trade action generation based on meeting analysis scores
- Parameter calculation for different score ranges
- Risk management logic (leverage, margin, stop-loss)
- Action schema validation

## Testing Strategies

### Unit Testing Approach
- **Isolation**: Each component tested in isolation with mocked dependencies
- **AAA Pattern**: Arrange, Act, Assert structure for all tests
- **Parametrized Tests**: Multiple input scenarios using `pytest.mark.parametrize`
- **Edge Cases**: Boundary conditions and error scenarios
- **Mocking Strategy**: External services (OpenAI, RabbitMQ) properly mocked

### Integration Testing Approach  
- **Live API Testing**: Real AI agent testing with actual API calls
- **Snapshot Testing**: AI agent responses validated against snapshots
- **End-to-End Workflows**: Complete message processing pipelines
- **Environment Requirements**: Tests require `OPENAI_API_KEY` and `OPENROUTER_API_KEY`

### Mock Strategy

#### RabbitMQ Mocking
```python
@pytest.fixture
def mock_mq_subscriber(mocker):
    """Mock MQSubscriber for testing message handling."""
    return mocker.patch('src.core.mq_subscriber.MQSubscriber')
```

#### AI Agent Mocking
```python
@pytest.fixture
def mock_openai_agent(mocker):
    """Mock OpenAI agent responses for unit tests."""
    return mocker.patch('pydantic_ai.Agent.run')
```

#### Threading Mocking
```python
@pytest.fixture
def mock_threading(mocker):
    """Mock threading components for deterministic testing."""
    return mocker.patch('threading.Thread')
```

## Test Execution

### Running Tests
```bash
# Run all tests
uv run pytest tests/ -v

# Run specific test categories
uv run pytest tests/test_mq_subscriber.py -v
uv run pytest tests/test_message_handler.py -v
uv run pytest tests/test_transformation.py -v

# Run integration tests (requires API keys)
OPENAI_API_KEY=your_key uv run pytest tests/integration/ -v

# Skip integration tests (unit tests only)
uv run pytest -m "not integration" -v

# Run with coverage reporting
uv run pytest tests/ --cov=src --cov-report=term-missing
uv run pytest tests/test_mq_subscriber.py --cov=src.core.mq_subscriber --cov-report=html

# Update snapshots when agent responses change
uv run pytest tests/integration/test_agents_integration.py --snapshot-update
```

### Coverage Targets
- **Overall Coverage**: 90%+ across all source modules
- **Critical Components**: 95%+ for core message processing
- **AI Agent Integration**: Comprehensive with snapshot validation
- **Error Handling**: All exception paths covered
- **Thread Safety**: Concurrent execution scenarios tested

## Quality Assurance

### Test Quality Standards
- **Independence**: Tests don't depend on each other's state
- **Repeatability**: Tests produce consistent results
- **Performance**: Unit tests complete in <5 seconds
- **Maintainability**: Tests are easy to understand and modify
- **Documentation**: Complex test scenarios have clear documentation

### Continuous Integration
- All tests must pass before merge
- Coverage thresholds enforced
- Integration tests run on dedicated CI resources
- Snapshot tests prevent AI agent regressions
- Security scanning for test dependencies

## Testing Best Practices

### Test Naming Convention
```python
def test_mq_subscriber_successful_connection():
    """Test MQSubscriber establishes connection successfully."""

def test_message_handler_thread_per_message_processing():
    """Test message handler creates dedicated thread per message."""
    
def test_trade_action_generation_for_high_scores():
    """Test trade action generation for meeting scores above threshold."""
```

### Fixture Organization
- **Scope**: Use appropriate fixture scopes (function, class, module)
- **Cleanup**: Ensure proper resource cleanup after tests
- **Reusability**: Share common fixtures across test modules
- **Configuration**: Environment-specific test configurations

### Error Testing
- **Exception Types**: Test specific exception types, not bare exceptions
- **Error Messages**: Validate error message content
- **Recovery**: Test error recovery and fallback mechanisms  
- **Logging**: Verify appropriate log messages during errors

## Future Testing Enhancements

### Planned Improvements
- **Performance Testing**: Benchmark tests for high-throughput scenarios
- **Load Testing**: Concurrent message processing under load
- **Chaos Testing**: Network partition and service failure scenarios
- **Property-Based Testing**: Using Hypothesis for edge case generation
- **Contract Testing**: API contract validation for external services

### Test Maintenance
- **Regular Review**: Quarterly review of test effectiveness
- **Refactoring**: Keep tests aligned with code changes
- **Documentation**: Update test documentation with new features
- **Tool Updates**: Keep testing dependencies current

## Test Environment Setup

### Local Development
```bash
# Install test dependencies
uv sync

# Set up environment variables
export OPENAI_API_KEY=your_test_api_key
export OPENROUTER_API_KEY=your_test_api_key

# Run quick test suite (unit tests only)
uv run pytest -m "not integration" -v
```

### CI/CD Environment  
- Separate test database instances
- Mocked external API endpoints
- Dedicated RabbitMQ test instances
- Secure API key management
- Parallel test execution

This comprehensive testing strategy ensures the reliability, maintainability, and quality of the AI-powered sentiment analysis microservice while supporting confident development and deployment practices.