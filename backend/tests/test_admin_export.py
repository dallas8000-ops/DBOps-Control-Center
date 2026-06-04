import json

from app.admin_export import EXPORT_TABLE_NAMES

from tests.test_auth_rbac import PRIMARY_SECRET, _auth_headers, _bootstrap_dba, _client


def test_export_table_names_are_fixed_whitelist() -> None:
    assert "users" in EXPORT_TABLE_NAMES
    assert "incidents" in EXPORT_TABLE_NAMES


def test_admin_export_endpoint_returns_whitelisted_tables() -> None:
    for client in _client():
        _bootstrap_dba(client)
        login = client.post("/auth/login", json={"email": "dba@example.com", "password": PRIMARY_SECRET})
        resp = client.get("/admin/export", headers=_auth_headers(login.json()["access_token"]))
        assert resp.status_code == 200
        snapshot = json.loads(resp.text)
        for table in EXPORT_TABLE_NAMES:
            assert table in snapshot
            assert isinstance(snapshot[table], list)
