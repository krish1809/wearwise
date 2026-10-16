"""Adding wardrobe items and outfits through the API, for tests."""

from typing import Any

from fastapi.testclient import TestClient


def add_item(client: TestClient, category_id: str, color: str, **fields: Any) -> dict[str, Any]:
    body = {"category_id": category_id, "color_primary": color, **fields}
    response = client.post("/api/v1/items", json=body)
    assert response.status_code == 201, response.text
    item: dict[str, Any] = response.json()
    return item


def basics(client: TestClient) -> dict[str, dict[str, Any]]:
    """A small wardrobe: shirt, chinos, loafers, sneakers, a watch, a dress."""
    return {
        "shirt": add_item(client, "casual_shirt", "navy"),
        "chinos": add_item(client, "chinos", "olive"),
        "loafers": add_item(client, "loafers", "brown"),
        "sneakers": add_item(client, "sneakers", "white"),
        "watch": add_item(client, "watch", "silver"),
        "dress": add_item(client, "dress", "black"),
    }


def save_outfit(client: TestClient, *items: dict[str, Any], **fields: Any) -> dict[str, Any]:
    body = {"item_ids": [item["id"] for item in items], **fields}
    response = client.post("/api/v1/outfits", json=body)
    assert response.status_code == 201, response.text
    outfit: dict[str, Any] = response.json()
    return outfit
