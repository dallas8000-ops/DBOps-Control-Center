"""Deployment-Stripe-center alignment: tier env, manifest, and readiness checks."""

from __future__ import annotations

import json
import logging
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .billing_plans import STRIPE_PRICE_ENV_BY_PLAN

logger = logging.getLogger(__name__)

AUTOMATION_CENTER_URL = "https://stripe-installer.gilliomfrontlinedigital.com"
_DB_URL_PREFIXES = ("postgres://", "postgresql://", "postgresql+")
_JWT_MIN_LEN = 32


@dataclass(frozen=True)
class ReadinessCheck:
    id: str
    category: str
    name: str
    status: str  # pass | warn | fail
    message: str
    fix: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _env_set(name: str) -> bool:
    return bool(os.getenv(name, "").strip())


def discover_config_root() -> Path | None:
    candidates: list[Path] = []
    here = Path(__file__).resolve()
    candidates.extend(here.parents)
    candidates.append(Path.cwd())
    seen: set[Path] = set()
    for base in candidates:
        if base in seen:
            continue
        seen.add(base)
        if (base / "deploy.config.json").is_file():
            return base
    return None


def _load_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def tier_readiness_from_env() -> str:
    tier_env = {plan: _env_set(env) for plan, env in STRIPE_PRICE_ENV_BY_PLAN.items()}
    billing_core = _env_set("STRIPE_SECRET_KEY") and _env_set("STRIPE_WEBHOOK_SECRET")
    if not billing_core or not tier_env.get("starter"):
        return "none"
    if tier_env.get("pro") and tier_env.get("enterprise"):
        return "scale"
    if tier_env.get("pro"):
        return "growth"
    return "starter"


def score_readiness(checks: list[ReadinessCheck]) -> int:
    if not checks:
        return 0
    weights = {"pass": 1.0, "warn": 0.5, "fail": 0.0}
    total = sum(weights.get(c.status, 0) for c in checks)
    return round((total / len(checks)) * 100)


def readiness_label(score: int) -> str:
    if score >= 80:
        return "Production ready"
    if score >= 50:
        return "Almost ready"
    return "Not ready"


