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

## Development Commands

```bash
# Run the application
python main.py

# Install dependencies
uv sync

# Add new dependencies
uv add <package-name>
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