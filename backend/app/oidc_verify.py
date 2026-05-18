"""OIDC ID-token verification and authorization-code exchange (stdlib + python-jose).

No extra dependencies beyond those already in requirements.txt.

Required env vars:
    OIDC_ISSUER       - e.g. https://accounts.google.com  or  https://login.microsoftonline.com/{tenant}/v2.0
    OIDC_CLIENT_ID    - your app's client_id from the OIDC provider

Optional env vars:
    OIDC_CLIENT_SECRET  - required for confidential clients; omit for public/PKCE-only clients
    OIDC_DEFAULT_ROLE   - role assigned to auto-provisioned OIDC users (DBA|Analyst|Viewer, default: Viewer)

Verify with:  GET /health/oidc
"""

from __future__ import annotations

import json
import logging
import os
import threading
import time
import urllib.parse
from urllib import request as urlrequest
from urllib.error import URLError

from jose import JWTError, jwk, jwt

logger = logging.getLogger(__name__)

_CACHE_TTL_SECONDS = 3_600
_OIDC_NOT_CONFIGURED = "OIDC is not configured"

_discovery_cache: dict[str, tuple[dict, float]] = {}
_jwks_cache: dict[str, tuple[dict, float]] = {}
_cache_lock = threading.Lock()


# ---------------------------------------------------------------------------
# Configuration helpers
# ---------------------------------------------------------------------------


def oidc_configured() -> bool:
    return bool(os.getenv("OIDC_ISSUER", "").strip() and os.getenv("OIDC_CLIENT_ID", "").strip())


def get_oidc_issuer() -> str:
    return os.getenv("OIDC_ISSUER", "").strip().rstrip("/")


def get_oidc_client_id() -> str:
    return os.getenv("OIDC_CLIENT_ID", "").strip()


def get_oidc_default_role() -> str:
    role = os.getenv("OIDC_DEFAULT_ROLE", "Viewer").strip()
    return role if role in ("DBA", "Analyst", "Viewer") else "Viewer"


# ---------------------------------------------------------------------------
# HTTP helpers (stdlib)
# ---------------------------------------------------------------------------


def _http_get_json(url: str, timeout: int = 10) -> dict:
    req = urlrequest.Request(url, headers={"Accept": "application/json"})
    with urlrequest.urlopen(req, timeout=timeout) as res:
        return json.loads(res.read())


