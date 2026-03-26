import re
from typing import List

class Redactor:
    """
    Sentinel Layer 4: Inference Broker Redaction.
    Redacts sensitive patterns (API keys, tokens) from prompts and completions.
    """
    
    # Patterns for common secrets
    PATTERNS = [
        r'sk-[a-zA-Z0-9]{32,}', # OpenAI, OpenRouter
        r'xai-[a-zA-Z0-9]{40,}',
        r'nvapi-[a-zA-Z0-9]{40,}', # NVIDIA
        r'AIzaSy[a-zA-Z0-9_-]{33}', # Google API Key
        r'(?i)token[:=]\s*[a-zA-Z0-9_-]{16,}',
        r'(?i)key[:=]\s*[a-zA-Z0-9_-]{16,}',
        r'(?i)password[:=]\s*[a-zA-Z0-9_-]{16,}',
    ]
    
    def redact(self, text: str) -> str:
        if not text:
            return ""
            
        redacted = text
        for pattern in self.PATTERNS:
            redacted = re.sub(pattern, "[REDACTED]", redacted)
            
        return redacted

# Default instance
redactor = Redactor()
