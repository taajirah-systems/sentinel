"""
Sovereign Scrub: Pipeline Orchestrator
Executes the three stages (Redact, Minify, Obfuscate) against arbitrary text payloads.
"""

from .redactor import apply_redaction
from .minifier import apply_minification
from .obfuscator import apply_obfuscation

def scrub_payload(text: str) -> tuple[str, dict]:
    """
    Passes a payload string through the complete Sovereign Scrub pipeline.
    
    Returns:
        (clean_text, metrics_dictionary)
    """
    if not text:
        return text, {}
        
    original_len = len(text)
    
    # Stage 1: Redaction (High confidence masking)
    stage1_text, redactions = apply_redaction(text)
    
    # Stage 2: Minification (Token trimming)
    stage2_text = apply_minification(stage1_text)
    
    # Stage 3: Obfuscation (Masking IP)
    final_text, obfuscations = apply_obfuscation(stage2_text)
    
    # Calculate token equivalence heuristic (1 token ~ 4 characters)
    final_len = len(final_text)
    chars_saved = original_len - final_len
    tokens_saved = chars_saved // 4
    
    metrics = {
        "redactions_applied": redactions,
        "obfuscations_applied": obfuscations,
        "bytes_in": original_len,
        "bytes_out": final_len,
        "estimated_tokens_saved": tokens_saved if tokens_saved > 0 else 0
    }
    
    return final_text, metrics
