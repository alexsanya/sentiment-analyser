# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AI-powered sentiment analysis microservice for cryptocurrency token detection and Trump-Zelenskyy meeting analysis, built on RabbitMQ message processing. Uses PydanticAI agents for text/image analysis, web scraping, topic filtering, duplicate detection, and geopolitical outcome analysis.

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
# Run application
python main.py

# Dependencies
uv sync
uv add <package-name>

# Testing
uv run pytest tests/ -v
uv run pytest tests/test_sentiment_analyzer.py --cov=src.core.sentiment_analyzer --cov-report=term-missing
OPENAI_API_KEY=your_key uv run pytest tests/integration/test_agents_integration.py -v

# Docker
docker-compose up -d
docker-compose logs -f news-watcher
docker-compose down

# RabbitMQ Management UI: http://localhost:15672 (admin/changeme)
```

## Architecture

**AI-powered sentiment analysis architecture**:

- **Main Application** (`main.py`): Threaded message consumption
- **Sentiment Analyzer** (`src/core/sentiment_analyzer.py`): Agent coordination with topic-priority logic
- **AI Agents** (`src/core/agents/`): PydanticAI agents for text/image/web analysis, topic filtering, duplicate detection, geopolitical analysis
- **News Database** (`src/core/news_database.py`): Thread-safe in-memory storage for duplicate prevention
- **MQ Subscriber** (`src/core/mq_subscriber.py`): RabbitMQ consumption/publishing with buffering
- **Data Transformation** (`src/core/transformation.py`): Tweet standardization pipeline
- **Schema Validation** (`src/models/schemas.py`): Pydantic models for data validation
- **RabbitMQ Monitor** (`src/core/rabbitmq_monitor.py`): Connection monitoring with auto-reconnection
- **Message Handlers** (`src/handlers/`): Threaded processing with sentiment analysis integration
- **Address Validators** (`src/core/utils/`): Blockchain address validation (Solana/EVM)
- **Configuration** (`src/config/`): Logging, Logfire observability, sentiment analysis config

### AI Agent System

- **TextSearchAgent**: Analyzes tweet text for token announcements/blockchain addresses
- **ImageSearchAgent**: OCR text extraction from images for token info
- **FirecrawlAgent**: Web scraping for token announcements
- **TopicFilterAgent**: Filters Trump-Zelenskyy meeting actionable outcomes (Grok-4)
- **DuplicateDetectorAgent**: Prevents news duplication using semantic analysis (Grok-4)
- **GeoExpertAgent**: Analyzes meeting outcomes for geopolitical impact and peace likelihood (Grok-4)

**Orchestration**: Topic-priority logic, result merging, dual-path workflows
**Address Validation**: Solana/EVM validation with regex/crypto validation

### Handler Architecture

- `src/handlers/tweet.py`: Tweet processing with transformation/sentiment analysis
- `src/handlers/message_handler.py`: Threaded RabbitMQ handler (thread-per-message)
- `src/handlers/__init__.py`: Centralized exports and factory functions

### Threaded Message Processing

**Thread-per-Message Pattern**: Each message spawns dedicated processing thread for long-running sentiment analysis

**Key Features**:
- Thread-safe acknowledgment via `connection.add_callback_threadsafe()`
- Concurrent processing without blocking consumer
- Graceful shutdown with thread completion wait
- Automatic thread cleanup and status monitoring

**Benefits**: Higher throughput, better CPU utilization, reduced latency, natural scaling

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
│   │   │   ├── topic_filter_agent.py # Trump-Zelenskyy meeting outcome filtering agent
│   │   │   ├── duplicate_detector_agent.py # News duplicate detection agent
│   │   │   ├── geo_expert_agent.py # Geopolitical expert agent for meeting analysis
│   │   │   └── retry_wrapper.py # Exponential backoff retry wrapper for agents
│   │   ├── utils/           # Utility functions
│   │   │   ├── __init__.py  # Utility exports
│   │   │   └── address_validators.py # Blockchain address validation
│   │   ├── sentiment_analyzer.py # Main sentiment analysis orchestration
│   │   ├── news_database.py # Thread-safe in-memory news storage for duplicate detection
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
│       └── schemas.py       # Pydantic models for data validation, token details, sentiment analysis, and topic analysis
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
│   ├── tg_bots_dialog.ipynb # Jupyter notebook for bot dialog examples
│   ├── PeaceTalksAnalyze.ipynb # Jupyter notebook for Trump-Zelenskyy meeting analysis examples
│   └── docker-compose.example.yml # Example Docker Compose configuration with environment variables
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

### Environment Variables

**RabbitMQ**:
- `RABBITMQ_HOST`, `RABBITMQ_PORT`, `RABBITMQ_QUEUE`, `ACTIONS_QUEUE_NAME`
- `RABBITMQ_MONITOR_ENABLED`, `RABBITMQ_MONITOR_INTERVAL`
- `MESSAGE_BUFFER_ENABLED`, `MESSAGE_BUFFER_SIZE`

**AI Agents**:
- `OPENAI_API_KEY` (token detection), `OPENROUTER_API_KEY` (topic analysis)
- `SENTIMENT_MODEL_NAME` (default: "openai:gpt-4o")
- `TOPIC_ANALYSIS_ENABLED`, `TOKEN_DETECTION_ENABLED`, `PEACE_TALKS_TOPIC_ENABLED`

**Observability**:
- `LOGFIRE_ENABLED`, `LOGFIRE_TOKEN`, `LOGFIRE_SERVICE_NAME`

**Blockchain Support**:
- EVM chains (Ethereum, BSC, Polygon, Arbitrum, etc.)
- Solana (Base58 validation)

## Docker

**Services**:
- **news-watcher**: Python 3.12 slim, UV package manager
- **rabbitmq**: rabbitmq:3.13-management (ports 5672/15672)
- **trading_network**: Custom bridge network

**Features**: Health checks, auto-restart, volume persistence, environment integration

## Key Components

- **Sentiment Analysis** (`src/core/sentiment_analyzer.py`): AI agent coordination with Trump-Zelenskyy workflow
- **AI Agents** (`src/core/agents/`): PydanticAI agents for analysis/filtering/duplicate detection
- **News Database** (`src/core/news_database.py`): Thread-safe news storage with duplicate prevention
- **MQ Subscriber** (`src/core/mq_subscriber.py`): RabbitMQ consumption/publishing
- **Data Transformation** (`src/core/transformation.py`): Tweet standardization
- **Schema Validation** (`src/models/schemas.py`): Pydantic models for meeting analysis
- **Message Buffer** (`src/core/message_buffer.py`): Thread-safe FIFO buffer
- **Message Handlers** (`src/handlers/`): Processing with Trump-Zelenskyy workflow integration
- **Action Publishing**: Auto-detection of tokens/meeting outcomes → snipe/trade actions
- **Logging**: JSON logs by level (error.log, warning.log, app.log)
- **Graceful Shutdown**: Proper cleanup

## Action System

**Snipe Actions**: Auto-published when tokens detected
**Trade Actions**: Published for Trump-Zelenskyy meeting outcomes (score ≥6)
**Notify Actions**: Published for all topic-relevant content

**Format**: `{"action": "snipe|trade|notify", "params": {...}}`
**Queue**: `actions_to_take` (configurable)
**Features**: Schema validation, buffering support

## AI Agent System

**Token Detection Agents**:
- **TextSearchAgent**: Text analysis for token announcements/addresses
- **ImageSearchAgent**: OCR extraction from images
- **FirecrawlAgent**: Web scraping for token announcements

**Topic Analysis Agents**:
- **TopicFilterAgent**: Trump-Zelenskyy meeting outcome filtering (Grok-4)
- **DuplicateDetectorAgent**: News duplicate detection using semantic analysis (Grok-4)
- **GeoExpertAgent**: Meeting outcome analysis for geopolitical impact (Grok-4)

**Features**: Regex patterns, blockchain ID mapping, address validation (EVM/Solana)

### Schemas

**Token Detection**: `TokenDetails`, `NoTokenFound`, `RelseaseAnnouncementWithoutDetails`
**Topic Analysis**: `TopicFilter` (match boolean), `AlignmentData` (score 1-10)
**Meeting Analysis**: `DuplicateCheckResult` (boolean), `OutcomeAnalysis`, `MeetingAnalysis` (overall score 1-10)
**Actions**: `SnipeAction`, `TradeAction`, `NotifyAction` with respective params
**News Storage**: `NewsDatabase` class for thread-safe duplicate prevention

### Agent Orchestration

1. Input processing (tweet text/images/links)
2. Agent selection based on content type
3. Parallel execution for efficiency
4. Result merging with priority logic
5. Output integration

**Supported Blockchains**: Ethereum, BSC, Polygon, Arbitrum, Optimism, Avalanche, Base, Solana (+20 EVM chains)

## Trump-Zelenskyy Meeting Analysis System

**Trump-Zelenskyy Workflow** (`analyze_with_trump_zelenskyy_workflow`):
1. `TopicFilterAgent` checks for actionable Trump-Zelenskyy meeting outcomes
2. If topic matches → `DuplicateDetectorAgent` checks against NewsDatabase
3. If not duplicate → Add to NewsDatabase → `GeoExpertAgent` analyzes all stored outcomes
4. If duplicate or no topic match → token detection agents
5. Generate appropriate actions (trade/snipe/notify)

**Trade Logic**:
- Overall score ≥6: Generate trade actions (ETHUSDT long)
- Score 6-7: leverage=5, margin=$300
- Score >7: leverage=7, margin=$500

**Duplicate Prevention**: Semantic analysis prevents redundant news processing
**NewsDatabase**: Thread-safe in-memory storage with global singleton pattern
**Benefits**: Reduced API costs, comprehensive analysis, duplicate prevention

## RabbitMQ Connection Monitoring

**Features**: Automatic health checks, intelligent reconnection with exponential backoff, status tracking, background operation

**Process**: Periodic health checks → failure detection → auto-reconnection with retry logic → status logging

**Integration**: Lifecycle management with graceful shutdown

## Message Buffer System

**Features**: FIFO queue (`collections.deque`), configurable capacity (default 10), thread safety, automatic overflow

**Integration**: Normal operation → failure buffering → auto-flush on reconnection

**Status**: Real-time buffer state monitoring

## Data Transformation

**Pipeline**: Datetime standardization → URL processing → content extraction → media handling → author attribution

**Schema**: Pydantic models with type safety, data source attribution, field validation, fallback values

**Integration**: Auto-validation before RabbitMQ publishing, error handling, MQ integration

## Testing

**Categories**: Sentiment analysis, agent integration, address validation, transformation, RabbitMQ monitor, message buffer, tweet handler, integration

**Coverage**: AI agent coordination, PydanticAI testing with real API calls, blockchain validation, pipeline testing, connection monitoring, thread safety, end-to-end workflows

**Execution**: `uv run pytest tests/ -v`, integration tests require API keys



## Logging

**Files**: `logs/error.log`, `logs/warning.log`, `logs/app.log` (auto-rotation 10MB, 5 backups)
**Format**: JSON (production) / console (development), structured with timestamps/context

## Development Notes

**Architecture**: AI-powered, message-centric processing with PydanticAI agents, modular design, thread-safe operations

**Patterns**: Factory pattern for handlers, dependency injection, clean separation of concerns, no global state

**Benefits**: Fault tolerance, intelligent retry logic (exponential backoff), comprehensive observability

**Agent Design**: Specialized roles, blockchain intelligence, robust error handling, testable with real API calls