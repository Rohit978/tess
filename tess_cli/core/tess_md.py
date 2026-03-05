"""
TESS.md Context Loader
Reads project-specific instructions from TESS.md files (like CLAUDE.md for Claude Code).
"""

import os
from .logger import setup_logger

logger = setup_logger("TessMD")

TESS_MD_FILENAME = "TESS.md"


def find_tess_md(start_path):
    """
    Walk up from start_path to find a TESS.md file.
    Returns the absolute path if found, None otherwise.
    """
    current = os.path.abspath(start_path)
    
    # Safety: don't walk up more than 10 levels
    for _ in range(10):
        candidate = os.path.join(current, TESS_MD_FILENAME)
        if os.path.isfile(candidate):
            logger.info(f"Found TESS.md at {candidate}")
            return candidate
        
        parent = os.path.dirname(current)
        if parent == current:
            break  # Reached filesystem root
        current = parent
    
    return None


def read_tess_md(start_path):
    """
    Find and read TESS.md content from the project root.
    Returns the content string or empty string if not found.
    """
    path = find_tess_md(start_path)
    if not path:
        return ""
    
    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read().strip()
        logger.info(f"Loaded TESS.md ({len(content)} chars)")
        return content
    except Exception as e:
        logger.error(f"Error reading TESS.md: {e}")
        return ""
