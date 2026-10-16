from fastapi.testclient import TestClient


def test_an_unknown_route_uses_the_error_shape(client: TestClient) -> None:
    response = client.get("/api/v1/nothing-here")

    assert response.status_code == 404
    assert response.json() == {"error": {"code": "not_found", "message": "Not Found"}}


def test_invalid_input_names_each_field(client: TestClient) -> None:
    response = client.post("/api/v1/auth/login", json={"email": "sam@example.com"})

    assert response.status_code == 422
    body = response.json()["error"]
    assert body["code"] == "invalid_input"
    assert set(body["fields"]) == {"password"}
