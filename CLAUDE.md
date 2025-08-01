# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is the RabbitMQ message processor microservice, a component designed for consuming and processing messages from RabbitMQ queues. The application focuses on message consumption, processing, and logging, with support for publishing capabilities as well. It can be integrated into larger systems for real-time message processing and data transformation.

## Technology Stack

- **Language**: Python 3.12
- **Package Manager**: UV (modern Python package manager)
- **Key Dependencies**: 
  - `pika` for RabbitMQ message consumption, publishing, and connection monitoring
  - `pydantic` for data validation and schema enforcement
  - `dotenv` for environment variable management
  - `structlog` for structured logging with JSON output
- **Testing**: 
  - `pytest` for unit testing framework
  - `pytest-mock` for mocking functionality
  - `pytest-cov` for coverage reporting
- **Containerization**:
  - `Docker` for containerization with Python 3.12 slim image
  - `docker-compose` for multi-service orchestration
  - Custom bridge network for service communication
  - Volume mounts for data persistence and log access

## Development Commands

```bash
# Run the application
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

**Simplified message processing architecture** focused on RabbitMQ operations:

- **Main Application** (`main.py`): Application orchestration and message consumption coordination
- **MQ Subscriber** (`src/core/mq_subscriber.py`): RabbitMQ message consumption and publishing service with schema validation and automatic buffering
- **Data Transformation** (`src/core/transformation.py`): Tweet data standardization and format conversion pipeline
- **Schema Validation** (`src/models/schemas.py`): Pydantic models for data validation and consistency
- **RabbitMQ Monitor** (`src/core/rabbitmq_monitor.py`): Automatic connection monitoring with health checks and reconnection logic
- **Message Handlers** (`src/handlers/` package): Modular message processing
- **Structured Logging** (`src/config/logging_config.py`): Centralized logging configuration

### Handler Architecture

**Message Handlers** (process incoming message content):
- `src/handlers/tweet.py`: Tweet message processing with transformation pipeline and data validation

**Handler Package** (`src/handlers/__init__.py`): Centralized exports for message handlers

### File Structure
```
├── main.py                    # Application entry point for RabbitMQ message processing
├── src/                       # Source code package
│   ├── __init__.py           # Package initialization
│   ├── config/               # Configuration modules
│   │   ├── __init__.py      # Package exports
│   │   └── logging_config.py # Structured logging configuration
│   ├── core/                 # Core business logic modules
│   │   ├── __init__.py      # Package exports
│   │   ├── mq_subscriber.py # RabbitMQ message consumption and publishing service
│   │   ├── message_buffer.py # Thread-safe FIFO message buffer for RabbitMQ outages
│   │   ├── transformation.py # Tweet data transformation and standardization pipeline
│   │   └── rabbitmq_monitor.py # RabbitMQ connection monitoring with automatic reconnection
│   ├── handlers/             # Message handlers package
│   │   ├── __init__.py      # Package exports
│   │   └── tweet.py         # Tweet message handler with transformation pipeline
│   └── models/               # Data models and schemas
│       ├── __init__.py      # Package exports
│       └── schemas.py       # Pydantic models for data validation and schema enforcement
├── tests/                    # Comprehensive test suite
│   ├── __init__.py          # Package initialization
│   ├── conftest.py          # Shared test fixtures
│   ├── test_mq_subscriber.py # MQSubscriber functionality tests
│   ├── test_rabbitmq_monitor.py # RabbitMQ connection monitor tests
│   ├── test_message_buffer.py # MessageBuffer tests
│   ├── test_transformation.py # Transformation pipeline tests
│   ├── test_tweet_handler.py # Tweet handler tests
│   └── test_main_rabbitmq.py # Main application integration tests
├── examples/                # Example files and sample data
│   └── tweet-sample.json   # Sample tweet data for testing and development
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
- **`RABBITMQ_USERNAME`**: Optional username for authentication
- **`RABBITMQ_PASSWORD`**: Optional password for authentication

