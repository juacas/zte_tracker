"""Test runner for development environment."""
import pytest
import sys
import os

# Add the custom_components directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'custom_components'))

if __name__ == "__main__":
    # Run tests with verbose output
    pytest.main([
        "-v",
        "--tb=short", 
        "tests/",
        "../custom_components/zte_tracker/tests/",
        "../custom_components/zte_tracker/zteclient/tests/"
    ])