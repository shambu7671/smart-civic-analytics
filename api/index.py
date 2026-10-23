"""
Vercel Serverless Function Entrypoint
====================================
Exports the WSGI app for Vercel's Python runtime.
"""
import sys
import os
from pathlib import Path

# Ensure project root is in sys.path
root_dir = str(Path(__file__).resolve().parent.parent)
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from wsgi import app