def build_deployment_checks(*, config_root: Path | None = None) -> list[ReadinessCheck]:
    root = config_root if config_root is not None else discover_config_root()
    checks: list[ReadinessCheck] = []

    db_url = os.getenv("DATABASE_URL", "").strip()
    db_ok = any(db_url.startswith(p) for p in _DB_URL_PREFIXES)
    checks.append(
        ReadinessCheck(
            id="database-url",
            category="database",
            name="DATABASE_URL configured",
            status="pass" if db_ok else "fail",
            message="PostgreSQL connection string present" if db_ok else "DATABASE_URL missing or invalid",
            fix=None if db_ok else "Set DATABASE_URL in Railway or Deployment-Stripe-center vault",
        )
    )

    jwt = os.getenv("JWT_SECRET_KEY", "").strip()
    jwt_ok = len(jwt) >= _JWT_MIN_LEN
    checks.append(
        ReadinessCheck(
            id="jwt-secret",
            category="security",
            name="JWT secret strength",
            status="pass" if jwt_ok else "fail",
            message=f"JWT_SECRET_KEY length {len(jwt)}" if jwt else "JWT_SECRET_KEY not set",
            fix=None if jwt_ok else "Set JWT_SECRET_KEY to 32+ random characters",
        )
    )

    stripe_ready = (
        _env_set("STRIPE_SECRET_KEY")
        and _env_set("STRIPE_WEBHOOK_SECRET")
        and _env_set("STRIPE_PRICE_ID_STARTER")
    )
    checks.append(
        ReadinessCheck(
            id="stripe-starter",
            category="stripe",
            name="Stripe starter billing",
            status="pass" if stripe_ready else "warn",
            message="Starter checkout + webhooks configured" if stripe_ready else "Missing STRIPE_* starter vars",
            fix=None if stripe_ready else "Store keys in Deployment-Stripe-center vault; run full setup",
        )
    )

    tier = tier_readiness_from_env()
    tier_status = "pass" if tier in ("growth", "scale") else ("warn" if tier == "starter" else "fail")
    checks.append(
        ReadinessCheck(
            id="tier-readiness",
            category="stripe",
            name="Stripe tier env (Growth/Scale)",
            status=tier_status,
            message=f"tier_readiness={tier}",
            fix="Set STRIPE_PRICE_ID_PRO and STRIPE_PRICE_ID_ENTERPRISE for full tier upgrades"
            if tier != "scale"
            else None,
        )
    )

    metrics_on = os.getenv("METRICS_ENABLED", "1").strip().lower() not in ("0", "false", "no")
    metrics_token = _env_set("METRICS_BEARER_TOKEN")
    if metrics_on:
        checks.append(
            ReadinessCheck(
                id="metrics-auth",
                category="monitoring",
                name="Metrics scrape auth",
                status="pass" if metrics_token else "warn",
                message="METRICS_BEARER_TOKEN set" if metrics_token else "Metrics enabled without bearer token",
                fix=None if metrics_token else "Set METRICS_BEARER_TOKEN for production /metrics",
            )
        )

    if root is not None:
        for name, path in (
            ("stripe-config", root / "stripe.config.json"),
            ("deploy-config", root / "deploy.config.json"),
            ("stripe-manifest", root / ".stripe-installer" / "stripe-manifest.json"),
        ):
            ok = path.is_file()
            checks.append(
                ReadinessCheck(
                    id=name,
                    category="deploy",
                    name=f"{path.name} present",
                    status="pass" if ok else "warn",
                    message=str(path.relative_to(root)) if ok else f"Missing {path.name}",
                    fix=None if ok else "Commit automation-center config files from repo root",
                )
            )

        manifest = _load_json(root / ".stripe-installer" / "stripe-manifest.json")
        if manifest:
            for price in manifest.get("prices", []):
                env_var = price.get("envVar")
                price_id = price.get("id")
                plan_key = price.get("planKey", price.get("tier", "")).lower()
                if not env_var or not price_id:
                    continue
                configured = os.getenv(env_var, "").strip()
                if not configured:
                    continue
                aligned = configured == price_id
                checks.append(
                    ReadinessCheck(
                        id=f"manifest-{plan_key}",
                        category="stripe",
                        name=f"Manifest sync ({env_var})",
                        status="pass" if aligned else "warn",
                        message="Matches stripe-manifest.json" if aligned else "Env price ID differs from manifest",
                        fix=None
                        if aligned
                        else f"Set {env_var}={price_id} or re-run installer full setup",
                    )
                )

    deploy_cfg = _load_json(root / "deploy.config.json") if root else None
    prod_url = (deploy_cfg or {}).get("productionUrl", "").strip()
    if prod_url:
        origins = os.getenv("FRONTEND_ORIGINS", "")
        origin_ok = prod_url.rstrip("/") in origins
        checks.append(
            ReadinessCheck(
                id="frontend-origins",
                category="security",
                name="FRONTEND_ORIGINS matches production",
                status="pass" if origin_ok else "warn",
                message="CORS origin includes production URL" if origin_ok else "FRONTEND_ORIGINS may not match deploy URL",
                fix=None if origin_ok else f"Add {prod_url} to FRONTEND_ORIGINS",
            )
        )

    return checks


def build_deployment_readiness(*, config_root: Path | None = None) -> dict[str, Any]:
    checks = build_deployment_checks(config_root=config_root)
    score = score_readiness(checks)
    return {
        "score": score,
        "label": readiness_label(score),
        "tier_readiness": tier_readiness_from_env(),
        "checks": [c.to_dict() for c in checks],
        "automation_center_url": AUTOMATION_CENTER_URL,
        "config_root": str(config_root) if config_root else (str(discover_config_root()) if discover_config_root() else None),
    }


def log_startup_readiness() -> None:
    payload = build_deployment_readiness()
    score = payload["score"]
    tier = payload["tier_readiness"]
    logger.info("deployment_readiness score=%s tier_readiness=%s", score, tier)
    for check in payload["checks"]:
        if check["status"] == "fail":
            logger.warning("deployment_check fail %s: %s", check["id"], check["message"])
        elif check["status"] == "warn":
            logger.info("deployment_check warn %s: %s", check["id"], check["message"])
