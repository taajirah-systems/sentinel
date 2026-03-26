import unicodedata
import re
import binascii

class Normalizer:
    """
    Sentinel Layer 1: Normalization Engine.
    Decodes obfuscated inputs to prepare them for policy enforcement.
    """
    def normalize(self, text: str) -> str:
        if not text:
            return ""
            
        # 1. Unicode Normalization (NFKC) handles homoglyphs and compatibility forms
        normalized = unicodedata.normalize('NFKC', text)
        
        # 2. Hex/Octal/Unicode Escape Decoding
        # We try to find patterns like \xHH, \uHHHH, or \OOO
        try:
            # Handle \xHH
            normalized = re.sub(r'\\x([0-9a-fA-F]{2})', lambda m: chr(int(m.group(1), 16)), normalized)
            # Handle \uHHHH
            normalized = re.sub(r'\\u([0-9a-fA-F]{4})', lambda m: chr(int(m.group(1), 16)), normalized)
        except Exception:
            pass # Fallback to original if decoding fails
            
        # 3. Flatten Whitespace
        normalized = re.sub(r'\s+', ' ', normalized).strip()
        
        return normalized

# Default instance
normalizer = Normalizer()
