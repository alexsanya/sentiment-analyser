# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an AI-powered sentiment analysis microservice for cryptocurrency token detection, built on RabbitMQ message processing architecture. The application specializes in analyzing tweets and social media content to detect new cryptocurrency token announcements using advanced AI agents. It combines message consumption, processing, and logging with sophisticated blockchain intelligence capabilities, featuring PydanticAI-powered agents for text analysis, image recognition, and web scraping. The service can be integrated into larger cryptocurrency monitoring and trading systems for real-time token discovery and market intelligence.

## Technology Stack

- **Language**: Python 3.12
- **Package Manager**: UV (modern Python package manager)
- **Key Dependencies**: 
  - `pydantic-ai` for AI-powered sentiment analysis agents
  - `pika` for RabbitMQ message consumption, publishing, and connection monitoring
  - `pydantic` for data validation and schema enforcement
  - `dotenv` for environment variable management
  - `structlog` for structured logging with JSON output
  - `logfire` for observability and PydanticAI instrumentation
  - `base58` for Solana address validation
  - `nest-asyncio` for async event loop management
- **Testing**: 
  - `pytest` for unit testing framework
  - `pytest-mock` for mocking functionality
  - `pytest-cov` for coverage reporting
  - `pytest-asyncio` for async test support
  - `syrupy` for snapshot testing agent responses
- **Containerization**:
  - `Docker` for containerization with Python 3.12 slim image
  - `docker-compose` for multi-service orchestration
  - Custom bridge network for service communication
  - Volume mounts for data persistence and log access

## Development Commands

```bash
# Run the application (threaded message processing)
python main.py

# Install dependencies
uv sync

# Add new dependencies
uv add <package-name>

# Run all tests
uv run pytest tests/ -v

# Run MQSubscriber tests
uv run pytest tests/test_mq_subscriber.py

# Run MQSubscriber tests with coverage
uv run pytest tests/test_mq_subscriber.py --cov=src.core.mq_subscriber --cov-report=term-missing

# Run RabbitMQ monitor tests
uv run pytest tests/test_rabbitmq_monitor.py

# Run RabbitMQ monitor tests with coverage
uv run pytest tests/test_rabbitmq_monitor.py --cov=src.core.rabbitmq_monitor --cov-report=term-missing

# Run message buffer tests
uv run pytest tests/test_message_buffer.py

# Run message buffer tests with coverage
uv run pytest tests/test_message_buffer.py --cov=src.core.message_buffer --cov-report=term-missing

# Run all RabbitMQ-related tests
uv run pytest tests/test_rabbitmq_monitor.py tests/test_mq_subscriber.py tests/test_main_rabbitmq.py -v

# Run all buffer and messaging tests
uv run pytest tests/test_message_buffer.py tests/test_mq_subscriber.py tests/test_rabbitmq_monitor.py -v

# Run transformation tests
uv run pytest tests/test_transformation.py

# Run transformation tests with coverage
uv run pytest tests/test_transformation.py --cov=src.core.transformation --cov-report=term-missing

# Run tweet handler tests
uv run pytest tests/test_tweet_handler.py

# Run tweet handler tests with coverage
uv run pytest tests/test_tweet_handler.py --cov=src.handlers.tweet --cov-report=term-missing

# Run message handler tests
uv run pytest tests/test_message_handler.py

# Run message handler tests with coverage
uv run pytest tests/test_message_handler.py --cov=src.handlers.message_handler --cov-report=term-missing

# Test message handler functionality (requires mocking)
# Note: Message handler tests are included in integration testing

# Sentiment Analysis and Agent Tests

# Run all sentiment analysis tests
uv run pytest tests/test_sentiment_analyzer.py -v

# Run sentiment analysis tests with coverage
uv run pytest tests/test_sentiment_analyzer.py --cov=src.core.sentiment_analyzer --cov-report=term-missing

# Run address validation tests
uv run pytest tests/test_address_validators.py -v

# Run address validation tests with coverage
uv run pytest tests/test_address_validators.py --cov=src.core.utils.address_validators --cov-report=term-missing

# Run retry wrapper tests
uv run pytest tests/test_retry_wrapper.py -v

# Run retry wrapper tests with coverage
uv run pytest tests/test_retry_wrapper.py --cov=src.core.agents.retry_wrapper --cov-report=term-missing

# Agent Integration Tests (require OPENAI_API_KEY)

# Run all agent integration tests (requires OpenAI API key)
OPENAI_API_KEY=your_key uv run pytest tests/integration/test_agents_integration.py -v

# Run specific agent integration tests
uv run pytest tests/integration/test_agents_integration.py::TestTextSearchAgent -v
uv run pytest tests/integration/test_agents_integration.py::TestImageSearchAgent -v
uv run pytest tests/integration/test_agents_integration.py::TestFirecrawlAgent -v

# Run individual test cases for debugging
uv run pytest tests/integration/test_agents_integration.py::TestIndividualTextCases::test_polygon_explicit_chain_evm_address -v

# Update snapshots when agent responses change
uv run pytest tests/integration/test_agents_integration.py --snapshot-update

# Run integration tests with specific marker
uv run pytest -m integration -v

# Skip integration tests (run only unit tests) 
uv run pytest -m "not integration" -v

# Run integration tests with coverage
uv run pytest tests/integration/ --cov=src.core.agents --cov-report=term-missing

# Run all sentiment analysis related tests
uv run pytest tests/test_sentiment_analyzer.py tests/test_address_validators.py tests/test_retry_wrapper.py tests/integration/test_agents_integration.py -v

# Docker Development Commands

# Build and start all services (RabbitMQ + News Watcher)
docker-compose up -d

# View logs for news watcher service
docker-compose logs -f news-watcher

# View logs for RabbitMQ service
docker-compose logs -f rabbitmq

# View logs for all services
docker-compose logs -f

# Rebuild and restart services after code changes
docker-compose up -d --build

# Stop all services
docker-compose down

# Stop services and remove volumes (clean slate)
docker-compose down -v

# Access RabbitMQ Management UI
# http://localhost:15672 (admin/changeme)
```

## Architecture

**AI-powered sentiment analysis architecture** for cryptocurrency token detection:

