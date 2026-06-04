from app.rate_limit import auth_rate_limit_key, check_auth_rate_limit, reset_auth_rate_limit


def test_none_client_host_uses_unknown_bucket_and_still_limits() -> None:
    reset_auth_rate_limit()
    key = auth_rate_limit_key(None, "login")
    assert key == "login:unknown"
    assert check_auth_rate_limit(None, "login") is True
    assert check_auth_rate_limit(None, "login") is True
