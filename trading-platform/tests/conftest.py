import pytest
import sys
from pathlib import Path

# Add the parent directory to the path so we can import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

@pytest.fixture(autouse=True)
def reset_singletons():
    """Reset any singleton instances between tests"""
    yield
    # Add cleanup code here if needed