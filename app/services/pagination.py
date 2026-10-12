"""
Opaque, signed cursor pagination for Firestore queries.
Minimizes read bandwidth by fetching strictly 12 items per page with signed tokens.
"""

import json
import base64
import hmac
import hashlib
from typing import Any, Optional


def create_cursor_token(doc_id: str, sort_field: str, sort_value: Any, secret_key: str) -> str:
    """
    Creates an opaque, HMAC-signed cursor token for Firestore pagination.
    Payload contains doc ID, sorting field name, and sorting value.
    """
    payload = {
        "id": doc_id,
        "field": sort_field,
        "val": sort_value,
    }
    json_bytes = json.dumps(payload, separators=(',', ':'), sort_keys=True).encode("utf-8")
    b64_payload = base64.urlsafe_b64encode(json_bytes).decode("ascii")

    # Generate HMAC signature
    signature = hmac.new(
        secret_key.encode("utf-8"),
        b64_payload.encode("utf-8"),
        hashlib.sha256
    ).digest()
    b64_sig = base64.urlsafe_b64encode(signature).decode("ascii").rstrip("=")

    return f"{b64_payload}.{b64_sig}"


def parse_cursor_token(token: Optional[str], secret_key: str) -> Optional[dict[str, Any]]:
    """
    Validates and decodes a signed cursor token.
    Returns payload dictionary or None if tampered or invalid.
    """
    if not token or "." not in token:
        return None

    try:
        b64_payload, b64_sig = token.rsplit(".", 1)

        # Pad signature if needed
        padding = 4 - (len(b64_sig) % 4)
        if padding < 4:
            b64_sig += "=" * padding

        expected_sig = hmac.new(
            secret_key.encode("utf-8"),
            b64_payload.encode("utf-8"),
            hashlib.sha256
        ).digest()

        actual_sig = base64.urlsafe_b64decode(b64_sig)
        if not hmac.compare_digest(expected_sig, actual_sig):
            return None

        # Decode payload
        json_bytes = base64.urlsafe_b64decode(b64_payload)
        return json.loads(json_bytes.decode("utf-8"))
    except Exception:
        return None
