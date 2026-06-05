"""Mock auth store — JSON persistence under LI_DATA_DIR (MVP until lidb users DDL)."""

from __future__ import annotations

import json
import os
import re
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from .crypto_util import generate_api_token, hash_api_token, hash_password, verify_password
from .errors import AuthError
from .jwt_util import encode_jwt

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
VALID_SCOPES = frozenset({"publish", "yank", "publish+yank"})


@dataclass
class UserRecord:
    id: str
    email: str
    password_hash: str
    publisher_id: str
    created_at: str


@dataclass
class PublisherRecord:
    id: str
    name: str
    public_key_hex: str
    created_at: str


@dataclass
class ApiTokenRecord:
    id: str
    token_hash: str
    publisher_id: str
    scope: str
    name: str | None
    expires_at: str | None
    created_at: str
    revoked_at: str | None = None


@dataclass
class MockAuthStore:
    data_dir: Path
    users: dict[str, UserRecord] = field(default_factory=dict)
    users_by_email: dict[str, str] = field(default_factory=dict)
    publishers: dict[str, PublisherRecord] = field(default_factory=dict)
    api_tokens: dict[str, ApiTokenRecord] = field(default_factory=dict)
    token_hash_index: dict[str, str] = field(default_factory=dict)

    @classmethod
    def open(cls, data_dir: str | Path | None = None) -> MockAuthStore:
        root = Path(data_dir or os.environ.get("LI_DATA_DIR", Path.home() / ".local/share/lis/data"))
        store = cls(data_dir=root)
        store._load()
        return store

    def _db_path(self) -> Path:
        return self.data_dir / "auth-mock.json"

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def _load(self) -> None:
        path = self._db_path()
        if not path.is_file():
            return
        raw = json.loads(path.read_text(encoding="utf-8"))
        for row in raw.get("users", []):
            user = UserRecord(**row)
            self.users[user.id] = user
            self.users_by_email[user.email.lower()] = user.id
        for row in raw.get("publishers", []):
            pub = PublisherRecord(**row)
            self.publishers[pub.id] = pub
        for row in raw.get("api_tokens", []):
            tok = ApiTokenRecord(**row)
            self.api_tokens[tok.id] = tok
            if tok.revoked_at is None:
                self.token_hash_index[tok.token_hash] = tok.id

    def _save(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        payload = {
            "users": [asdict(u) for u in self.users.values()],
            "publishers": [asdict(p) for p in self.publishers.values()],
            "api_tokens": [asdict(t) for t in self.api_tokens.values()],
        }
        self._db_path().write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    def signup(self, email: str, password: str, *, publisher_name: str | None = None) -> dict[str, Any]:
        email = email.strip().lower()
        if not EMAIL_RE.match(email):
            raise AuthError("bad_request", "invalid email", status=400)
        if len(password) < 8:
            raise AuthError("bad_request", "password must be at least 8 characters", status=400)
        if email in self.users_by_email:
            raise AuthError("conflict", "email already registered", status=409)

        now = self._now()
        pub_id = str(uuid.uuid4())
        user_id = str(uuid.uuid4())
        pub_name = (publisher_name or email.split("@")[0]).strip().lower()
        if not pub_name:
            pub_name = f"pub-{user_id[:8]}"
        if pub_name in {p.name for p in self.publishers.values()}:
            pub_name = f"{pub_name}-{user_id[:8]}"

        publisher = PublisherRecord(
            id=pub_id,
            name=pub_name,
            public_key_hex="00" * 32,
            created_at=now,
        )
        user = UserRecord(
            id=user_id,
            email=email,
            password_hash=hash_password(password),
            publisher_id=pub_id,
            created_at=now,
        )
        self.publishers[pub_id] = publisher
        self.users[user_id] = user
        self.users_by_email[email] = user_id
        self._save()
        return self._session_response(user)

    def login(self, email: str, password: str) -> dict[str, Any]:
        email = email.strip().lower()
        user_id = self.users_by_email.get(email)
        if not user_id:
            raise AuthError("unauthorized", "invalid email or password", status=401)
        user = self.users[user_id]
        if not verify_password(password, user.password_hash):
            raise AuthError("unauthorized", "invalid email or password", status=401)
        return self._session_response(user)

    def _session_response(self, user: UserRecord) -> dict[str, Any]:
        access_token = encode_jwt(
            {
                "sub": user.id,
                "role": "authenticated",
                "publisher_id": user.publisher_id,
                "typ": "session",
            },
            ttl_seconds=3600,
        )
        pub = self.publishers.get(user.publisher_id)
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": 3600,
            "user": {
                "id": user.id,
                "email": user.email,
                "publisher_id": user.publisher_id,
                "publisher_name": pub.name if pub else None,
            },
        }

    def create_api_token(
        self,
        *,
        user_id: str,
        name: str | None = None,
        scope: str = "publish",
        expires_in: int | None = None,
    ) -> dict[str, Any]:
        user = self.users.get(user_id)
        if not user:
            raise AuthError("unauthorized", "unknown user", status=401)
        if scope not in VALID_SCOPES:
            raise AuthError("bad_request", f"scope must be one of {sorted(VALID_SCOPES)}", status=400)

        plain = generate_api_token()
        token_hash = hash_api_token(plain)
        now = self._now()
        tok_id = str(uuid.uuid4())
        expires_at: str | None = None
        if expires_in is not None and expires_in > 0:
            expires_at = (datetime.now(timezone.utc) + timedelta(seconds=expires_in)).isoformat()

        record = ApiTokenRecord(
            id=tok_id,
            token_hash=token_hash,
            publisher_id=user.publisher_id,
            scope=scope,
            name=name,
            expires_at=expires_at,
            created_at=now,
        )
        self.api_tokens[tok_id] = record
        self.token_hash_index[token_hash] = tok_id
        self._save()
        return {
            "id": tok_id,
            "token": plain,
            "scope": scope,
            "name": name,
            "publisher_id": user.publisher_id,
            "expires_at": expires_at,
            "created_at": now,
        }

    def list_api_tokens(self, *, user_id: str) -> dict[str, Any]:
        user = self.users.get(user_id)
        if not user:
            raise AuthError("unauthorized", "unknown user", status=401)
        tokens = []
        for tok in self.api_tokens.values():
            if tok.publisher_id != user.publisher_id or tok.revoked_at is not None:
                continue
            if tok.expires_at:
                try:
                    exp = datetime.fromisoformat(tok.expires_at)
                    if exp.tzinfo is None:
                        exp = exp.replace(tzinfo=timezone.utc)
                    if exp < datetime.now(timezone.utc):
                        continue
                except ValueError:
                    pass
            tokens.append(
                {
                    "id": tok.id,
                    "scope": tok.scope,
                    "name": tok.name,
                    "publisher_id": tok.publisher_id,
                    "expires_at": tok.expires_at,
                    "created_at": tok.created_at,
                }
            )
        tokens.sort(key=lambda t: t["created_at"], reverse=True)
        return {"tokens": tokens, "total": len(tokens)}

    def revoke_api_token(self, *, user_id: str, token_id: str) -> dict[str, Any]:
        user = self.users.get(user_id)
        if not user:
            raise AuthError("unauthorized", "unknown user", status=401)
        tok = self.api_tokens.get(token_id)
        if not tok or tok.publisher_id != user.publisher_id:
            raise AuthError("not_found", "token not found", status=404)
        if tok.revoked_at:
            raise AuthError("conflict", "token already revoked", status=409)
        now = self._now()
        tok.revoked_at = now
        self.token_hash_index.pop(tok.token_hash, None)
        self._save()
        return {"id": token_id, "revoked_at": now}

    def resolve_bearer_token(self, token: str) -> dict[str, Any] | None:
        """Return publisher context for registry publish if token is valid."""
        dev = os.environ.get("LI_REGISTRY_DEV_TOKEN", "").strip()
        if dev and token == dev:
            return {"publisher_id": "dev", "scope": "publish+yank", "source": "dev_token"}

        token_hash = hash_api_token(token)
        tok_id = self.token_hash_index.get(token_hash)
        if tok_id:
            tok = self.api_tokens.get(tok_id)
            if tok and tok.revoked_at is None:
                if tok.expires_at:
                    try:
                        exp = datetime.fromisoformat(tok.expires_at)
                        if exp.tzinfo is None:
                            exp = exp.replace(tzinfo=timezone.utc)
                        if exp < datetime.now(timezone.utc):
                            return None
                    except ValueError:
                        pass
                return {
                    "publisher_id": tok.publisher_id,
                    "scope": tok.scope,
                    "source": "api_token",
                    "token_id": tok.id,
                }
        return None


_store: MockAuthStore | None = None


def get_auth_store() -> MockAuthStore:
    global _store
    if _store is None:
        _store = MockAuthStore.open()
    return _store


def reset_auth_store() -> None:
    global _store
    _store = None
