# Unit Testing Plan for WebSocketManager

## Overview
Create comprehensive unit tests for the `WebSocketManager` class in `websocket_manager.py` to ensure robust testing coverage of WebSocket lifecycle management, error handling, and graceful shutdown functionality.

## Test File Structure
Create `test_websocket_manager.py` with the following test coverage:

### 1. **Initialization Tests**
- Test proper initialization with all callback functions
- Verify initial state values (shutdown_requested=False, current_ws=None)
- Test logger setup with correct class name

### 2. **Signal Handler Tests**
- Test signal handler sets shutdown_requested flag
- Test WebSocket closing when current_ws is active
- Test graceful handling when no active WebSocket exists
- Test error handling during WebSocket close operation

### 3. **Connection Management Tests**
- Test successful WebSocket connection establishment
- Test connection retry logic with 5-second delays
- Test graceful shutdown interrupting connection loop
- Test KeyboardInterrupt handling
- Test exception handling with proper logging

### 4. **WebSocket Lifecycle Tests**
- Mock WebSocketApp creation and run_forever calls
- Test callback function assignment to WebSocket instance
- Test ping_interval=30 and ping_timeout=20 parameters
- Test current_ws reference management

### 5. **Error Handling Tests**
- Test connection failures with retry mechanism
- Test shutdown flag checks during retry loops
- Test proper cleanup in finally blocks
- Test various exception scenarios

### 6. **Integration Tests**
- Test complete connection lifecycle with mocked WebSocket
- Test shutdown sequence from signal to connection termination

## Dependencies to Add
- Add `pytest` for test framework
- Add `pytest-mock` for mocking capabilities
- Add `unittest.mock` for built-in mocking (already available in Python 3.12)

## Implementation Approach
- Use pytest fixtures for common setup
- Mock `websocket.WebSocketApp` and related components
- Mock time.sleep for faster test execution
- Mock logging to verify proper log messages
- Use parameterized tests for different error scenarios

## Test Cases Detail

### Initialization Tests
```python
def test_websocket_manager_init():
    """Test WebSocketManager initialization with callback functions."""
    
def test_initial_state():
    """Test initial state values are set correctly."""
```

### Signal Handler Tests
```python
def test_signal_handler_sets_shutdown_flag():
    """Test signal handler sets shutdown_requested to True."""
    
def test_signal_handler_closes_active_websocket():
    """Test signal handler closes current WebSocket connection."""
    
def test_signal_handler_no_active_websocket():
    """Test signal handler when no active WebSocket exists."""
    
def test_signal_handler_websocket_close_error():
    """Test signal handler handles WebSocket close errors gracefully."""
```

### Connection Management Tests
```python
def test_connect_successful_connection():
    """Test successful WebSocket connection establishment."""
    
def test_connect_with_retry_logic():
    """Test connection retry after failures with 5-second delays."""
    
def test_connect_shutdown_interrupts_loop():
    """Test shutdown flag interrupts connection loop."""
    
def test_connect_keyboard_interrupt():
    """Test KeyboardInterrupt handling in connection loop."""
    
def test_connect_exception_handling():
    """Test general exception handling with proper logging."""
```

### WebSocket Lifecycle Tests
```python
def test_websocket_app_creation():
    """Test WebSocketApp is created with correct parameters."""
    
def test_callback_assignment():
    """Test callback functions are properly assigned to WebSocket."""
    
def test_ping_parameters():
    """Test ping_interval and ping_timeout are set correctly."""
    
def test_current_ws_reference_management():
    """Test current_ws is properly set and cleared."""
```

### Error Handling Tests
```python
def test_connection_failure_retry():
    """Test connection failures trigger retry mechanism."""
    
def test_shutdown_check_during_retry():
    """Test shutdown flag is checked during retry sleep periods."""
    
def test_finally_block_cleanup():
    """Test current_ws is cleared in finally block."""
    
def test_various_exception_scenarios():
    """Test handling of different exception types."""
```

### Integration Tests
```python
def test_complete_lifecycle():
    """Test complete connection lifecycle with mocked WebSocket."""
    
def test_shutdown_sequence():
    """Test complete shutdown sequence from signal to termination."""
```

## Mock Strategy

### WebSocket Mocking
```python
@pytest.fixture
def mock_websocket_app(mocker):
    """Mock WebSocketApp for testing."""
    return mocker.patch('websocket_manager.websocket.WebSocketApp')
```

### Time Mocking
```python
@pytest.fixture
def mock_time_sleep(mocker):
    """Mock time.sleep for faster test execution."""
    return mocker.patch('websocket_manager.time.sleep')
```

### Logger Mocking
```python
@pytest.fixture
def mock_logger(mocker):
    """Mock logger for verifying log messages."""
    return mocker.patch('websocket_manager.get_logger')
```

## Expected Test Coverage
- **Lines**: >95% coverage of websocket_manager.py
- **Branches**: >90% coverage of conditional logic
- **Functions**: 100% coverage of public methods
- **Edge Cases**: Comprehensive coverage of error scenarios

## Running Tests
```bash
# Install test dependencies
uv add pytest pytest-mock

# Run tests with coverage
pytest test_websocket_manager.py -v --cov=websocket_manager

# Run tests with coverage report
pytest test_websocket_manager.py --cov=websocket_manager --cov-report=html
```