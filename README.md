# News-Powered Trading System

A real-time news monitoring and trading signal generation system that connects to Twitter/X feeds via WebSocket to capture market-relevant tweets for sentiment analysis and automated trading decisions.

## Features

- **Real-time Twitter Stream Processing**: WebSocket connection to third party API streaming Tweets in real time based on filters
- **Event-driven Architecture**: Handles `connected`, `ping`, and `tweet` events in real-time  
- **Automatic Reconnection**: Robust error handling with exponential backoff
- **Latency Monitoring**: Tracks timestamp differences for performance analysis
- **Structured Logging**: JSON-formatted logs with level separation
- **Comprehensive Testing**: 92% test coverage with 32 unit tests

## Technology Stack

- **Python 3.12** - Modern Python with type hints
- **UV** - Fast Python package manager
- **WebSocket Client** - Real-time Twitter API connections
- **Structlog** - Structured JSON logging
- **Pytest** - Comprehensive test suite

## Quick Start

### Prerequisites

- Python 3.12+
- UV package manager
- Twitter API key

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
# Edit .env and add your TWITTERAPI_KEY
```

4. Run the application:
```bash
uv run main.py
```

## Configuration

Create a `.env` file with the following variables:

```env
TWITTERAPI_KEY=your_twitter_api_key_here
ENVIRONMENT=development  # or 'production' for JSON logs
```

## Usage

The application automatically connects to Twitter's WebSocket stream and processes incoming tweets. All events are logged with structured data for analysis.

### Development Commands

```bash
# Run the application
uv run main.py

# Install new dependencies
uv add <package-name>

# Run all tests
uv run pytest test_websocket_manager.py

# Run tests with coverage
uv run pytest test_websocket_manager.py --cov=websocket_manager --cov-report=term-missing

# Run specific test categories
uv run pytest tests/test_initialization.py
uv run pytest tests/test_signal_handler.py
```

## Architecture

### Single-File Design
The application uses a single-file architecture (`main.py`) with:

- **WebSocketManager**: Core connection and event handling
- **Event Processors**: Handle different message types
- **Error Recovery**: Automatic reconnection with backoff
- **Signal Handlers**: Graceful shutdown on interrupts

## Testing

Comprehensive test suite with 32 tests across 6 categories:

```bash
# Run all tests
uv run pytest tests/

# Individual test modules
uv run pytest tests/test_initialization.py -v
uv run pytest tests/test_connection_management.py -v
uv run pytest tests/test_error_handling.py -v
```

### Test Coverage
- **92% Coverage** of core WebSocket functionality
- **Integration Tests**: End-to-end workflow validation
- **Error Handling**: Comprehensive exception scenarios
- **Connection Management**: Retry logic and lifecycle testing

## Logging

Structured logs are written to the `logs/` directory:

- `error.log` - ERROR level messages only
- `warning.log` - WARNING level and above  
- `app.log` - All application logs (INFO+)

Log rotation: 10MB files, 5 backups retained.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass: `uv run pytest`
5. Submit a pull request

## Support

For issues and questions, please open a GitHub issue.