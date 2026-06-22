"""Tests for Deployment-Stripe-center automation checks."""

import os
from pathlib import Path
from unittest.mock import patch

from app.automation_config import (
    build_deployment_checks,
    build_deployment_readiness,
    score_readiness,
    tier_readiness_from_env,
)


def test_tier_readiness_from_env_scale() -> None:
    env = {
        "STRIPE_SECRET_KEY": "sk_test",
        "STRIPE_WEBHOOK_SECRET": "whsec_test",
        "STRIPE_PRICE_ID_STARTER": "price_s",
        "STRIPE_PRICE_ID_PRO": "price_p",
        "STRIPE_PRICE_ID_ENTERPRISE": "price_e",
    }
    with patch.dict(os.environ, env, clear=False):
        assert tier_readiness_from_env() == "scale"


def test_tier_readiness_none_without_stripe() -> None:
    with patch.dict(os.environ, {}, clear=True):
        assert tier_readiness_from_env() == "none"


def test_build_deployment_checks_with_config_files(tmp_path: Path) -> None:
    (tmp_path / "deploy.config.json").write_text(
        '{"productionUrl": "https://example.com"}',
        encoding="utf-8",
    )
    (tmp_path / "stripe.config.json").write_text("{}", encoding="utf-8")
    installer = tmp_path / ".stripe-installer"
    installer.mkdir()
    (installer / "stripe-manifest.json").write_text(
        '{"prices": [{"planKey": "starter", "envVar": "STRIPE_PRICE_ID_STARTER", "id": "price_live"}]}',
        encoding="utf-8",
    )
    env = {
        "DATABASE_URL": "postgresql://u:p@h/db",
        "JWT_SECRET_KEY": "x" * 32,
        "STRIPE_SECRET_KEY": "sk",
        "STRIPE_WEBHOOK_SECRET": "whsec",
        "STRIPE_PRICE_ID_STARTER": "price_live",
        "STRIPE_PRICE_ID_PRO": "price_pro",
        "FRONTEND_ORIGINS": "https://example.com",
        "METRICS_ENABLED": "0",
    }
    with patch.dict(os.environ, env, clear=True):
        checks = build_deployment_checks(config_root=tmp_path)
        assert any(c.id == "stripe-config" and c.status == "pass" for c in checks)
        assert any(c.id == "manifest-starter" and c.status == "pass" for c in checks)
        readiness = build_deployment_readiness(config_root=tmp_path)
        assert readiness["score"] >= 50
        assert readiness["tier_readiness"] in ("starter", "growth", "scale")


def test_score_readiness_weighting() -> None:
    from app.automation_config import ReadinessCheck

    checks = [
        ReadinessCheck("a", "x", "A", "pass", "ok"),
        ReadinessCheck("b", "x", "B", "warn", "ok"),
    ]
    assert score_readiness(checks) == 75
