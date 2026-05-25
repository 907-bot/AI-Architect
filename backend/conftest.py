"""
Root conftest — adds repo root to sys.path so that
`from backend.xxx import yyy` works when pytest runs from backend/.
"""
import sys
import os

# Insert the repo root (parent of backend/) into sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
