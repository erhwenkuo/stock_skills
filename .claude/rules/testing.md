---
paths:
  - "tests/**/*.py"
  - "tests/conftest.py"
  - "tests/fixtures/**"
---

# Test Development Rules

## Running Tests

```bash
python3 -m pytest tests/ -q                       # Run all tests (~1191 tests, ~1 second)
python3 -m pytest tests/core/test_indicators.py -v # Specific module
python3 -m pytest tests/ -k "test_value_score"     # Keyword filter
```

## Test Structure

- `tests/core/` — Unit tests for core logic
- `tests/data/` — Tests for the data retrieval layer
- `tests/output/` — Tests for the formatter layer
- `tests/conftest.py` — Shared fixtures
- `tests/fixtures/` — JSON/CSV test data (Toyota 7203.T based)

## Mocking

- `mock_yahoo_client` fixture: Mocks yahoo_client module functions via monkeypatch
- Set `return_value` before use
- yahoo_client uses module functions (not classes), making monkeypatch straightforward

## Test Writing Guidelines

- Each test must be independently runnable (no external API dependencies)
- Always mock yahoo_client calls
- Reuse existing data from `tests/fixtures/`
- Create a corresponding test file for each new module
