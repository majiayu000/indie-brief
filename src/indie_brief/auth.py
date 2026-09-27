from __future__ import annotations

import hmac


def presented_token(header: str | None) -> str | None:
    if header is None:
        return None
    scheme, _, token = header.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        return None
    return token.strip()


def authorized(token: str | None, keys: set[str]) -> bool:
    if token is None or not keys:
        return False
    token_bytes = token.encode()
    matched = False
    for key in keys:
        matched = hmac.compare_digest(token_bytes, key.encode()) or matched
    return matched
