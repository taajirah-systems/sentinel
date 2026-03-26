import json
import base64
import os
import time
import hmac
import hashlib
from typing import Any, Dict, Optional

class InferenceBroker:
    """
    Sentinel Layer 4: Hardened Inference Broker.
    Handles host-side key custody, request signing, and structured response shaping.
    """
    def __init__(self, secret_key: Optional[str] = None):
        # The secret key used for internal request signing (HMAC)
        # Should be distinct from provider API keys.
        self.secret_key = secret_key or os.getenv("SENTINEL_INTERNAL_SECRET", "sentinel-internal-dev-secret")

    def sign_request(self, payload_str: str) -> str:
        """Generates an HMAC signature for internal validation."""
        return hmac.new(
            self.secret_key.encode(),
            payload_str.encode(),
            hashlib.sha256
        ).hexdigest()

    def verify_signature(self, payload_str: str, signature: str) -> bool:
        """Verifies if a request came from an authenticated Sentinel component."""
        expected = self.sign_request(payload_str)
        return hmac.compare_digest(expected, signature)

    def shape_response(self, provider_response: Dict[str, Any]) -> Dict[str, Any]:
        """ Standardizes provider responses into a rigid internal format. """
        # This prevents the agent from seeing raw provider metadata/errors
        # and ensures downstream components get a consistent object.
        choices = provider_response.get("choices", [])
        if not choices:
            return {"error": "No completion provided by upstream"}
            
        return {
            "id": provider_response.get("id"),
            "model": provider_response.get("model"),
            "content": choices[0].get("message", {}).get("content", ""),
            "finish_reason": choices[0].get("finish_reason"),
            "usage": provider_response.get("usage", {})
        }

# Default instance
inference_broker = InferenceBroker()