Example `.env` configuration:
```bash
# RabbitMQ Connection
RABBITMQ_HOST=localhost
RABBITMQ_PORT=5672
RABBITMQ_QUEUE=tweet_events
RABBITMQ_CONSUME_QUEUE=incoming_messages
RABBITMQ_USERNAME=admin
RABBITMQ_PASSWORD=changeme
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

- **Message Consumption** (`src/core/mq_subscriber.py`): RabbitMQ message consumption in dedicated threads with automatic reconnection
- **Message Publishing** (`src/core/mq_subscriber.py`): RabbitMQ service with connection management, schema validation, and automatic buffering
- **Data Transformation** (`src/core/transformation.py`): Tweet data standardization with datetime parsing and URL extraction
- **Schema Validation** (`src/models/schemas.py`): Pydantic models ensuring data consistency and type safety
- **Message Buffer** (`src/core/message_buffer.py`): Thread-safe FIFO buffer system for storing messages during RabbitMQ outages
- **Message Processing** (`src/handlers/` package): Modular message processing and transformation
- **Message Logging** (`main.py`): Simple message handler that logs all incoming messages with metadata
- **Structured Logging**: JSON-formatted logs separated by level (error.log, warning.log, app.log)
- **Graceful Shutdown**: Signal handling with proper RabbitMQ connection and consumer cleanup

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
    "links": ["https://..."]         # External links array
}
```

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
- **Initialization Tests**: WebSocketManager setup, callback assignment, initial state validation
- **Signal Handler Tests**: Graceful shutdown, WebSocket closing, error handling, different signal types
- **Connection Management Tests**: WebSocket connection lifecycle, retry logic, error handling, shutdown coordination
- **WebSocket Lifecycle Tests**: WebSocketApp creation, callback assignment, ping parameters, current_ws reference management
- **Error Handling Tests**: Comprehensive error scenarios, exception types, retry mechanisms, finally block cleanup
- **Integration Tests**: End-to-end workflows, complete lifecycle management, signal-to-shutdown sequences
- **RabbitMQ Monitor Tests**: Connection monitoring, health checks, automatic reconnection, failure tracking, thread management, environment configuration
- **Transformation Tests**: Data transformation pipeline, schema validation, datetime parsing, URL extraction, edge cases

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
- **WebSocket Manager Coverage**: 92% of src/core/websocket_manager.py (70/70 tests passing across all components)
- **RabbitMQ Monitor Coverage**: Comprehensive test coverage with 23 test cases covering all monitor functionality
- **Tested Components**: WebSocketManager initialization, signal handling, connection management, WebSocket lifecycle, comprehensive error handling, integration workflows, MQMessenger functionality, RabbitMQ connection monitoring, data transformation pipeline, schema validation, and tweet handler operations
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

## Logging

- **Log Files**: Located in `logs/` directory with automatic rotation (10MB, 5 backups)
  - `error.log`: ERROR level messages only
  - `warning.log`: WARNING level and above
  - `app.log`: All log levels (INFO and above)
- **Environment**: Set `ENVIRONMENT=production` for JSON logs, `development` for console output
- **Format**: Structured logging with timestamps, context, and metadata

## Development Notes

### Application Design
- **Message-Centric Architecture**: Focused on RabbitMQ message consumption and processing
- **Modular Architecture**: Separated concerns with dedicated handler modules for maintainability
- **Continuous Operation**: Designed for long-running message processing
- **Thread-Safe**: Consumer operations run in dedicated daemon threads
- **Integrated Processing**: MQSubscriber includes both consumption and publishing capabilities
- **Graceful Shutdown**: Signal handling ensures proper consumer and connection cleanup

### MQSubscriber Architecture
- **Dual Functionality**: Supports both message consumption and publishing
- **Thread Safety**: Consumer runs in separate daemon thread with proper synchronization
- **Connection Management**: Automatic reconnection handling for both consumers and publishers
- **Buffer Integration**: Seamless integration with message buffer for fault tolerance
- **Clean Shutdown**: Proper consumer cancellation and thread termination

### Handler Development
- **Simple Processing**: Handlers focus on data transformation and processing logic
- **No Dependencies**: Tweet handler no longer requires MQSubscriber injection
- **Pure Functions**: Handlers are stateless and testable
- **Consistent Interface**: All handlers follow established patterns for logging and error handling
- **Individual Testing**: Each handler can be tested independently

### Configuration Management
- **Environment Variables**: RabbitMQ connection settings via environment variables
- **Environment Detection**: `ENVIRONMENT` setting controls logging format (development/production)
- **Queue Configuration**: Separate configuration for publishing and consuming queues
- **Authentication**: Optional username/password authentication support

### Monitoring & Observability
- **Structured Logging**: All events and errors logged with contextual metadata
- **Message Logging**: Incoming messages are logged with routing key and metadata
- **Connection Monitoring**: Automatic health checks and reconnection logging
- **Consumer Status**: Real-time monitoring of consumer thread status