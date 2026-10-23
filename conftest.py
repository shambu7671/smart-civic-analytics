"""
conftest.py — adds the project root to sys.path so that pytest can import
the `app` package regardless of the working directory.
"""
import sys
import os

# Ensure the project root (this file's directory) is on sys.path
sys.path.insert(0, os.path.dirname(__file__))