def _http_post_form(url: str, data: dict, timeout: int = 10) -> dict:
    encoded = urllib.parse.urlencode(data).encode("utf-8")
    req = urlrequest.Request(
        url,
        data=encoded,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    with urlrequest.urlopen(req, timeout=timeout) as res:
        return json.loads(res.read())


# ---------------------------------------------------------------------------
# Discovery + JWKS caching
# ---------------------------------------------------------------------------


def _get_discovery(issuer: str) -> dict:
    now = time.monotonic()
    with _cache_lock:
        cached = _discovery_cache.get(issuer)
        if cached and now - cached[1] < _CACHE_TTL_SECONDS:
            return cached[0]
    doc = _http_get_json(f"{issuer}/.well-known/openid-configuration")
    with _cache_lock:
        _discovery_cache[issuer] = (doc, time.monotonic())
    return doc


def _get_jwks(jwks_uri: str, *, force_refresh: bool = False) -> dict:
    now = time.monotonic()
    with _cache_lock:
        cached = _jwks_cache.get(jwks_uri)
        if not force_refresh and cached and now - cached[1] < _CACHE_TTL_SECONDS:
            return cached[0]
    keys = _http_get_json(jwks_uri)
    with _cache_lock:
        _jwks_cache[jwks_uri] = (keys, time.monotonic())
    return keys


# ---------------------------------------------------------------------------
# Token verification
# ---------------------------------------------------------------------------


def _select_jwk(token: str, jwks: dict) -> dict:
    """Pick the signing key from a JWKS dict that matches the token's kid header."""
    # Reading the header without verifying the signature is intentional here:
    # we only extract the `kid` to select the correct signing key from the JWKS,
    # then the full signature verification happens in _decode_id_token.
    try:
        headers = jwt.get_unverified_header(token)
    except JWTError as exc:
        raise ValueError(f"Cannot read token header: {exc}") from exc

    kid = headers.get("kid")
    all_keys = jwks.get("keys", [])

    if kid:
        matched = [k for k in all_keys if k.get("kid") == kid]
        if matched:
            return matched[0]

    sig_keys = [k for k in all_keys if k.get("use", "sig") == "sig"]
    if sig_keys:
        return sig_keys[0]
    if all_keys:
        return all_keys[0]

    raise ValueError(f"No usable signing key found in JWKS for kid={kid!r}")


def _decode_id_token(token: str, key_data: dict, *, issuer: str, client_id: str) -> dict:
    alg = key_data.get("alg", "RS256")
    key_obj = jwk.construct(key_data, algorithm=alg)
    return jwt.decode(
        token,
        key_obj.to_pem().decode("utf-8"),
        algorithms=["RS256", "RS384", "RS512", "ES256", "ES384", "ES512"],
        audience=client_id,
        issuer=issuer,
    )


def verify_oidc_id_token(id_token: str) -> dict:
    """Verify an OIDC ID token and return its claims.

    Raises:
        ValueError  – OIDC not configured, bad token structure, missing email.
        JWTError    – signature/claims validation failure.
        URLError    – network issue reaching the OIDC provider.
    """
    if not oidc_configured():
        raise ValueError(_OIDC_NOT_CONFIGURED)

    issuer = get_oidc_issuer()
    client_id = get_oidc_client_id()
    discovery = _get_discovery(issuer)
    jwks_uri = discovery["jwks_uri"]

    def _try_decode(force: bool) -> dict:
        jw = _get_jwks(jwks_uri, force_refresh=force)
        key_data = _select_jwk(id_token, jw)
        return _decode_id_token(id_token, key_data, issuer=issuer, client_id=client_id)

    try:
        claims = _try_decode(False)
    except (JWTError, ValueError):
        logger.debug("JWKS key miss — refreshing JWKS cache and retrying")
        claims = _try_decode(True)

    if not claims.get("email"):
        raise ValueError("ID token is missing the email claim")

    return claims


# ---------------------------------------------------------------------------
# Authorization-code exchange (PKCE)
# ---------------------------------------------------------------------------


def exchange_authorization_code(
    *,
    code: str,
    redirect_uri: str,
    code_verifier: str,
) -> dict:
    """Exchange a PKCE authorization code for tokens at the provider's token endpoint.

    Returns the raw token endpoint response (contains id_token, access_token, etc.).

    Raises:
        ValueError  – OIDC not configured or provider returned an error.
        URLError    – network issue.
    """
    if not oidc_configured():
        raise ValueError(_OIDC_NOT_CONFIGURED)

    issuer = get_oidc_issuer()
    client_id = get_oidc_client_id()
    client_secret = os.getenv("OIDC_CLIENT_SECRET", "").strip()
    discovery = _get_discovery(issuer)
    token_endpoint = discovery["token_endpoint"]

    data: dict[str, str] = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": redirect_uri,
        "client_id": client_id,
        "code_verifier": code_verifier,
    }
    if client_secret:
        data["client_secret"] = client_secret

    try:
        response = _http_post_form(token_endpoint, data)
    except URLError as exc:
        raise URLError(f"Token endpoint unreachable: {exc}") from exc

    if "error" in response:
        raise ValueError(f"Token endpoint error: {response.get('error_description', response['error'])}")

    return response


# ---------------------------------------------------------------------------
# Frontend config helper
# ---------------------------------------------------------------------------


def get_authorization_endpoint() -> str:
    """Return the OIDC provider's authorization endpoint URL."""
    if not oidc_configured():
        raise ValueError(_OIDC_NOT_CONFIGURED)
    discovery = _get_discovery(get_oidc_issuer())
    return discovery["authorization_endpoint"]
