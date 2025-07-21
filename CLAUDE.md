# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a news-powered trading system that monitors Twitter/X feeds in real-time via WebSocket connections. The application connects to Twitter's streaming API to capture tweets and their metadata for sentiment analysis and trading signal generation.

## Technology Stack

- **Language**: Python 3.12
- **Package Manager**: UV (modern Python package manager)
- **Key Dependencies**: 
  - `websocket-client` for real-time Twitter API connections
  - `dotenv` for environment variable management
  - `structlog` for structured logging with JSON output
- **Testing**: 
  - `pytest` for unit testing framework
  - `pytest-mock` for mocking functionality
  - `pytest-cov` for coverage reporting

## Development Commands

```bash
# Run the application
python main.py

# Install dependencies
uv sync

# Add new dependencies
uv add <package-name>

# Run all tests
uv run pytest test_websocket_manager.py

# Run tests with coverage
uv run pytest test_websocket_manager.py --cov=websocket_manager --cov-report=term-missing

# Run specific test categories
uv run pytest tests/test_initialization.py
uv run pytest tests/test_signal_handler.py

# Run tests in verbose mode
uv run pytest tests/ -v
```

## Architecture

**Single-file application** (`main.py`) with event-driven WebSocket architecture:

- **WebSocket Client**: Connects to `wss://ws.twitterapi.io/twitter/tweet/websocket`
- **Event Handlers**: Processes `connected`, `ping`, and `tweet` events
- **Error Handling**: Comprehensive error handling with auto-reconnect functionality
- **Time Analysis**: Calculates timestamp differences for latency monitoring

## Configuration

- **`.env`**: Contains `TWITTERAPI_KEY` for Twitter API authentication and optional `ENVIRONMENT` setting
- **`pyproject.toml`**: Project configuration and dependencies
- **`.python-version`**: Enforces Python 3.12 requirement
- **`logging_config.py`**: Structured logging configuration with file separation by log level

## Key Components

- **Connection Management**: Automatic reconnection on failures with exponential backoff
- **Event Processing**: Real-time tweet data processing with metadata extraction
- **Structured Logging**: JSON-formatted logs separated by level (error.log, warning.log, app.log)
- **Time Tracking**: Monitors message latency and processing times

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
└── test_integration.py            # End-to-end integration tests (2 tests)

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

# Run specific test classes
uv run pytest tests/test_connection_management.py::TestConnectionManagement -v
uv run pytest tests/test_websocket_lifecycle.py::TestWebSocketLifecycle -v
uv run pytest tests/test_error_handling.py::TestErrorHandling -v
uv run pytest tests/test_integration.py::TestIntegration -v

# Run with coverage reporting
uv run pytest test_websocket_manager.py --cov=websocket_manager --cov-report=term-missing

# Run specific test class
uv run pytest test_websocket_manager.py::TestWebSocketManagerInitialization

# Generate HTML coverage report
uv run pytest test_websocket_manager.py --cov=websocket_manager --cov-report=html
```

### Test Coverage
- **Current Coverage**: 92% of websocket_manager.py (32/32 tests passing)
- **Tested Components**: WebSocketManager initialization, signal handling, connection management, WebSocket lifecycle, comprehensive error handling, and integration workflows
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

## Logging

- **Log Files**: Located in `logs/` directory with automatic rotation (10MB, 5 backups)
  - `error.log`: ERROR level messages only
  - `warning.log`: WARNING level and above
  - `app.log`: All log levels (INFO and above)
- **Environment**: Set `ENVIRONMENT=production` for JSON logs, `development` for console output
- **Format**: Structured logging with timestamps, context, and metadata

## Development Notes

- The application is designed for continuous operation
- Environment variables are required for API authentication
- WebSocket connection handles Twitter's real-time streaming protocol
- Error recovery includes connection retries and graceful degradation
- All events and errors are logged with structured data for analysis