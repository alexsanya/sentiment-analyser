# Agent Integration Tests

This directory contains integration tests for PydanticAI agents that make real API calls to OpenAI.

## Overview

The integration tests validate the behavior of three agents:
- **TextSearchAgent**: Analyzes text content for token announcements
- **ImageSearchAgent**: Analyzes images for token announcements  
- **FirecrawlAgent**: Scrapes web content for token announcements

## Test Data

Test cases are extracted from `examples/sentiment-analyze.ipynb`:
- **11 text samples** covering various scenarios (token releases, purchases, no announcements)
- **3 image URLs** with different announcement types
- **2 web URLs** for scraping tests

## Prerequisites

### Required Environment Variables
```bash
export OPENAI_API_KEY="your-openai-api-key-here"
```

### Optional (for FirecrawlAgent tests)
- Firecrawl MCP server running at `http://localhost:3000/sse`

## Running Tests

### Basic Commands
```bash
# Run all integration tests (requires API key)
OPENAI_API_KEY=your_key uv run pytest tests/integration/ -v

# Run specific agent tests
uv run pytest tests/integration/test_agents_integration.py::TestTextSearchAgent -v
uv run pytest tests/integration/test_agents_integration.py::TestImageSearchAgent -v
uv run pytest tests/integration/test_agents_integration.py::TestFirecrawlAgent -v

# Run individual test for debugging
uv run pytest tests/integration/test_agents_integration.py::TestIndividualTextCases::test_polygon_explicit_chain_evm_address -v
```

### Snapshot Management
```bash
# Generate initial snapshots (first run)
uv run pytest tests/integration/ --snapshot-update

# Update snapshots when agent behavior changes
uv run pytest tests/integration/ --snapshot-update

# View snapshot diffs
uv run pytest tests/integration/ -v
```

### Using Pytest Markers
```bash
# Run only integration tests
uv run pytest -m integration -v

# Skip integration tests (run only unit tests)
uv run pytest -m "not integration" -v
```

## Test Structure

### Snapshot Testing
- Uses **Syrupy** for JSON snapshot comparison
- Agent responses are serialized to JSON using `model_dump()`
- Snapshots stored in `__snapshots__/` directory
- Each test case has named snapshots for easy identification

### Test Organization
- **Parameterized tests**: Efficient execution of multiple similar cases
- **Individual test methods**: Easier debugging and snapshot management
- **Environment validation**: Ensures required API keys are available
- **Error handling tests**: Validates agent behavior with edge cases

### Expected Snapshot Format
```json
{
  "chain_id": 137,
  "chain_name": "Polygon", 
  "is_release": true,
  "chain_defined_explicitly": true,
  "definition_fragment": "My new token on Polygon blockchain:",
  "token_address": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"
}
```

## Test Cases Coverage

### TextSearchAgent (11 + 2 edge cases)
- Explicit chain detection (Polygon, Solana)
- Chain inference from address format (EVM → Ethereum, Solana)
- Release vs. purchase distinction
- No token scenarios
- Release announcements without details
- Empty input handling
- Very long input handling

### ImageSearchAgent (3 cases)
- Token announcement images (Trump, Melania)
- Non-announcement images
- OCR text extraction validation

### FirecrawlAgent (2 cases)
- Token website scraping
- Non-token website analysis
- Requires Firecrawl MCP server

## Troubleshooting

### Common Issues
1. **API Key Missing**: Set `OPENAI_API_KEY` environment variable
2. **Firecrawl Tests Failing**: Ensure Firecrawl MCP server is running
3. **Snapshot Mismatches**: Use `--snapshot-update` to refresh snapshots
4. **Rate Limiting**: OpenAI API has rate limits, run tests with delays if needed

### Test Debugging
```bash
# Run single test with verbose output
uv run pytest tests/integration/test_agents_integration.py::TestIndividualTextCases::test_polygon_explicit_chain_evm_address -v -s

# Show collected tests without running
uv run pytest tests/integration/ --collect-only

# Generate coverage report
uv run pytest tests/integration/ --cov=src.core.agents --cov-report=html
```