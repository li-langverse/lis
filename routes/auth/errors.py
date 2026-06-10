"""Auth route errors."""

from __future__ import annotations

from typing import Any


class AuthError(Exception):
    def __init__(self, error: str, message: str, status: int = 400, **details: Any) -> None:
        super().__init__(message)
        self.error = error
        self.message = message
        self.status = status
        self.details = details
