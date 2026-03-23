from __future__ import annotations

from uuid import uuid4


def generate_message_id(prefix: str = "message") -> str:
    return f"{prefix}-{uuid4().hex[:12]}"



def generate_entity_id(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex[:12]}"
