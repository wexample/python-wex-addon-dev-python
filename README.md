# wexample-wex-addon-dev-python

Version: 0.0.64

Python dev addon for wex

## Table of Contents

- [Status Compatibility](#status-compatibility)
- [Tests](#tests)
- [Roadmap](#roadmap)
- [Useful Links](#useful-links)


## Status & Compatibility

**Maturity**: Production-ready

**Python Support**: >=3.10

**OS Support**: Linux, macOS, Windows

**Status**: Actively maintained

## Tests

This project uses `pytest` for testing and `pytest-cov` for code coverage analysis.

### Installation

First, install the required testing dependencies:
```bash
.venv/bin/python -m pip install pytest pytest-cov
```

### Basic Usage

Run all tests with coverage:
```bash
.venv/bin/python -m pytest --cov --cov-report=html
```

### Common Commands
```bash
# Run tests with coverage for a specific module
.venv/bin/python -m pytest --cov=your_module

# Show which lines are not covered
.venv/bin/python -m pytest --cov=your_module --cov-report=term-missing

# Generate an HTML coverage report
.venv/bin/python -m pytest --cov=your_module --cov-report=html

# Combine terminal and HTML reports
.venv/bin/python -m pytest --cov=your_module --cov-report=term-missing --cov-report=html

# Run specific test file with coverage
.venv/bin/python -m pytest tests/test_file.py --cov=your_module --cov-report=term-missing
```

### Viewing HTML Reports

After generating an HTML report, open `htmlcov/index.html` in your browser to view detailed line-by-line coverage information.

### Coverage Threshold

To enforce a minimum coverage percentage:
```bash
.venv/bin/python -m pytest --cov=your_module --cov-fail-under=80
```

This will cause the test suite to fail if coverage drops below 80%.

## Known Limitations & Roadmap

Current limitations and planned features are tracked in the GitHub issues.

See the [project roadmap](https://github.com/wexample/python-wex_addon_dev_python/issues) for upcoming features and improvements.

## Useful Links

- **Homepage**: https://github.com/wexample/python-wex-addon-dev-python
- **Documentation**: [docs.wexample.com](https://docs.wexample.com)
- **Issue Tracker**: https://github.com/wexample/python-wex-addon-dev-python/issues
- **Discussions**: https://github.com/wexample/python-wex-addon-dev-python/discussions
- **PyPI**: [pypi.org/project/wexample-wex-addon-dev-python](https://pypi.org/project/wexample-wex-addon-dev-python/)