- **Main Application** (`main.py`): Application orchestration and threaded message consumption for high-throughput processing
- **Sentiment Analyzer** (`src/core/sentiment_analyzer.py`): Main sentiment analysis orchestration with agent coordination
- **AI Agents** (`src/core/agents/` package): PydanticAI-powered agents for text, image, and web content analysis
- **MQ Subscriber** (`src/core/mq_subscriber.py`): RabbitMQ message consumption and publishing service with schema validation and automatic buffering
- **Data Transformation** (`src/core/transformation.py`): Tweet data standardization and format conversion pipeline
- **Schema Validation** (`src/models/schemas.py`): Pydantic models for data validation, token details, sentiment analysis results, and snipe action messages
- **RabbitMQ Monitor** (`src/core/rabbitmq_monitor.py`): Automatic connection monitoring with health checks and reconnection logic
- **Message Handlers** (`src/handlers/` package): Threaded message processing with sentiment analysis integration and snipe action publishing
- **Address Validators** (`src/core/utils/` package): Blockchain address validation utilities for Solana and EVM chains
- **Configuration Management** (`src/config/` package): Structured logging, Logfire observability, and sentiment analysis configuration

### Sentiment Analysis Architecture

**AI Agent System** (cryptocurrency token detection):
- **TextSearchAgent** (`src/core/agents/text_search_agent.py`): Analyzes tweet text content for token announcements and blockchain addresses
- **ImageSearchAgent** (`src/core/agents/image_search_agent.py`): Extracts and analyzes text from images for token information
- **FirecrawlAgent** (`src/core/agents/firecrawl_agent.py`): Scrapes and analyzes linked websites for token announcements

**Agent Orchestration** (`src/core/sentiment_analyzer.py`): Coordinates multiple agents and merges analysis results

**Address Validation** (`src/core/utils/address_validators.py`): Validates Solana and EVM blockchain addresses using regex patterns and cryptographic validation

### Handler Architecture

**Message Handlers** (process incoming message content):
- `src/handlers/tweet.py`: Tweet message processing with transformation pipeline, data validation, and sentiment analysis integration
- `src/handlers/message_handler.py`: Threaded RabbitMQ message handler with thread-per-message processing for long-running sentiment analysis operations

**Handler Package** (`src/handlers/__init__.py`): Centralized exports for message handlers and factory functions

### Threaded Message Processing Architecture

**Default Processing Pattern** (based on Pika threaded consumer example):

The application uses a thread-per-message processing pattern optimized for handling potentially long-running sentiment analysis operations:

**Key Features:**
- **Thread-per-Message**: Each incoming message spawns a dedicated processing thread
- **Thread-Safe Acknowledgment**: Uses `connection.add_callback_threadsafe()` for safe message acknowledgment from worker threads
- **Concurrent Processing**: Multiple messages can be processed simultaneously without blocking the consumer
- **Graceful Shutdown**: Waits for all processing threads to complete during application shutdown
- **Thread Management**: Automatic cleanup of finished threads and status monitoring

**Processing Flow:**
1. **Message Reception**: Consumer receives message and immediately spawns processing thread
2. **Thread Processing**: Worker thread performs sentiment analysis (potentially taking seconds)
3. **Safe Acknowledgment**: Uses thread-safe callback to acknowledge message completion
4. **Concurrent Operations**: Multiple threads can process different messages simultaneously
5. **Resource Cleanup**: Finished threads are automatically cleaned up

**ThreadedMessageProcessor Class:**
- **Processor Management**: Coordinates thread lifecycle and provides status monitoring
- **Consumer Integration**: Seamlessly integrates with existing MQSubscriber infrastructure
- **Configuration**: Supports QoS settings to limit concurrent processing load
- **Monitoring**: Real-time status reporting for active threads and processor state

**Performance Benefits:**
- **Higher Throughput**: Multiple messages processed concurrently instead of sequentially
- **Better Resource Utilization**: CPU cores can be fully utilized during AI agent processing
- **Reduced Latency**: Fast messages aren't blocked by slow sentiment analysis operations
- **Scalability**: Natural scaling with available CPU cores and memory

### File Structure
```
├── main.py                    # Application entry point with threaded RabbitMQ message processing
├── src/                       # Source code package
│   ├── __init__.py           # Package initialization
│   ├── config/               # Configuration modules
│   │   ├── __init__.py      # Package exports
│   │   ├── logging_config.py # Structured logging configuration
│   │   ├── logfire_config.py # Logfire observability configuration
│   │   └── sentiment_config.py # Sentiment analysis and agent configuration
│   ├── core/                 # Core business logic modules
│   │   ├── __init__.py      # Package exports
│   │   ├── agents/          # AI sentiment analysis agents
│   │   │   ├── __init__.py  # Agent exports
│   │   │   ├── text_search_agent.py # Text content analysis agent
│   │   │   ├── image_search_agent.py # Image text extraction agent
│   │   │   ├── firecrawl_agent.py # Web scraping agent
│   │   │   └── retry_wrapper.py # Exponential backoff retry wrapper for agents
│   │   ├── utils/           # Utility functions
│   │   │   ├── __init__.py  # Utility exports
│   │   │   └── address_validators.py # Blockchain address validation
│   │   ├── sentiment_analyzer.py # Main sentiment analysis orchestration
│   │   ├── mq_subscriber.py # RabbitMQ message consumption and publishing service
│   │   ├── message_buffer.py # Thread-safe FIFO message buffer for RabbitMQ outages
│   │   ├── transformation.py # Tweet data transformation and standardization pipeline
│   │   └── rabbitmq_monitor.py # RabbitMQ connection monitoring with automatic reconnection
│   ├── handlers/             # Message handlers package
│   │   ├── __init__.py      # Package exports
│   │   ├── tweet.py         # Tweet message handler with transformation and sentiment analysis
│   │   └── message_handler.py # Threaded RabbitMQ message handler with thread-per-message processing
│   └── models/               # Data models and schemas
│       ├── __init__.py      # Package exports
│       └── schemas.py       # Pydantic models for data validation, token details, and sentiment analysis
├── tests/                    # Comprehensive test suite
│   ├── __init__.py          # Package initialization
│   ├── conftest.py          # Shared test fixtures
│   ├── integration/         # Integration tests
│   │   ├── __init__.py      # Integration test package
│   │   ├── README.md        # Integration test documentation  
│   │   ├── __snapshots__/   # Snapshot test data
│   │   ├── test_agents_integration.py # Agent integration tests
│   │   └── test_data.py     # Test data for agent integration
│   ├── test_mq_subscriber.py # MQSubscriber functionality tests
│   ├── test_rabbitmq_monitor.py # RabbitMQ connection monitor tests
│   ├── test_message_buffer.py # MessageBuffer tests
│   ├── test_transformation.py # Transformation pipeline tests
│   ├── test_tweet_handler.py # Tweet handler tests
│   ├── test_message_handler.py # Message handler tests
│   ├── test_sentiment_analyzer.py # Sentiment analyzer tests
│   ├── test_address_validators.py # Address validation tests
│   ├── test_retry_wrapper.py # Agent retry wrapper tests
│   └── test_main_rabbitmq.py # Main application integration tests
├── examples/                # Example files and sample data
│   ├── tweet-sample.json   # Sample tweet data for testing and development
│   ├── sentiment-analyze.ipynb # Jupyter notebook for sentiment analysis examples
│   └── tg_bots_dialog.ipynb # Jupyter notebook for bot dialog examples
├── docs/                    # Documentation files
│   ├── review-process.md   # Code review process documentation
│   └── unit-testing-plan.md # Testing strategy documentation
├── logs/                    # Log files (auto-created)
│   ├── app.log             # All log levels (INFO and above)
│   ├── warning.log         # WARNING level and above
│   └── error.log           # ERROR level messages only
├── docker/                  # Docker-related files
├── mypy.ini                # MyPy type checking configuration
├── pyproject.toml          # Project configuration and dependencies
├── uv.lock                 # UV lock file for reproducible builds
├── docker-compose.yml      # Multi-service Docker orchestration
├── Dockerfile             # Container build instructions
└── README.md              # Project overview and setup instructions
```

