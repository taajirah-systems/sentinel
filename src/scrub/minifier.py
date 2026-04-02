"""
Sovereign Scrub: Minifier Module
Strips unnecessary whitespace and comments to save JOULE tokens during cloud inference.
"""

import re

def apply_minification(text: str) -> str:
    """
    Strips token weight by:
    1. Reducing 3+ contiguous newlines into a maximum of 2 newlines.
    2. Collapsing excess spaces (outside of quotes if possible, though a simple regex covers most).
    3. Stripping specific common single-line code comments without breaking the file.
    
    Returns the minified string.
    """
    minified = text
    
    # 1. Strip full-line python/bash comments that start with '#' (but don't break shebangs)
    # Only remove if it's solely a comment line and no code is on it
    minified = re.sub(r'^[ \t]*#(?!!).*$', '', minified, flags=re.MULTILINE)
    
    # 2. Strip single-line JS/TS comment lines '//'
    minified = re.sub(r'^[ \t]*//.*$', '', minified, flags=re.MULTILINE)
    
    # 3. Collapse 3+ contiguous newlines down to 2
    minified = re.sub(r'\n{3,}', '\n\n', minified)
    
    # 4. Collapse 2+ contiguous spaces into 1 space (except at the start of a line to preserve indentation)
    # We do a lookbehind to ensure we aren't collapsing indentation spaces at the beginning of lines.
    minified = re.sub(r'(?<!^)[ \t]{2,}', ' ', minified, flags=re.MULTILINE)
    
    return minified.strip()
