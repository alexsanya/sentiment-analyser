# AI-Powered Cryptocurrency Token Detection Service

![Cover picture](cover.png)

An AI-powered sentiment analysis microservice for cryptocurrency token detection, built on RabbitMQ message processing architecture. The application specializes in analyzing tweets and social media content to detect new cryptocurrency token announcements using advanced AI agents, automatically publishing snipe actions for downstream trading systems.

## Features

- **AI-Powered Token Detection**: PydanticAI agents analyze text, images, and web content for cryptocurrency token announcements
- **Multi-Agent Architecture**: Specialized agents for text analysis, image OCR, and web scraping with result merging
- **Automatic Snipe Actions**: Publishes structured snipe actions to `actions_to_take` queue when tokens are detected
- **Blockchain Address Validation**: Supports Solana and EVM chains with comprehensive address validation
- **RabbitMQ Message Processing**: Consumes tweets and publishes actions with schema validation and buffering
- **Message Buffer System**: Thread-safe FIFO buffer prevents message loss during RabbitMQ outages
- **RabbitMQ Connection Monitoring**: Automatic health checks and reconnection with configurable retry logic
- **Data Transformation Pipeline**: Tweet standardization with datetime parsing and URL extraction
- **Factory Pattern Architecture**: Clean dependency injection with no global state
- **Comprehensive Observability**: Logfire integration with PydanticAI instrumentation and structured logging
- **Comprehensive Testing**: 90%+ test coverage with integration tests for AI agents

## Technology Stack

- **Python 3.12** - Modern Python with type hints and advanced features
- **UV** - Fast, modern Python package manager
- **PydanticAI** - AI-powered agents for text analysis, image recognition, and web scraping
- **Pika** - RabbitMQ message consumption, publishing, and connection monitoring
- **Pydantic** - Data validation and schema enforcement with token detection models
- **Structlog** - Structured JSON logging with contextual metadata
- **Logfire** - Observability and instrumentation for PydanticAI agents
- **Base58** - Solana address validation
- **Pytest** - Comprehensive test suite with mocking, coverage, and snapshot testing

## Quick Start

### Prerequisites