## Configuration

- **`.env`**: Contains environment variables for RabbitMQ connection and optional `ENVIRONMENT` setting
- **`pyproject.toml`**: Project configuration and dependencies
- **`mypy.ini`**: MyPy type checking configuration
- **`src/config/logging_config.py`**: Structured logging configuration with file separation by log level

### MQSubscriber Configuration

The MQSubscriber supports both consumption and publishing via environment variables:

- **`RABBITMQ_HOST`**: RabbitMQ server host (default: "localhost")
- **`RABBITMQ_PORT`**: RabbitMQ server port (default: "5672")
- **`RABBITMQ_QUEUE`**: Default queue name for publishing (default: "tweet_events")
- **`RABBITMQ_CONSUME_QUEUE`**: Queue name for consumption (defaults to RABBITMQ_QUEUE)
- **`ACTIONS_QUEUE_NAME`**: Queue name for publishing snipe actions when tokens are detected (default: "actions_to_take")
- **`RABBITMQ_USERNAME`**: Optional username for authentication
- **`RABBITMQ_PASSWORD`**: Optional password for authentication

Example `.env` configuration:
```bash
# RabbitMQ Connection
RABBITMQ_HOST=localhost
RABBITMQ_PORT=5672
RABBITMQ_QUEUE=tweet_events
RABBITMQ_CONSUME_QUEUE=incoming_messages
ACTIONS_QUEUE_NAME=actions_to_take
RABBITMQ_USERNAME=admin
RABBITMQ_PASSWORD=changeme

# Logfire Configuration
LOGFIRE_ENABLED=true
LOGFIRE_TOKEN=your_logfire_token_here
LOGFIRE_SERVICE_NAME=tweets-notifier
LOGFIRE_ENVIRONMENT=development
SERVICE_VERSION=0.1.0
```

### RabbitMQ Monitor Configuration

The RabbitMQ connection monitor is configurable via environment variables:

- **`RABBITMQ_MONITOR_ENABLED`**: Enable/disable connection monitoring (default: "true")
- **`RABBITMQ_MONITOR_INTERVAL`**: Seconds between health checks (default: "30")
- **`RABBITMQ_MAX_RETRY_ATTEMPTS`**: Maximum reconnection attempts before giving up (default: "3")
- **`RABBITMQ_RETRY_DELAY`**: Seconds to wait between reconnection attempts (default: "5")

Example `.env` configuration:
```bash
# RabbitMQ Connection Monitoring
RABBITMQ_MONITOR_ENABLED=true
RABBITMQ_MONITOR_INTERVAL=30
RABBITMQ_MAX_RETRY_ATTEMPTS=3
RABBITMQ_RETRY_DELAY=5
```

### Message Buffer Configuration

The application includes a message buffer system that stores up to 10 messages when RabbitMQ is unavailable. This prevents message loss during temporary connection outages.

- **`MESSAGE_BUFFER_ENABLED`**: Enable/disable message buffering (default: "true")
- **`MESSAGE_BUFFER_SIZE`**: Maximum number of messages to buffer (default: "10")

Example `.env` configuration:
```bash
# Message Buffer Configuration
MESSAGE_BUFFER_ENABLED=true
MESSAGE_BUFFER_SIZE=10
```

### Sentiment Analysis Configuration

The sentiment analysis system uses AI agents to detect cryptocurrency token announcements. Configuration is managed through environment variables and dedicated configuration modules.

- **`OPENAI_API_KEY`**: OpenAI API key for PydanticAI agents (required for sentiment analysis)
- **`SENTIMENT_MODEL_NAME`**: AI model to use for analysis (default: "openai:gpt-4o")
- **`FIRECRAWL_MCP_SERVER_URL`**: Firecrawl MCP server URL for web scraping (default: "http://localhost:3000/sse")
- **`MAX_CONCURRENT_ANALYSIS`**: Maximum concurrent agent operations (default: 5)
- **`AGENT_RETRIES`**: Number of retry attempts for failed agent operations (default: 4)

Example `.env` configuration:
```bash
# Sentiment Analysis Configuration
OPENAI_API_KEY=your_openai_api_key_here
SENTIMENT_MODEL_NAME=openai:gpt-4o
FIRECRAWL_MCP_SERVER_URL=http://localhost:3000/sse
MAX_CONCURRENT_ANALYSIS=5
AGENT_RETRIES=4
```

#### Agent System Configuration

The system includes three specialized agents:

- **TextSearchAgent**: Analyzes tweet text content for token announcements using regex patterns and blockchain identification
- **ImageSearchAgent**: Extracts text from images and analyzes for token information
- **FirecrawlAgent**: Scrapes linked websites for token announcement content

