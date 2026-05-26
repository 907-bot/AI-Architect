"""
Ensure repo root is in sys.path for all tests.
"""
import sys
import os

# Repo root = 2 levels up from backend/tests/
repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)
