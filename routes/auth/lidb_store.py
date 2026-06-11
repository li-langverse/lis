"""Auth store backed by lidb catalog.heap (Li-native durable persistence)."""

from __future__ import annotations

import os
from dataclasses import asdict
from pathlib import Path

from .lidb_snapshot import catalog_path, ensure_auth_schema, merge_auth_tables
from .mock_store import (
    ApiTokenRecord,
    DeviceCodeRecord,
    MockAuthStore,
    PublisherRecord,
    SignupTokenRecord,
    UserRecord,
)


class LidbAuthStore(MockAuthStore):
    """Same API as MockAuthStore; persists to LI_DATA_DIR/.lidb/catalog.heap."""

    @classmethod
    def open(cls, data_dir: str | Path | None = None) -> LidbAuthStore:
        root = Path(data_dir or os.environ.get("LI_DATA_DIR", Path.home() / ".local/share/lis/data"))
        ensure_auth_schema(root)
        store = cls(data_dir=root)
        store._load()
        return store

    def _db_path(self) -> Path:
        return catalog_path(self.data_dir)

    def _load(self) -> None:
        from .lidb_snapshot import load_catalog

        path = self._db_path()
        if not path.is_file():
            return
        raw = load_catalog(path)
        for row in raw.get("users", []):
            if not row.get("id"):
                continue
            user = UserRecord(
                id=row["id"],
                email=row["email"],
                password_hash=row["password_hash"],
                publisher_id=row["publisher_id"],
                created_at=row.get("created_at", ""),
            )
            self.users[user.id] = user
            self.users_by_email[user.email.lower()] = user.id
        for row in raw.get("publishers", []):
            if not row.get("id"):
                continue
            pub = PublisherRecord(
                id=row["id"],
                name=row["name"],
                public_key_hex=row.get("public_key") or row.get("public_key_hex") or ("00" * 32),
                created_at=row.get("created_at", ""),
            )
            self.publishers[pub.id] = pub
        for row in raw.get("api_tokens", []):
            if not row.get("id"):
                continue
            tok = ApiTokenRecord(
                id=row["id"],
                token_hash=row["token_hash"],
                publisher_id=row["publisher_id"],
                scope=row["scope"],
                name=row.get("name") or None,
                expires_at=row.get("expires_at") or None,
                created_at=row.get("created_at", ""),
                revoked_at=row.get("revoked_at") or None,
            )
            self.api_tokens[tok.id] = tok
            if tok.revoked_at is None:
                self.token_hash_index[tok.token_hash] = tok.id
        for row in raw.get("signup_tokens", []):
            if not row.get("id"):
                continue
            st = SignupTokenRecord(
                id=row["id"],
                token_hash=row["token_hash"],
                email_hint=row.get("email_hint") or None,
                max_uses=int(row.get("max_uses") or 1),
                uses=int(row.get("uses") or 0),
                expires_at=row.get("expires_at") or None,
                created_by=row.get("created_by") or None,
                created_at=row.get("created_at", ""),
            )
            self.signup_tokens[st.id] = st
            if st.uses < st.max_uses:
                self.signup_hash_index[st.token_hash] = st.id
        for row in raw.get("device_codes", []):
            if not row.get("id"):
                continue
            dc = DeviceCodeRecord(
                id=row["id"],
                device_code=row["device_code"],
                user_code=row["user_code"],
                status=row.get("status", "pending"),
                user_id=row.get("user_id") or None,
                session_token=row.get("session_token") or None,
                api_token=row.get("api_token") or None,
                expires_at=row.get("expires_at", ""),
                created_at=row.get("created_at", ""),
            )
            self.device_codes[dc.id] = dc
            if dc.status == "pending":
                self.device_by_user_code[dc.user_code.upper()] = dc.id

    def _save(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        merge_auth_tables(
            self._db_path(),
            users=[asdict(u) for u in self.users.values()],
            publishers=[
                {
                    "id": p.id,
                    "name": p.name,
                    "public_key": p.public_key_hex,
                    "created_at": p.created_at,
                }
                for p in self.publishers.values()
            ],
            api_tokens=[asdict(t) for t in self.api_tokens.values()],
            signup_tokens=[asdict(t) for t in self.signup_tokens.values()],
            device_codes=[asdict(d) for d in self.device_codes.values()],
        )


def import_mock_json(data_dir: str | Path, mock_path: Path) -> dict[str, int]:
    """One-shot import auth-mock.json into lidb catalog."""
    import json

    raw = json.loads(mock_path.read_text(encoding="utf-8"))
    root = Path(data_dir)
    ensure_auth_schema(root)
    merge_auth_tables(
        catalog_path(root),
        users=raw.get("users", []),
        publishers=[
            {
                "id": p["id"],
                "name": p["name"],
                "public_key": p.get("public_key_hex", "00" * 32),
                "created_at": p.get("created_at", ""),
            }
            for p in raw.get("publishers", [])
        ],
        api_tokens=raw.get("api_tokens", []),
        signup_tokens=raw.get("signup_tokens", []),
        device_codes=raw.get("device_codes", []),
    )
    return {
        "users": len(raw.get("users", [])),
        "api_tokens": len(raw.get("api_tokens", [])),
    }