Each agent uses blockchain chain ID mapping and address validation patterns to identify:
- **EVM Addresses**: Ethereum, BSC, Polygon, Arbitrum, etc. (0x + 40 hex characters)
- **Solana Addresses**: Base58 encoded addresses (32-44 characters, typically 44)

### Logfire Configuration

The application includes comprehensive observability through Logfire, providing tracing and metrics for all PydanticAI agents.

- **`LOGFIRE_ENABLED`**: Enable/disable Logfire observability (default: "true")
- **`LOGFIRE_TOKEN`**: Logfire API token (required for observability)
- **`LOGFIRE_SERVICE_NAME`**: Service name for tracing (default: "sentiment-analyzer")
- **`LOGFIRE_ENVIRONMENT`**: Environment name for tracing (default: value of ENVIRONMENT or "development")
- **`SERVICE_VERSION`**: Service version for tracing (default: "0.1.0")

Example `.env` configuration:
```bash
# Logfire Observability
LOGFIRE_ENABLED=true
LOGFIRE_TOKEN=your_logfire_token_here
LOGFIRE_SERVICE_NAME=sentiment-analyzer
LOGFIRE_ENVIRONMENT=production
SERVICE_VERSION=0.1.0
```

#### Logfire Features

- **PydanticAI Instrumentation**: Automatic instrumentation of all PydanticAI agents via `instrument_pydantic_ai()`
- **Agent Execution Tracing**: Detailed spans for TextSearchAgent, ImageSearchAgent, and FirecrawlAgent operations
- **Performance Metrics**: Execution time, input size, result types, and success/failure tracking
- **Error Tracking**: Comprehensive error logging with context and stack traces
- **Correlation**: Integration with existing structured logging for full observability

## Docker Containerization

The application supports Docker containerization with multi-service orchestration via docker-compose.

### Docker Architecture

- **news-watcher**: Main application container running the WebSocket news monitoring service
- **rabbitmq**: RabbitMQ message broker with management UI
- **trading_network**: Custom bridge network for secure inter-service communication
- **Volume mounts**: Persistent data storage and log access from host

### Docker Services

#### News Watcher Service
- **Base Image**: Python 3.12 slim for optimal performance
- **Package Manager**: UV for fast dependency resolution
- **Health Checks**: Automated container health monitoring
- **Restart Policy**: Automatic restart on failures
- **Network**: Connected to trading_network for RabbitMQ communication

#### RabbitMQ Service
- **Image**: rabbitmq:3.13-management with web UI
- **Ports**: 5672 (AMQP), 15672 (Management UI)
- **Persistence**: Named volume for message durability
- **Health Checks**: Port connectivity validation
- **Credentials**: Configurable via environment variables

### Container Networking

- **Internal Communication**: news-watcher connects to rabbitmq:5672
- **External Access**: RabbitMQ Management UI at localhost:15672
- **Service Discovery**: Automatic DNS resolution between containers
- **Network Isolation**: Services isolated on custom bridge network

### Environment Variable Integration

All configuration from `.env` file is automatically passed to containers:
- Twitter API credentials
- RabbitMQ connection settings (host automatically set to 'rabbitmq')
- Monitoring and buffer configuration
- Application environment settings

### Docker Development Workflow

```bash
# Initial setup - create environment file
# Copy your configuration to .env file

# Start all services
docker-compose up -d

# Monitor application logs
docker-compose logs -f news-watcher

# Access RabbitMQ Management UI
# Navigate to http://localhost:15672
# Default credentials: admin/changeme (configurable via .env)

# Rebuild after code changes
docker-compose up -d --build

# Clean shutdown
docker-compose down
```

## Key Components

- **Sentiment Analysis** (`src/core/sentiment_analyzer.py`): AI-powered cryptocurrency token detection orchestration and agent coordination
- **AI Agent System** (`src/core/agents/` package): PydanticAI-powered agents for text, image, and web content analysis
- **Address Validation** (`src/core/utils/address_validators.py`): Blockchain address validation for Solana and EVM chains
- **Message Consumption** (`src/core/mq_subscriber.py`): RabbitMQ message consumption in dedicated threads with automatic reconnection
- **Message Publishing** (`src/core/mq_subscriber.py`): RabbitMQ service with connection management, schema validation, and automatic buffering
- **Data Transformation** (`src/core/transformation.py`): Tweet data standardization with datetime parsing and URL extraction
- **Schema Validation** (`src/models/schemas.py`): Pydantic models ensuring data consistency, type safety, and token analysis results
- **Message Buffer** (`src/core/message_buffer.py`): Thread-safe FIFO buffer system for storing messages during RabbitMQ outages
- **Message Processing** (`src/handlers/` package): Modular message processing with sentiment analysis integration and dependency injection
- **Snipe Action Publishing** (`src/handlers/message_handler.py`): Automatic detection of token announcements and publishing of snipe actions to `actions_to_take` queue
- **Message Handler Factory** (`src/handlers/message_handler.py`): Clean dependency injection pattern using `create_message_handler()` for RabbitMQ message processing
- **Structured Logging**: JSON-formatted logs separated by level (error.log, warning.log, app.log)
- **Graceful Shutdown**: Signal handling with proper RabbitMQ connection and consumer cleanup

## Snipe Action System

The application automatically publishes **snipe actions** when AI agents detect cryptocurrency token announcements, enabling downstream services to act on newly discovered tokens.

### Snipe Action Workflow

1. **Tweet Processing**: Incoming tweets are processed through sentiment analysis
2. **Token Detection**: AI agents analyze content and return `TokenDetails` if a token is found
3. **Automatic Publishing**: When `TokenDetails` is detected, a `SnipeAction` is automatically created and published to the `actions_to_take` queue
4. **Message Structure**: Published messages follow a standardized format for downstream consumption

### Snipe Action Message Format

```json
{
  "action": "snipe",
  "params": {
    "chain_id": 1,
    "chain_name": "Ethereum",
    "token_address": "0x742d35Cc6765C0532575f5A2c0a078Df8a2D4e5e"
  }
}
```

### Configuration

- **`ACTIONS_QUEUE_NAME`**: Queue name for publishing snipe actions (default: `"actions_to_take"`)
- **Automatic Detection**: No manual configuration required - happens automatically when tokens are detected
- **Error Handling**: Comprehensive error handling with logging for failed publishes

