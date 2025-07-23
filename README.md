# News-Powered Trading Signals - Tweets watcher

The first microservice in multi-module real-time news monitoring and trading signal generation system.
Connects to third-party provider via WebSocket to capture market-relevant tweets in real time for sentiment analysis and automated trading decisions.

## Features

- **Real-time Twitter Stream Processing**: WebSocket connection to Twitter's streaming API with automatic reconnection
- **Modular Event-driven Architecture**: Specialized handlers for different message types and connection events
- **RabbitMQ Message Publishing**: Reliable message queuing with schema validation and automatic buffering
- **Message Buffer System**: Thread-safe FIFO buffer prevents message loss during RabbitMQ outages
- **RabbitMQ Connection Monitoring**: Automatic health checks and reconnection with configurable retry logic
- **Data Transformation Pipeline**: Tweet standardization with datetime parsing and URL extraction
- **Schema Validation**: Pydantic models ensure data consistency and type safety
- **Dependency Injection**: Clean architecture with proper separation of concerns
- **Structured Logging**: JSON-formatted logs with level separation and automatic rotation
- **Comprehensive Testing**: 92% test coverage with 70+ unit tests across all components

## Technology Stack

- **Python 3.12** - Modern Python with type hints and advanced features
- **UV** - Fast, modern Python package manager
- **WebSocket Client** - Real-time Twitter API connections with reconnection logic
- **Pika** - RabbitMQ message publishing and connection monitoring
- **Pydantic** - Data validation and schema enforcement
- **Structlog** - Structured JSON logging with contextual metadata  
- **Pytest** - Comprehensive test suite with mocking and coverage

## Quick Start

### Prerequisites

- Python 3.12+
- UV package manager
- Twitter API key
- RabbitMQ server (for message publishing)

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
cp .env.example .env
# Edit .env and add your configuration (see Configuration section)
```

4. Run the application:
```bash
python main.py
```

## Configuration

Create a `.env` file with the following variables:

### Core Configuration
```env
TWITTERAPI_KEY=your_twitter_api_key_here
ENVIRONMENT=development  # or 'production' for JSON logs
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

## Architecture

### Modular Event-driven Design

The system uses a **modular event-driven WebSocket architecture** with dependency injection:

- **Main Application** (`main.py`): Orchestration and dependency injection coordination
- **WebSocket Manager** (`websocket_manager.py`): Connection lifecycle with integrated message processing
- **MQ Messenger** (`mq_messenger.py`): RabbitMQ publishing with schema validation and buffering
- **Data Transformation** (`transformation.py`): Tweet standardization and format conversion
- **Schema Validation** (`schemas.py`): Pydantic models for data consistency
- **RabbitMQ Monitor** (`rabbitmq_monitor.py`): Connection monitoring with automatic reconnection
- **Message Buffer** (`message_buffer.py`): Thread-safe FIFO buffer for RabbitMQ outages
- **Event Handlers** (`handlers/` package): Modular message and lifecycle event processing

### File Structure
```
├── main.py                    # Application entry point with dependency injection
├── websocket_manager.py       # WebSocket lifecycle management
├── mq_messenger.py            # RabbitMQ message publishing service
├── message_buffer.py          # Thread-safe FIFO message buffer
├── transformation.py          # Tweet data transformation pipeline
├── schemas.py                 # Pydantic models for data validation
├── rabbitmq_monitor.py        # RabbitMQ connection monitoring
├── logging_config.py          # Structured logging configuration
├── handlers/                  # Event and message handlers package
│   ├── connected.py          # Connection establishment handler
│   ├── ping.py               # Ping message handler with timing analysis
│   ├── tweet.py              # Tweet message handler with transformation
│   ├── unknown.py            # Unknown message type handler
│   ├── error.py              # WebSocket error handler with diagnostics
│   ├── close.py              # Connection close handler
│   └── open.py               # Connection open handler
├── tests/                     # Comprehensive test suite
└── logs/                      # Log files (auto-created)
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
uv run pytest tests/

# Run tests with coverage
uv run pytest test_websocket_manager.py --cov=websocket_manager --cov-report=term-missing

# Run specific test categories
uv run pytest tests/test_initialization.py -v
uv run pytest tests/test_rabbitmq_monitor.py -v
uv run pytest tests/test_transformation.py -v
uv run pytest tests/test_message_buffer.py -v

# Run all RabbitMQ-related tests
uv run pytest tests/test_rabbitmq_monitor.py tests/test_mq_messenger.py tests/test_main_rabbitmq.py -v

# Generate HTML coverage report
uv run pytest test_websocket_manager.py --cov=websocket_manager --cov-report=html
```

## Key Components

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

### Data Transformation Pipeline
- **Schema Validation**: Pydantic models with automatic type coercion
- **Datetime Standardization**: Twitter datetime to Unix timestamp conversion
- **URL Processing**: Extraction and processing of media URLs and external links
- **Content Validation**: Text cleaning and encoding handling with fallback values

## Testing

Comprehensive test suite with **92% coverage** across **70+ tests**:

### Test Categories
- **WebSocket Manager**: Initialization, connection management, lifecycle, error handling
- **RabbitMQ Monitor**: Health checks, reconnection, thread management (23 tests)
- **Message Buffer**: Thread safety, FIFO operations, integration (27 tests)  
- **Data Transformation**: Schema validation, datetime parsing, URL extraction (27 tests)
- **MQ Messenger**: Publishing, buffering, reconnection (37+ tests)
- **Integration**: End-to-end workflows and system integration

### Running Tests
```bash
# Run all tests with verbose output
uv run pytest tests/ -v

# Run specific test modules
uv run pytest tests/test_connection_management.py::TestConnectionManagement -v
uv run pytest tests/test_rabbitmq_monitor.py::TestRabbitMQConnectionMonitor -v
uv run pytest tests/test_transformation.py::TestTransformation -v
```

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