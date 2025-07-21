"""
Main test suite entry point for WebSocketManager.

This file imports all test modules to provide a centralized test runner.
Individual test classes are organized in the tests/ directory:

- tests/test_initialization.py - Initialization and setup tests
- tests/test_signal_handler.py - Signal handler functionality tests

Run all tests (main entry point):
    pytest test_websocket_manager.py

Run all tests (from tests directory):
    pytest tests/

Run specific test modules:
    pytest tests/test_initialization.py
    pytest tests/test_signal_handler.py

Run with coverage:
    pytest test_websocket_manager.py --cov=websocket_manager --cov-report=term-missing
"""

# Import all test classes to make them discoverable by pytest
from tests.test_initialization import TestWebSocketManagerInitialization
from tests.test_signal_handler import TestWebSocketManagerSignalHandler

__all__ = [
    'TestWebSocketManagerInitialization',
    'TestWebSocketManagerSignalHandler',
]