### Integration

- **Next Service Integration**: Downstream services can consume from `actions_to_take` queue
- **Message Validation**: All snipe actions are validated using Pydantic schemas
- **Buffering Support**: Failed publishes are automatically buffered during RabbitMQ outages

## AI Agent System

The application features a sophisticated AI-powered sentiment analysis system for detecting cryptocurrency token announcements in social media content.

### Agent Architecture

The system uses three specialized PydanticAI agents, each optimized for different content types:

#### TextSearchAgent (`src/core/agents/text_search_agent.py`)
- **Purpose**: Analyzes tweet text content for token announcements and blockchain addresses
- **Capabilities**: 
  - Regex pattern matching for contract addresses
  - Blockchain identification using chain ID mapping
  - Token announcement detection in natural language
  - Address format validation (EVM vs Solana)
- **Input**: Tweet text content
- **Output**: TokenDetails with address, chain info, and announcement confirmation

#### ImageSearchAgent (`src/core/agents/image_search_agent.py`)
- **Purpose**: Extracts and analyzes text from images for token information
- **Capabilities**:
  - OCR text extraction from images
  - Pattern recognition for addresses and announcements
  - Same validation logic as TextSearchAgent applied to image text
  - Handles screenshots, charts, and promotional images
- **Input**: Image URLs from tweets
- **Output**: TokenDetails extracted from image content

#### FirecrawlAgent (`src/core/agents/firecrawl_agent.py`)
- **Purpose**: Scrapes and analyzes linked websites for token announcements
- **Capabilities**:
  - Web page scraping via Firecrawl MCP server
  - Content analysis of linked articles and websites
  - Deep inspection of external token announcement sources
  - Structured data extraction from web pages
- **Input**: URLs from tweet links
- **Output**: TokenDetails found in web content

### Result Schema

All agents return structured results using these Pydantic models:

```python
class TokenDetails(BaseModel):
    chain_id: Optional[int]              # Blockchain chain ID (1=Ethereum, 56=BSC, etc.)
    chain_name: Optional[str]            # Blockchain name
    is_release: Optional[bool]           # Whether this is a token release announcement
    chain_defined_explicitly: Optional[bool]  # Whether blockchain was explicitly mentioned
    definition_fragment: Optional[str]   # Text fragment mentioning blockchain
    token_address: str                   # Contract address

class NoTokenFound(BaseModel):           # No token information detected
    pass

class RelseaseAnnouncementWithoutDetails(BaseModel):  # Release detected but no details
    pass

# Union type for all possible results
SentimentAnalysisResult = Union[TokenDetails, NoTokenFound, RelseaseAnnouncementWithoutDetails]
```

### Agent Orchestration

The `sentiment_analyzer.py` module coordinates agent execution:

1. **Input Processing**: Receives tweet data with text, images, and links
2. **Agent Selection**: Determines which agents to run based on available content
3. **Parallel Execution**: Runs multiple agents concurrently for efficiency
4. **Result Merging**: Combines results using priority logic (TokenDetails > ReleaseAnnouncement > NoTokenFound)
5. **Output Integration**: Adds sentiment analysis results to tweet output schema

### Blockchain Support

The system supports major blockchain networks:

**EVM-Compatible Chains**:
- Ethereum Mainnet (Chain ID: 1)
- BNB Smart Chain (Chain ID: 56)
- Polygon (Chain ID: 137)
- Arbitrum One (Chain ID: 42161)
- Optimism (Chain ID: 10)
- Avalanche C-Chain (Chain ID: 43114)
- Base (Chain ID: 8453)
- And 20+ additional EVM chains

**Non-EVM Chains**:
- Solana (Base58 address validation)

### Address Validation

Robust address validation ensures accuracy:

- **EVM Addresses**: Regex pattern `^0x[a-fA-F0-9]{40}$` with checksum validation
- **Solana Addresses**: Base58 decoding with 32-byte validation and length checks
- **Format Detection**: Automatic blockchain type detection based on address format

## RabbitMQ Connection Monitoring

The application includes sophisticated RabbitMQ connection monitoring to ensure reliable message delivery and automatic recovery from connection failures.

### Monitor Features

- **Automatic Health Checks**: Periodic connection health monitoring with configurable intervals
- **Intelligent Reconnection**: Automatic reconnection attempts with exponential backoff and retry limits
- **Status Tracking**: Connection state monitoring with failure counting and status change detection
- **Background Operation**: Non-blocking monitoring in dedicated daemon threads
- **Graceful Shutdown**: Clean monitoring thread termination during application shutdown
- **Environment Configuration**: Fully configurable via environment variables

### Connection Monitoring Process

1. **Health Check Cycle**: Monitor performs periodic health checks using `MQMessenger.is_connected()` and `MQMessenger.test_connection()`
2. **Failure Detection**: Tracks consecutive connection failures and logs status changes
3. **Automatic Reconnection**: Attempts reconnection using `MQMessenger.reconnect()` method with fallback to `close()` + `connect()`
4. **Retry Logic**: Implements configurable retry attempts with delays between reconnection attempts
5. **Status Logging**: Comprehensive logging of connection status changes, failures, and recovery

### Monitor Integration

The monitor is integrated into the main application lifecycle:

```python
# Initialize RabbitMQ connection monitor
connection_monitor = RabbitMQConnectionMonitor.from_env(mq_messenger)
connection_monitor.start()

# Graceful shutdown handling
def shutdown_handler(signum, frame):
    connection_monitor.stop()  # Stop monitor first
    ws_manager.shutdown()      # Then shutdown WebSocket
    mq_messenger.close()       # Finally close MQ connection
```

### Monitor Status Information

The monitor provides real-time status information via `get_status()`:
- **is_running**: Monitor thread operational status
- **last_connection_status**: Most recent connection health status
- **consecutive_failures**: Current failure count for retry logic
- **max_retry_attempts**: Configured maximum retry attempts
- **check_interval**: Health check frequency in seconds

## Message Buffer System

The application includes a sophisticated message buffer system to prevent message loss during RabbitMQ outages and ensure reliable message delivery.

### Buffer Features

