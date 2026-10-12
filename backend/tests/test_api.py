"""HTTP contracts, validation, and persistence across application restarts."""

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from matapan.main import create_app


def test_health_and_interactive_api(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok", "version": "0.1.0"}
    assert client.get("/docs").status_code == 200
    schema = client.get("/openapi.json").json()
    assert (
        schema["components"]["schemas"]["BalanceCreate"]["properties"]["amount"]["type"] == "string"
    )


def test_create_list_and_read_account(client):
    response = client.post(
        "/api/v1/accounts",
        json={
            "name": "  Test account  ",
            "institution": "Synthetic Bank",
            "currency_code": " chf ",
        },
    )
    assert response.status_code == 201
    account = response.json()
    assert account["name"] == "Test account"
    assert account["currency_code"] == "CHF"
    assert account["created_at"].endswith("Z")
    assert client.get(f"/api/v1/accounts/{account['id']}").json() == account
    assert client.get("/api/v1/accounts").json() == [account]


@pytest.mark.parametrize(
    "payload",
    [
        {"name": " ", "currency_code": "CHF"},
        {"name": "Test", "currency_code": "CH"},
        {"name": "Test", "currency_code": "C1F"},
        {"name": "Test", "currency_code": "CHF", "unexpected": "value"},
    ],
)
def test_invalid_account_does_not_persist(client, payload):
    assert client.post("/api/v1/accounts", json=payload).status_code == 422
    assert client.get("/api/v1/accounts").json() == []


def test_delete_empty_account_survives_restart(client, database_url, account):
    other = client.post(
        "/api/v1/accounts", json={"name": "Keep this account", "currency_code": "EUR"}
    ).json()
    url = f"/api/v1/accounts/{account['id']}"
    response = client.delete(url)
    assert response.status_code == 204
    assert response.content == b""
    assert client.get(url).status_code == 404
    assert client.delete(url).status_code == 404
    with TestClient(create_app(database_url), base_url="http://localhost") as restarted:
        assert restarted.get(url).status_code == 404
        assert restarted.get("/api/v1/accounts").json() == [other]


def test_delete_unknown_or_invalid_account(client):
    assert client.delete(f"/api/v1/accounts/{uuid4()}").status_code == 404
    assert client.delete("/api/v1/accounts/not-a-uuid").status_code == 422


def test_delete_account_with_balance_preserves_data(client, account, save_balance):
    saved = save_balance("123.45")
    url = f"/api/v1/accounts/{account['id']}"
    response = client.delete(url)
    assert response.status_code == 409
    assert client.get(url).json() == account
    assert client.get(f"{url}/cash-balances").json() == [saved]
    assert client.get(f"{url}/report?as_of=2026-01-31").json()["amount"] == "123.45"


@pytest.mark.parametrize(
    "amount",
    [12.34, 123, True, None, "NaN", "Infinity", "1e3", "1.234567891", "100000000000000000000"],
)
def test_invalid_amount_does_not_persist(client, account, amount):
    url = f"/api/v1/accounts/{account['id']}/cash-balances"
    response = client.post(
        url, json={"currency_code": "CHF", "as_of_date": "2026-01-31", "amount": amount}
    )
    assert response.status_code == 422
    assert client.get(url).json() == []


@pytest.mark.parametrize("as_of", ["not-a-date", "2026-02-30", "20260131", 1769817600])
def test_invalid_balance_date_does_not_persist(client, account, as_of):
    url = f"/api/v1/accounts/{account['id']}/cash-balances"
    response = client.post(
        url, json={"currency_code": "CHF", "as_of_date": as_of, "amount": "1.00"}
    )
    assert response.status_code == 422
    assert client.get(url).json() == []


def test_wrong_currency_does_not_persist(client, account):
    url = f"/api/v1/accounts/{account['id']}/cash-balances"
    response = client.post(
        url, json={"currency_code": "EUR", "as_of_date": "2026-01-31", "amount": "100.00"}
    )
    assert response.status_code == 422
    assert client.get(url).json() == []


def test_money_and_provenance_survive_restart(client, database_url, account, save_balance):
    saved = save_balance("9007199254740993.12345678")
    assert saved["amount"] == "9007199254740993.12345678"
    assert saved["source"] == "manual"
    assert saved["status"] == "user_confirmed"
    assert saved["recorded_at"].endswith("Z")
    with TestClient(create_app(database_url), base_url="http://localhost") as restarted:
        assert restarted.get(f"/api/v1/accounts/{account['id']}/cash-balances").json() == [saved]


def test_unknown_accounts_are_not_created_implicitly(client):
    missing = str(uuid4())
    assert client.get(f"/api/v1/accounts/{missing}").status_code == 404
    assert client.get(f"/api/v1/accounts/{missing}/cash-balances").status_code == 404
    assert client.get(f"/api/v1/accounts/{missing}/report?as_of=2026-01-31").status_code == 404
    response = client.post(
        f"/api/v1/accounts/{missing}/cash-balances",
        json={"currency_code": "CHF", "as_of_date": "2026-01-31", "amount": "1.00"},
    )
    assert response.status_code == 404


def test_nonlocal_host_is_rejected(client):
    assert client.get("/health", headers={"Host": "untrusted.example"}).status_code == 400


def test_pagination_is_bounded(client):
    assert client.get("/api/v1/accounts?limit=101").status_code == 422
    assert client.get("/api/v1/accounts?offset=-1").status_code == 422
