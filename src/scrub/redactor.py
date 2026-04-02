"""
Sovereign Scrub: Redactor Module
Strips Personally Identifiable Information (PII), API keys, and internal IPs from payloads.
"""

import re

# High-confidence Regex patterns for sensitive data
REDACTION_PATTERNS = {
    "IPv4": r"\b(?:\d{1,3}\.){3}\d{1,3}\b",
    
    # Generic API Keys (e.g., sk-..., AIza...)
    "OPENAI_KEY": r"\bsk-[a-zA-Z0-9]{32,}\b",
    "GEMINI_KEY": r"\bAIza[0-9A-Za-z_-]{35}\b",
    
    # Email Addresses
    "EMAIL": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b",
    
    # SA Phone Numbers (+27 or 0)
    "ZA_PHONE": r"\+?27[0-9]{9}\b|0[0-9]{9}\b",
    
    # JWT Tokens (eyJ...)
    "JWT": r"eyJ[a-zA-Z0-9_-]+\.eyJ[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+",
    
    # SA ID Numbers (13 digits, approx format yyMMDD...)
    "SA_ID": r"\b\d{2}(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\d|3[01])\d{7}\b",
}

def apply_redaction(text: str) -> tuple[str, dict[str, int]]:
    """
    Scans the text for patterns and replaces them with <[TYPE]> placeholders.
    Returns the redacted string and a dictionary of redaction counts.
    """
    scrubbed = text
    stats = {k: 0 for k in REDACTION_PATTERNS.keys()}
    
    for key, pattern in REDACTION_PATTERNS.items():
        # Find all matches first to count them
        matches = re.findall(pattern, scrubbed)
        if matches:
            stats[key] += len(matches)
            # Replace all matches with the placeholder
            scrubbed = re.sub(pattern, f"<REDACTED_{key}>", scrubbed)
            
    # Filter out empty stats
    stats = {k: v for k, v in stats.items() if v > 0}
    
    return scrubbed, stats