- **FIFO Queue**: Messages are stored and retrieved in first-in-first-out order using `collections.deque`
- **Configurable Capacity**: Default buffer size of 10 messages, configurable via environment variables
- **Thread Safety**: All buffer operations are protected by threading locks for concurrent access
- **Automatic Overflow**: When buffer reaches capacity, oldest messages are automatically removed
- **Message Metadata**: Each buffered message includes timestamp and sequence information
- **Environment Configuration**: Fully configurable via `MESSAGE_BUFFER_ENABLED` and `MESSAGE_BUFFER_SIZE`

### Buffer Integration

The message buffer is seamlessly integrated into the MQMessenger publish workflow:

1. **Normal Operation**: Messages are published directly to RabbitMQ as usual
2. **Connection Failure**: Failed messages are automatically stored in the buffer instead of being lost
3. **Connection Restore**: RabbitMQ monitor triggers automatic buffer flush when connection is restored
4. **FIFO Processing**: Buffered messages are flushed in the order they were received
5. **Partial Failure Handling**: If some messages fail during flush, remaining messages stay in buffer

### Buffer Status Information

The buffer provides comprehensive status information via `get_buffer_status()`:
- **enabled**: Whether buffering is currently enabled
- **current_size**: Number of messages currently in buffer
- **max_size**: Maximum buffer capacity
- **is_full**: Whether buffer has reached capacity
- **is_empty**: Whether buffer contains no messages
- **oldest_message_timestamp**: Timestamp of oldest buffered message
- **newest_message_timestamp**: Timestamp of newest buffered message
- **oldest_message_age_seconds**: Age of oldest message in seconds

## Data Transformation and Schema Validation

The application includes a comprehensive data transformation and validation system to ensure consistent data structure and reliability across the pipeline.

### Schema Enforcement Features

- **Pydantic Models**: Type-safe data validation using Pydantic with automatic type coercion and validation
- **Data Source Attribution**: Structured tracking of message origin, author information, and platform source
- **Field Validation**: Custom validators for text content, URL lists, and data integrity
- **Fallback Values**: Default values for missing or invalid fields to ensure data consistency
- **Type Safety**: Automatic type checking and conversion with comprehensive error handling

### Transformation Pipeline

The transformation system standardizes tweet data format and extracts key information:

1. **Datetime Standardization**: Converts Twitter datetime strings (`"Sat Jul 19 22:54:07 +0000 2025"`) to Unix timestamps
2. **URL Processing**: Extracts and processes markdown-style links and media URLs from tweet entities
3. **Content Extraction**: Cleans and validates tweet text content with proper encoding handling
4. **Media Handling**: Processes extended entities for media URLs (images, videos) with HTTPS enforcement
5. **Author Attribution**: Maps tweet author information including username and user ID

### Schema Structure

**TweetOutput Schema**:
```python
{
    "data_source": {
        "name": "Twitter",           # Platform identifier  
        "author_name": "username",   # Tweet author username
        "author_id": "12345"         # Tweet author user ID
    },
    "createdAt": 1721765647,         # Unix timestamp
    "text": "Tweet content...",       # Processed tweet text
    "media": ["https://..."],        # Media URLs array
    "links": ["https://..."],        # External links array
    "sentiment_analysis": {          # AI-powered token detection results
        "chain_id": 1,               # Blockchain chain ID (1=Ethereum, 56=BSC, etc.)
        "chain_name": "Ethereum",    # Blockchain name
        "is_release": true,          # Whether this is a token release announcement
        "chain_defined_explicitly": true,  # Whether blockchain was explicitly mentioned
        "definition_fragment": "launching on Ethereum",  # Text fragment mentioning blockchain
        "token_address": "0x742d35Cc6765C0532575f5A2c0a078Df8a2D4e5e"  # Contract address
    }
}
```

**Sentiment Analysis Result Types**:
- **TokenDetails**: Complete token information with address and blockchain details
- **RelseaseAnnouncementWithoutDetails**: Token release detected but no specific details found  
- **NoTokenFound**: No token information detected in the content

### Integration with Message Publishing

- **Automatic Validation**: All tweet messages are validated against schema before RabbitMQ publishing
- **Error Handling**: Validation errors are logged with detailed diagnostic information
- **Fallback Processing**: Invalid data is processed with fallback values rather than being dropped
- **MQ Integration**: Seamless integration with MQMessenger for validated message publishing

### Transformation Testing

The transformation system includes comprehensive test coverage:
- **Schema Validation**: Tests for all field types and validation rules
- **Edge Cases**: Handling of malformed data, missing fields, and invalid formats
- **Datetime Processing**: Validation of Twitter datetime parsing with timezone handling
- **URL Extraction**: Testing of markdown link processing and media URL handling
- **Integration Testing**: End-to-end validation with tweet handler pipeline

## Testing

The project includes comprehensive unit tests for the WebSocket management functionality:

### Test Structure
```
tests/
├── __init__.py                    # Package initialization
├── conftest.py                    # Shared test fixtures
├── test_initialization.py         # WebSocketManager initialization tests (4 tests)
├── test_signal_handler.py         # Signal handler functionality tests (5 tests)
├── test_connection_management.py  # Connection management tests (8 tests)
├── test_websocket_lifecycle.py    # WebSocket lifecycle management tests (6 tests)
├── test_error_handling.py         # Comprehensive error handling tests (7 tests)
├── test_integration.py            # End-to-end integration tests (2 tests)
├── test_rabbitmq_monitor.py       # RabbitMQ connection monitor tests (23 tests)
├── test_mq_messenger.py           # MQMessenger functionality tests (37 tests with buffer integration)
├── test_mq_messenger_reconnect.py # MQMessenger reconnection tests
├── test_main_rabbitmq.py          # Main application RabbitMQ integration tests
├── test_message_buffer.py         # MessageBuffer comprehensive test suite (27 tests)
├── test_transformation.py         # Data transformation pipeline tests (27 tests)
└── test_tweet_handler.py          # Tweet handler with MQ integration tests

test_websocket_manager.py          # Main test suite entry point
conftest.py                        # Root-level fixtures for main runner
```

### Test Categories
- **Sentiment Analysis Tests**: AI agent coordination, result merging, and orchestration logic
- **Agent Integration Tests**: PydanticAI agent testing with real API calls and snapshot validation
- **Address Validation Tests**: Blockchain address validation for Solana and EVM chains
- **Transformation Tests**: Data transformation pipeline, schema validation, datetime parsing, URL extraction, edge cases
- **RabbitMQ Monitor Tests**: Connection monitoring, health checks, automatic reconnection, failure tracking, thread management, environment configuration
- **Message Buffer Tests**: Thread-safe buffer operations, FIFO queue management, and RabbitMQ integration
- **Tweet Handler Tests**: Message processing with sentiment analysis integration
- **Integration Tests**: End-to-end workflows, complete lifecycle management, and system integration

