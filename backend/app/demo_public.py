"""Lock public evaluation deployments: disable admin seed accounts and rotate passwords."""

from __future__ import annotations

import os
import secrets

from sqlalchemy.orm import Session

from .auth_utils import hash_password
from .db import SessionLocal
from .models import User
from .seed_demo import SEED_FILE, _load_seed_file

_ADMIN_ROLES = frozenset({"DBA", "Analyst"})


def demo_public_mode_enabled() -> bool:
    return os.getenv("DEMO_PUBLIC_MODE", "").lower() in ("1", "true", "yes")


def lock_public_demo(*, db: Session | None = None) -> dict[str, str]:
    """Disable DBA/Analyst seed users and rotate all seed passwords away from published defaults."""
    owns_session = db is None
    session = db if db is not None else SessionLocal()
    results: dict[str, str] = {}
    try:
        data = _load_seed_file()
        for user_def in data.get("users", []):
            email = user_def["email"]
            role = user_def["role"]
            user = session.query(User).filter(User.email == email.lower()).first()
            if user is None:
                results[email] = "skipped (user not found)"
                continue

            env_key = user_def.get("password_env", "")
            env_password = os.getenv(env_key, "").strip() if env_key else ""

            if role in _ADMIN_ROLES:
                user.is_active = False
                user.hashed_password = hash_password(env_password or secrets.token_urlsafe(24))
                results[email] = "disabled; password rotated"
                session.add(user)
                continue

            if role == "Viewer" and env_password:
                user.is_active = True
                user.hashed_password = hash_password(env_password)
                results[email] = f"active; password from {env_key}"
                session.add(user)
                continue

            user.is_active = False
            user.hashed_password = hash_password(secrets.token_urlsafe(24))
            results[email] = "disabled; set SEED_VIEWER_PASSWORD to enable read-only demo"
            session.add(user)

        session.commit()
        return results
    except Exception:
        session.rollback()
        raise
    finally:
        if owns_session:
            session.close()


def print_lock_summary(results: dict[str, str]) -> None:
    print("Public demo lock complete:")
    for email, status in results.items():
        print(f"  {email}: {status}")
    print(f"Seed source: {SEED_FILE}")
    if demo_public_mode_enabled():
        print("DEMO_PUBLIC_MODE is enabled — admin bootstrap remains blocked while seed users exist.")
