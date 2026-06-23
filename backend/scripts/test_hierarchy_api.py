"""Integration tests for hierarchy API endpoints."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app


def test_hierarchy_end_to_end():
    client = TestClient(app)

    countries = client.get("/countries")
    assert countries.status_code == 200, countries.text
    data = countries.json()
    assert len(data) >= 1
    assert isinstance(data[0]["id"], int)
    assert data[0]["code"] in ("CA", "AU")

    ca = next((c for c in data if c["code"] == "CA"), data[0])
    states = client.get(f"/countries/{ca['id']}/states")
    assert states.status_code == 200, states.text
    state_list = states.json()
    assert len(state_list) >= 1
    assert isinstance(state_list[0]["id"], int)

    ontario = next((s for s in state_list if s["slug"] == "ontario"), state_list[0])
    companies = client.get(f"/states/{ontario['id']}/companies")
    assert companies.status_code == 200, companies.text
    company_list = companies.json()
    assert len(company_list) >= 1
    assert isinstance(company_list[0]["id"], str)
    assert isinstance(company_list[0]["name"], str)

    detail = client.get(f"/companies/{company_list[0]['id']}")
    assert detail.status_code == 200, detail.text
    body = detail.json()
    assert "company" in body
    assert "executives" in body
    assert body["company"]["name"]

    stats = client.get("/stats")
    assert stats.status_code == 200
    assert stats.json()["total_companies"] >= len(company_list)


if __name__ == "__main__":
    test_hierarchy_end_to_end()
    print("OK — hierarchy API end-to-end passed")