### Test Execution Options
```bash
# Run all tests (main entry point)
uv run pytest test_websocket_manager.py

# Run all tests (from tests directory)  
uv run pytest tests/

# Run individual test modules
uv run pytest tests/test_initialization.py -v
uv run pytest tests/test_signal_handler.py -v
uv run pytest tests/test_connection_management.py -v
uv run pytest tests/test_websocket_lifecycle.py -v
uv run pytest tests/test_error_handling.py -v
uv run pytest tests/test_integration.py -v
uv run pytest tests/test_rabbitmq_monitor.py -v
uv run pytest tests/test_transformation.py -v

# Run specific test classes
uv run pytest tests/test_connection_management.py::TestConnectionManagement -v
uv run pytest tests/test_websocket_lifecycle.py::TestWebSocketLifecycle -v
uv run pytest tests/test_error_handling.py::TestErrorHandling -v
uv run pytest tests/test_integration.py::TestIntegration -v
uv run pytest tests/test_rabbitmq_monitor.py::TestRabbitMQConnectionMonitor -v
uv run pytest tests/test_rabbitmq_monitor.py::TestRabbitMQMonitorEnvironmentIntegration -v
uv run pytest tests/test_transformation.py::TestTransformation -v

# Run with coverage reporting
uv run pytest test_websocket_manager.py --cov=src.core.websocket_manager --cov-report=term-missing

# Run specific test class
uv run pytest test_websocket_manager.py::TestWebSocketManagerInitialization

# Generate HTML coverage report
uv run pytest test_websocket_manager.py --cov=src.core.websocket_manager --cov-report=html
```

### Test Coverage
- **Sentiment Analysis Coverage**: Comprehensive testing of AI agent orchestration, result merging, and token detection workflows
- **Agent Integration Coverage**: Real-world testing of PydanticAI agents with API calls, snapshot validation, and error handling
- **Address Validation Coverage**: Complete testing of Solana and EVM address validation with edge cases and format detection
- **RabbitMQ Monitor Coverage**: Comprehensive test coverage with 23 test cases covering all monitor functionality
- **Transformation Coverage**: Complete pipeline testing with 27 test cases covering data transformation, schema validation, and integration
- **Message Buffer Coverage**: 27 test cases covering thread safety, FIFO operations, and RabbitMQ failure handling
- **Tested Components**: Sentiment analysis orchestration, AI agent coordination, blockchain address validation, message processing with token detection, RabbitMQ connection monitoring, data transformation pipeline, schema validation, tweet handler operations with AI integration, and message handler factory with dependency injection
- **Connection Management Tests** (8 tests): Connection lifecycle, retry logic, error handling, shutdown coordination
  - Successful WebSocket connection establishment
  - Connection retry logic with 5-second delays  
  - Graceful shutdown interrupting connection loop
  - Shutdown flag interrupting retry sleep periods
  - KeyboardInterrupt handling in connection loop
  - Exception handling with proper logging and traceback
  - WebSocket reference management (current_ws lifecycle)
  - Double shutdown check logic validation
- **WebSocket Lifecycle Tests** (6 tests): WebSocketApp creation, callback management, ping configuration, reference lifecycle
  - WebSocketApp creation with correct URL, headers, and callback parameters
  - Callback function assignment and identity verification
  - Ping interval (30s) and ping timeout (20s) parameter validation
  - current_ws reference lifecycle during normal connection flow
  - current_ws cleanup on exceptions (finally block execution)
  - WebSocket parameter order, types, and configuration validation
- **Error Handling Tests** (7 tests): Comprehensive error scenarios, exception recovery, cleanup mechanisms
  - Connection failure retry mechanism with different error types (ConnectionError, TimeoutError)
  - Shutdown flag checking during granular retry sleep periods (1-second intervals)
  - Finally block cleanup across multiple exception scenarios (Exception, KeyboardInterrupt, ConnectionError, RuntimeError)
  - WebSocket-specific exception handling (WebSocketException, WebSocketConnectionClosedException, OSError, ConnectionRefusedError, ConnectionAbortedError, BrokenPipeError, socket.error, ssl.SSLError)
  - Error logging during WebSocket close operations in signal handler
  - Edge case handling when WebSocketApp constructor raises exceptions
  - Multiple consecutive error recovery cycles with different exception types
- **Integration Tests** (2 tests): End-to-end workflow validation, complete system integration testing
  - Complete connection lifecycle from initialization to shutdown with state tracking
  - Signal-to-shutdown sequence testing with WebSocket close operations and cleanup
  - Manager state transitions during full workflow execution
  - Comprehensive logging validation throughout integration flows
  - Resource cleanup verification after complete operations
- **Remaining Coverage**: 4% uncovered lines primarily in edge case logging scenarios
- **RabbitMQ Monitor Tests** (23 tests): Comprehensive connection monitoring, health checks, and automatic reconnection testing
  - Monitor initialization with default and custom parameters
  - Environment variable configuration and factory method creation
  - Monitor start/stop lifecycle with proper thread management
  - Connection health check success and failure scenarios
  - Automatic reconnection attempts with retry logic and failure counting
  - Fallback reconnection methods when primary reconnect unavailable
  - Maximum retry attempt limits and proper error handling
  - Exception handling during reconnection attempts with comprehensive logging
  - Real-time status information tracking and reporting
  - Complete monitoring loop integration with graceful shutdown
  - Connection status change detection and logging
  - Thread shutdown with timeout handling and cleanup verification
  - Environment configuration integration testing
  - Main application integration patterns and lifecycle management
- **Message Buffer Tests** (27 tests): Comprehensive buffer functionality, thread safety, and integration testing
  - Buffer initialization with default and custom parameters
  - Environment variable configuration via `from_env()` factory method
  - Message addition, retrieval, and removal operations
  - FIFO queue ordering and overflow behavior with automatic oldest message removal
  - Thread safety validation with concurrent operations
  - Buffer capacity management and full/empty state detection
  - Message metadata handling including timestamps and sequence numbers
  - Buffer status reporting with comprehensive state information
  - Integration with MQMessenger for automatic message buffering on RabbitMQ failures
  - Flush operations with partial failure handling and message preservation
