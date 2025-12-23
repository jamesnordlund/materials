"""Pytest configuration for mcp_materials tests."""

import sys
from pathlib import Path

# Add src directory to path for test imports
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))
