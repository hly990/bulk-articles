#!/usr/bin/env python
"""
Run YT-Article Craft model tests

This script imports and runs the model tests to verify functionality.
"""

import sys
import os
from pathlib import Path

# Add parent directory to Python path for imports
current_dir = Path(__file__).parent
parent_dir = current_dir.parent
sys.path.insert(0, str(parent_dir))

# Import test module
from src.models.test_models import main as run_tests

# Run the tests
if __name__ == "__main__":
    print("Running YT-Article Craft model tests...")
    run_tests()
    print("\nTests finished.") 