- **Transformation Tests** (27 tests): Comprehensive data transformation pipeline testing
  - Tweet data transformation with schema validation
  - Datetime parsing from Twitter format to Unix timestamps
  - URL extraction from markdown-style links and media entities
  - Data source attribution and author information mapping
  - Schema validation with Pydantic models and error handling
  - Edge cases including malformed data, missing fields, and invalid formats
  - Integration with tweet handler for end-to-end processing
  - Fallback values and data consistency validation
- **Sentiment Analysis Tests**: AI-powered token detection testing
  - Agent orchestration and coordination logic
  - Result merging with priority-based selection
  - Integration with tweet processing pipeline
  - Error handling for AI agent failures
- **Agent Integration Tests**: Real-world AI agent testing with live API calls
  - TextSearchAgent testing with various tweet content patterns
  - ImageSearchAgent testing with OCR and image analysis
  - FirecrawlAgent testing with web scraping scenarios
  - Snapshot testing for consistent agent responses
  - Chain ID detection and blockchain identification
  - Address validation across EVM and Solana networks
  - Token announcement detection accuracy
- **Address Validation Tests**: Blockchain address validation comprehensive testing
  - EVM address format validation with regex patterns
  - Solana address Base58 decoding and length validation
  - Edge cases for malformed addresses and invalid formats
  - Automatic blockchain type detection based on address format
- **Retry Wrapper Tests**: Agent retry logic comprehensive testing with exponential backoff
  - Progressive delay validation (1s, 2s, 4s, 8s) for retry attempts
  - TokenDetails success conditions and non-TokenDetails retry behavior
  - Maximum retry limits and timeout handling
  - Exception propagation and error recovery testing
  - Concurrent execution and thread safety validation

## Logging

- **Log Files**: Located in `logs/` directory with automatic rotation (10MB, 5 backups)
  - `error.log`: ERROR level messages only
  - `warning.log`: WARNING level and above
  - `app.log`: All log levels (INFO and above)
- **Environment**: Set `ENVIRONMENT=production` for JSON logs, `development` for console output
- **Format**: Structured logging with timestamps, context, and metadata

## Development Notes

### Application Design
- **AI-Powered Architecture**: Focused on cryptocurrency sentiment analysis with PydanticAI agents
- **Message-Centric Processing**: Built on RabbitMQ message consumption and processing foundation
- **Agent Orchestration**: Coordinates multiple AI agents for comprehensive token detection
- **Modular Architecture**: Separated concerns with dedicated agent modules, handlers, and utilities
- **Continuous Operation**: Designed for long-running sentiment analysis and message processing
- **Thread-Safe**: Consumer operations and agent coordination run in dedicated daemon threads
- **Integrated Processing**: MQSubscriber includes both consumption and publishing with sentiment analysis integration
- **Graceful Shutdown**: Signal handling ensures proper consumer, agent, and connection cleanup

### MQSubscriber Architecture
- **Dual Functionality**: Supports both message consumption and publishing
- **Thread Safety**: Consumer runs in separate daemon thread with proper synchronization
- **Connection Management**: Automatic reconnection handling for both consumers and publishers
- **Buffer Integration**: Seamless integration with message buffer for fault tolerance
- **Clean Shutdown**: Proper consumer cancellation and thread termination

### Handler Development
- **Factory Pattern**: Message handlers use factory functions with dependency injection for clean architecture
- **Separation of Concerns**: Tweet processing logic separated from RabbitMQ message handling
- **Dependency Injection**: MQSubscriber and other dependencies passed explicitly via closures
- **Modular Design**: Handlers organized in dedicated package with clear responsibilities
- **No Global State**: Eliminated global variables using closure-based dependency capture
- **Pure Functions**: Handlers are stateless and testable with consistent sentiment analysis integration
- **Individual Testing**: Each handler can be tested independently with mocked dependencies

### Agent Development
- **PydanticAI Integration**: All agents built on PydanticAI framework for structured AI interactions
- **Specialized Roles**: Each agent optimized for specific content types (text, images, web content)
- **Blockchain Intelligence**: Agents incorporate comprehensive blockchain knowledge and address validation
- **Robust Error Handling**: Retry logic, fallback mechanisms, and graceful degradation
- **Observability**: Full Logfire integration for monitoring agent performance and results
- **Testable Design**: Agents support both unit testing and integration testing with real API calls

### Configuration Management
- **Environment Variables**: RabbitMQ connection settings and AI agent configuration via environment variables
- **Environment Detection**: `ENVIRONMENT` setting controls logging format (development/production)
- **Queue Configuration**: Separate configuration for publishing and consuming queues
- **Authentication**: Optional username/password authentication support
- **AI Configuration**: OpenAI API keys, model selection, and agent retry settings
- **Blockchain Configuration**: Chain ID mapping and address validation patterns

### Architectural Benefits

The application demonstrates several architectural best practices:

- **Clean Architecture**: Separation of concerns with dedicated modules for specific responsibilities
- **Dependency Injection**: Factory pattern eliminates global variables and improves testability
- **Modular Design**: Handlers, agents, and core components are organized in logical packages
- **No Global State**: Closure-based dependency capture avoids global variable usage
- **Factory Pattern**: Message handlers use dependency injection for clean, testable code
- **Automatic Token Detection**: Seamless integration between AI analysis and action publishing
- **Message-Driven Architecture**: Asynchronous processing with RabbitMQ message queues
- **Fault Tolerance**: Built-in buffering, reconnection, and error handling mechanisms
- **Intelligent Retry Logic**: Exponential backoff retry wrapper for AI agents with progressive delays (1s, 2s, 4s, 8s)
- **Observability**: Comprehensive logging and tracing throughout the system

### Monitoring & Observability
- **Structured Logging**: All events and errors logged with contextual metadata
- **Message Logging**: Incoming messages are logged with routing key and metadata
- **Agent Monitoring**: AI agent execution tracking, performance metrics, retry attempt logging, and result tracking with exponential backoff delays
- **Connection Monitoring**: Automatic health checks and reconnection logging
- **Consumer Status**: Real-time monitoring of consumer thread status
- **Logfire Integration**: Comprehensive observability for PydanticAI agents with execution traces, performance metrics, and error tracking