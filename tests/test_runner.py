"""Test runner for development environment."""
import pytest
import sys
import os

# Add the repo root to the Python path so "custom_components...." imports resolve.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

if __name__ == "__main__":
    # Run tests with verbose output. All suites now live under tests/.
    pytest.main([
        "-v",
        "--tb=short",
        os.path.dirname(__file__),
    ])