- Python 3.12+
- UV package manager
- OpenAI API key (for PydanticAI agents)
- RabbitMQ server (for message processing)
- Optional: Firecrawl MCP server (for web scraping agent)

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd news_povered_trading
```

2. Install dependencies:
```bash
uv sync
```

3. Configure environment:
```bash
# Create .env file and add your configuration (see Configuration section)
touch .env
```

4. Run the application:
```bash
python main.py
```

## Configuration

Create a `.env` file with the following variables:

### Core Configuration
```env
ENVIRONMENT=development  # or 'production' for JSON logs
OPENAI_API_KEY=your_openai_api_key_here
```

### RabbitMQ Configuration
```env
RABBITMQ_HOST=localhost
RABBITMQ_PORT=5672
RABBITMQ_QUEUE=tweet_events
RABBITMQ_CONSUME_QUEUE=incoming_messages
ACTIONS_QUEUE_NAME=actions_to_take
RABBITMQ_USERNAME=admin              # Optional
RABBITMQ_PASSWORD=changeme           # Optional
```

### RabbitMQ Connection Monitoring
```env
RABBITMQ_MONITOR_ENABLED=true        # Enable/disable monitoring (default: true)
RABBITMQ_MONITOR_INTERVAL=30         # Health check interval in seconds (default: 30)
RABBITMQ_MAX_RETRY_ATTEMPTS=3        # Max reconnection attempts (default: 3)
RABBITMQ_RETRY_DELAY=5               # Delay between reconnection attempts (default: 5)
```

### Message Buffer Configuration
```env
MESSAGE_BUFFER_ENABLED=true          # Enable/disable buffering (default: true)
MESSAGE_BUFFER_SIZE=10               # Buffer capacity (default: 10)
```

### Sentiment Analysis Configuration
```env
SENTIMENT_MODEL_NAME=openai:gpt-4o   # AI model for analysis (default)
FIRECRAWL_MCP_SERVER_URL=http://localhost:3000/sse  # Optional web scraping
MAX_CONCURRENT_ANALYSIS=5            # Max concurrent agent operations (default: 5)
AGENT_RETRIES=4                      # Retry attempts for failed operations (default: 4)
```

### Logfire Configuration (Optional)
```env
LOGFIRE_ENABLED=true
LOGFIRE_TOKEN=your_logfire_token_here
LOGFIRE_SERVICE_NAME=tweets-notifier
LOGFIRE_ENVIRONMENT=development
SERVICE_VERSION=0.1.0
```

## Architecture

### AI-Powered Message Processing Design

The system uses a **clean architecture with AI-powered sentiment analysis** and dependency injection:

- **Main Application** (`main.py`): Application orchestration and message consumption coordination
- **Message Handler Factory** (`src/handlers/message_handler.py`): RabbitMQ message processing with dependency injection
- **AI Agent System** (`src/core/agents/` package): PydanticAI agents for text, image, and web content analysis
- **Sentiment Analyzer** (`src/core/sentiment_analyzer.py`): Agent orchestration and result merging
- **MQ Subscriber** (`src/core/mq_subscriber.py`): RabbitMQ consumption and publishing with schema validation
- **Data Transformation** (`src/core/transformation.py`): Tweet standardization and format conversion
- **Schema Validation** (`src/models/schemas.py`): Pydantic models for tokens, tweets, and snipe actions
- **RabbitMQ Monitor** (`src/core/rabbitmq_monitor.py`): Connection monitoring with automatic reconnection
- **Message Buffer** (`src/core/message_buffer.py`): Thread-safe FIFO buffer for RabbitMQ outages
- **Address Validators** (`src/core/utils/` package): Blockchain address validation for Solana and EVM chains

### File Structure
```
├── main.py                    # Application entry point for RabbitMQ message processing
├── src/                       # Source code package
│   ├── config/               # Configuration modules
│   │   ├── logging_config.py # Structured logging configuration
│   │   ├── logfire_config.py # Logfire observability configuration
│   │   └── sentiment_config.py # Sentiment analysis and agent configuration
│   ├── core/                 # Core business logic modules
│   │   ├── agents/          # AI sentiment analysis agents
│   │   │   ├── text_search_agent.py # Text content analysis agent
│   │   │   ├── image_search_agent.py # Image text extraction agent
│   │   │   └── firecrawl_agent.py # Web scraping agent
│   │   ├── utils/           # Utility functions
│   │   │   └── address_validators.py # Blockchain address validation
│   │   ├── sentiment_analyzer.py # Main sentiment analysis orchestration
│   │   ├── mq_subscriber.py # RabbitMQ message consumption and publishing service
│   │   ├── message_buffer.py # Thread-safe FIFO message buffer
│   │   ├── transformation.py # Tweet data transformation pipeline
│   │   └── rabbitmq_monitor.py # RabbitMQ connection monitoring
│   ├── handlers/             # Message handlers package
│   │   ├── tweet.py         # Tweet message handler with transformation and sentiment analysis
│   │   └── message_handler.py # RabbitMQ message handler factory with snipe action publishing
│   └── models/               # Data models and schemas
│       └── schemas.py       # Pydantic models for tokens, tweets, and snipe actions
├── tests/                    # Comprehensive test suite with AI agent integration tests
├── examples/                 # Example files and sample data
├── docs/                     # Documentation files
├── logs/                     # Log files (auto-created)
└── docker-compose.yml        # Multi-service Docker orchestration
```

## Development Commands

### Running the Application
```bash
# Run the application
python main.py

# Install dependencies
uv sync

# Add new dependencies
uv add <package-name>
```

### Testing
```bash
# Run all tests
uv run pytest tests/ -v

# Run specific test categories
uv run pytest tests/test_mq_subscriber.py -v
uv run pytest tests/test_rabbitmq_monitor.py -v
uv run pytest tests/test_transformation.py -v
uv run pytest tests/test_message_buffer.py -v
uv run pytest tests/test_tweet_handler.py -v
uv run pytest tests/test_sentiment_analyzer.py -v
uv run pytest tests/test_address_validators.py -v

# Run AI agent integration tests (requires OPENAI_API_KEY)
OPENAI_API_KEY=your_key uv run pytest tests/integration/test_agents_integration.py -v

# Run tests with coverage
uv run pytest tests/test_mq_subscriber.py --cov=src.core.mq_subscriber --cov-report=term-missing
uv run pytest tests/test_sentiment_analyzer.py --cov=src.core.sentiment_analyzer --cov-report=term-missing

# Skip integration tests (run only unit tests)
uv run pytest -m "not integration" -v

