"""
Sovereign Scrub: Obfuscator Module
Obfuscates internal IP / project names into generic ones before leaving the machine.
"""

import re

# Dictionary mapping proprietary institutional IP names to generic equivalents.
OBFUSCATION_MAP = {
    # Project Names
    r"\bSentinel\b": "Project_Alpha",
    r"\bNemoClaw\b": "Project_Beta",
    r"\bOpenClaw\b": "Agent_Runtime",
    
    # Internal component terms
    r"\bSovereign Scrub\b": "DLP_Middleware",
    r"\bDirty Sandbox\b": "Execution_Environment",
    
    # Can extend with specific trading algorithms, variable names, database column names
}

def apply_obfuscation(text: str) -> tuple[str, dict[str, int]]:
    """
    Scans the text for proprietary terms and replaces them with generic names.
    Returns the obfuscated string and a dictionary of replacement counts.
    """
    obfuscated = text
    stats = {}
    
    for pattern, generic_name in OBFUSCATION_MAP.items():
        matches = len(re.findall(pattern, obfuscated, flags=re.IGNORECASE))
        if matches > 0:
            stats[generic_name] = matches
            obfuscated = re.sub(pattern, generic_name, obfuscated, flags=re.IGNORECASE)
            
    return obfuscated, stats
