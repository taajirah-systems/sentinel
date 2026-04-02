"""
Sentinel Hierarchy Validator — Enforcing strict budget ownership rules.
"""

from typing import Optional, Literal

WalletType = Literal["org", "project", "agent", "contractor", "treasury", "system"]

# Allowed relationships: child_type -> parent_type
HIERARCHY_RULES = {
    "project": ["org"],
    "agent": ["project"],
    "contractor": [],
    "treasury": [],
    "system": [],
    "org": [] # Org is the root
}

def validate_hierarchy_link(child_type: WalletType, parent_type: Optional[WalletType]) -> bool:
    """
    Validates if a child wallet of a certain type can be linked to a parent of a certain type.
    """
    if parent_type is None:
        # Some types are allowed to be roots
        return child_type in ["org", "contractor", "treasury", "system"]
    
    allowed_parents = HIERARCHY_RULES.get(child_type, [])
    return parent_type in allowed_parents

def get_required_parent_type(child_type: WalletType) -> Optional[WalletType]:
    """
    Returns the required parent type for a given child type.
    """
    if child_type == "project": return "org"
    if child_type == "agent": return "project"
    return None