# Update snapshots when agent responses change
uv run pytest tests/integration/test_agents_integration.py --snapshot-update
```

## Key Components

### AI Agent System
- **TextSearchAgent**: Analyzes tweet text content for token announcements and blockchain addresses
- **ImageSearchAgent**: Extracts text from images and analyzes for token information using OCR
- **FirecrawlAgent**: Scrapes linked websites for token announcement content
- **Multi-Agent Coordination**: Concurrent execution with result merging and priority logic
- **Chain Detection**: Supports Solana and 20+ EVM chains with automatic address validation

### Snipe Action Publishing
- **Automatic Detection**: When `TokenDetails` are found, publishes structured snipe actions
- **Message Format**: Standardized JSON with `action: "snipe"` and token parameters
- **Queue Integration**: Publishes to configurable `actions_to_take` queue for downstream services
- **Error Handling**: Comprehensive error handling with logging and buffering support

### Message Processing Pipeline
- **Factory Pattern**: Clean dependency injection using `create_message_handler()` factory
- **Tweet Analysis**: Processes incoming tweets through AI sentiment analysis pipeline
- **Schema Validation**: Pydantic models for tweets, tokens, and snipe actions
- **Data Transformation**: Tweet standardization with datetime parsing and URL extraction

### RabbitMQ Connection Monitoring
- **Automatic Health Checks**: Periodic connection monitoring with configurable intervals
- **Intelligent Reconnection**: Automatic reconnection with retry limits and exponential backoff
- **Background Operation**: Non-blocking monitoring in dedicated daemon threads
- **Status Tracking**: Real-time connection state monitoring and failure counting

### Message Buffer System  
- **FIFO Queue**: Thread-safe message storage during RabbitMQ outages
- **Automatic Overflow**: Oldest messages removed when buffer reaches capacity
- **Seamless Integration**: Automatic buffering on connection failures, automatic flush on reconnection
- **Configurable Capacity**: Environment-configurable buffer size and behavior

## Testing

Comprehensive test suite with **90%+ coverage** across **80+ tests**:

### Test Categories
- **AI Agents**: Sentiment analysis orchestration, agent coordination, result merging
- **Agent Integration**: Real-world AI agent testing with live API calls and snapshot validation
- **Address Validation**: Blockchain address validation for Solana and EVM chains
- **RabbitMQ Subscriber**: Message consumption, publishing, buffering, reconnection (43 tests)
- **RabbitMQ Monitor**: Health checks, reconnection, thread management (23 tests)
- **Message Buffer**: Thread safety, FIFO operations, integration (27 tests)
- **Data Transformation**: Schema validation, datetime parsing, URL extraction (27 tests)
- **Tweet Handler**: Message processing with sentiment analysis integration
- **Message Handler**: Factory pattern and dependency injection testing

### Running Tests
```bash
# Run all tests with verbose output
uv run pytest tests/ -v

# Run specific test modules
uv run pytest tests/test_mq_subscriber.py::TestMQSubscriberPublish -v
uv run pytest tests/test_sentiment_analyzer.py::TestSentimentAnalyzer -v
uv run pytest tests/test_address_validators.py::TestAddressValidation -v

# Run AI agent integration tests (requires OpenAI API key)
OPENAI_API_KEY=your_key uv run pytest tests/integration/test_agents_integration.py -v
```

### Snipe Action Testing

The application includes comprehensive testing for the snipe action workflow:

```bash
# Test snipe action message creation and publishing
uv run pytest tests/test_tweet_handler.py -v

# Test message handler factory pattern
uv run pytest tests/ -k "message_handler" -v

# Test complete sentiment analysis to snipe action pipeline
OPENAI_API_KEY=your_key uv run pytest tests/integration/ -v
```

## Snipe Action Workflow

The application automatically publishes **snipe actions** when AI agents detect cryptocurrency token announcements:

### 1. Tweet Processing
```bash
# Incoming tweet message from RabbitMQ queue
{
  "id": "12345",
  "text": "🚀 New token launching on Ethereum! Contract: 0x742d35Cc6765C0532575f5A2c0a078Df8a2D4e5e",
  "author_name": "crypto_trader",
  "created_at": "Sat Jul 19 22:54:07 +0000 2025"
}
```

### 2. AI Analysis
- **TextSearchAgent** analyzes tweet content for token announcements
- **ImageSearchAgent** processes any attached images for token information
- **FirecrawlAgent** scrapes linked websites for additional token details
- Results are merged with priority logic (`TokenDetails` > `ReleaseAnnouncement` > `NoTokenFound`)

### 3. Automatic Snipe Action Publishing
When `TokenDetails` are detected, a snipe action is automatically published:

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

### 4. Downstream Integration
- **Queue**: Published to `actions_to_take` queue (configurable via `ACTIONS_QUEUE_NAME`)
- **Next Service**: Downstream trading services consume snipe actions for automated token acquisition
- **Error Handling**: Failed publishes are buffered during RabbitMQ outages

## Logging

Structured logs are automatically written to the `logs/` directory with rotation (10MB, 5 backups):

- **`error.log`** - ERROR level messages only
- **`warning.log`** - WARNING level and above  
- **`app.log`** - All application logs (INFO and above)

**Environment Control**: 
- `ENVIRONMENT=development` - Console output with colors
- `ENVIRONMENT=production` - JSON-formatted logs for analysis

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality (maintain 90%+ coverage)
4. Ensure all tests pass: `uv run pytest tests/`
5. Follow the existing code patterns and dependency injection architecture
6. Submit a pull request with clear description

## Support

For issues and questions, please open a GitHub issue with:
- Python version and environment details
- Relevant log excerpts from `logs/` directory
- Steps to reproduce any issues