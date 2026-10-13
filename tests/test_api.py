"""End-to-end API tests running against SQLite with the in-memory cache."""
import httpx
import pytest

from app.config import get_settings
from app.main import app

CREDS = {
    "name": "Vendedora Lautaro",
    "email": "owner@example.test",
    "password": "UnaClaveSegura123",
}


def product(**overrides):
    data = {
        "title": "Bicicleta urbana",
        "description": "En buen estado y lista para usar.",
        "price": 85000,
        "category": "Deportes",
        "city": "Lautaro",
        "image": "",
        "condition": "Usado",
    }
    data.update(overrides)
    return data


def fresh_client():
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    )


async def test_auth_basics(client):
    assert (await client.get("/api/me")).json() is None

    registered = await client.post("/api/register", json=CREDS)
    assert registered.status_code == 200
    body = registered.json()
    assert body["email"] == CREDS["email"] and "password" not in body

    assert (await client.get("/api/me")).json()["name"] == CREDS["name"]
    assert (await client.post("/api/register", json=dict(CREDS))).status_code == 409

    await client.post("/api/logout")
    assert (await client.get("/api/me")).json() is None

    wrong = await client.post(
        "/api/login", json={"email": CREDS["email"], "password": "WrongPassword123"}
    )
    assert wrong.status_code == 401
    ok = await client.post(
        "/api/login", json={"email": CREDS["email"], "password": CREDS["password"]}
    )
    assert ok.status_code == 200


async def test_listing_crud_and_validation(client):
    assert (await client.post("/api/listings", json=product())).status_code == 401

    await client.post("/api/register", json=CREDS)
    assert (await client.post("/api/listings", json=product(price=-1))).status_code == 400
    assert (
        await client.post("/api/listings", json=product(image="javascript:alert(1)"))
    ).status_code == 400
    assert (
        await client.post("/api/listings", json=product(image="http://insecure.test/x.png"))
    ).status_code == 400
    assert (await client.post("/api/listings", json=product(category="Nope"))).status_code == 400
    assert (
        await client.post("/api/listings", json=product(image="/media/../secret"))
    ).status_code == 400

    created = await client.post(
        "/api/listings", json=product(image="/media/uploaded.png")
    )
    assert created.status_code == 201
    listing_id = created.json()["id"]

    listings = (await client.get("/api/listings")).json()
    assert len(listings) == 1
    assert listings[0]["seller"] == CREDS["name"]
    assert listings[0]["image"] == "/media/uploaded.png"
    assert listings[0]["favorite_count"] == 0
    assert (await client.get(f"/api/listings/{listing_id}")).json()["title"] == product()["title"]
    assert (await client.get("/api/listings/999999")).status_code == 404

    assert (
        await client.patch(f"/api/listings/{listing_id}", json={"price": 65000})
    ).status_code == 200
    assert (await client.get(f"/api/listings/{listing_id}")).json()["price"] == 65000
    assert (
        await client.patch(f"/api/listings/{listing_id}", json={"condition": "Roto"})
    ).status_code == 400

    assert (await client.delete(f"/api/listings/{listing_id}")).status_code == 200
    assert (await client.get("/api/listings")).json() == []


async def test_filters_sort_pagination_and_count(client):
    await client.post("/api/register", json=CREDS)
    ids = []
    for index in range(5):
        response = await client.post(
            "/api/listings",
            json=product(
                title=f"Producto {index}",
                price=1000 + index,
                city="Temuco" if index % 2 else "Lautaro",
                category="Hogar" if index % 2 else "Moda",
                condition="Nuevo" if index == 0 else "Usado",
            ),
        )
        ids.append(response.json()["id"])

    assert (await client.get("/api/listings/count")).json() == {"total": 5}

    first = (await client.get("/api/listings?limit=2&offset=0&sort=price_asc")).json()
    second = (await client.get("/api/listings?limit=2&offset=2&sort=price_asc")).json()
    assert len(first) == 2 and len(second) == 2
    assert {row["id"] for row in first}.isdisjoint({row["id"] for row in second})
    assert first[0]["price"] == 1000

    assert len((await client.get("/api/listings?category=Hogar")).json()) == 2
    assert len((await client.get("/api/listings?city=Lautaro")).json()) == 3
    assert len((await client.get("/api/listings?condition=Nuevo")).json()) == 1
    assert len((await client.get("/api/listings?q=Producto%204")).json()) == 1

    assert (await client.get("/api/listings?limit=abc")).status_code == 400
    assert (await client.get("/api/listings?limit=0")).status_code == 400
    assert (await client.get("/api/listings?min_price=100&max_price=1")).status_code == 400
    assert (await client.get("/api/listings?sort=nope")).status_code == 400


async def test_favorites_sold_and_profile(client):
    await client.post("/api/register", json=CREDS)
    listing_id = (await client.post("/api/listings", json=product())).json()["id"]

    async with fresh_client() as buyer:
        await buyer.post(
            "/api/register", json=dict(CREDS, email="buyer@example.test", name="Comprador")
        )
        assert (await buyer.post(f"/api/favorites/{listing_id}")).status_code == 200
        assert (await buyer.post(f"/api/favorites/{listing_id}")).status_code == 200
        favorites = (await buyer.get("/api/listings?favorites=1")).json()
        assert len(favorites) == 1 and favorites[0]["favorite"] is True
        assert (await buyer.get(f"/api/listings/{listing_id}")).json()["favorite_count"] == 1
        assert (await buyer.delete(f"/api/favorites/{listing_id}")).status_code == 200
        assert (await buyer.get("/api/listings?favorites=1")).json() == []

    assert (await client.patch(f"/api/listings/{listing_id}", json={"status": "sold"})).status_code == 200
    assert (await client.get("/api/listings")).json() == []
    mine = (await client.get("/api/listings?mine=1")).json()
    assert len(mine) == 1 and mine[0]["status"] == "sold"

    renamed = await client.patch("/api/profile", json={"name": "Nuevo nombre"})
    assert renamed.json()["name"] == "Nuevo nombre"
    assert (await client.get(f"/api/listings/{listing_id}")).json()["seller"] == "Nuevo nombre"


async def test_authorization_boundaries(client):
    await client.post("/api/register", json=CREDS)
    listing_id = (await client.post("/api/listings", json=product())).json()["id"]

    assert (await client.get("/api/listings?mine=1")).status_code == 200  # authenticated
    assert (await client.get("/api/listings/count?mine=1")).status_code == 200

    async with fresh_client() as stranger:
        assert (await stranger.get("/api/listings?mine=1")).status_code == 401
        assert (await stranger.get("/api/listings?favorites=1")).status_code == 401
        assert (await stranger.patch(f"/api/listings/{listing_id}", json={"price": 1})).status_code == 401

    async with fresh_client() as other:
        await other.post(
            "/api/register", json=dict(CREDS, email="other@example.test", name="Otro")
        )
        assert (
            await other.patch(f"/api/listings/{listing_id}", json={"price": 1})
        ).status_code == 404
        assert (await other.delete(f"/api/listings/{listing_id}")).status_code == 404


async def test_origin_guard_blocks_cross_site(client):
    response = await client.post(
        "/api/register", json=CREDS, headers={"Origin": "https://evil.example"}
    )
    assert response.status_code == 403
    response = await client.get(
        "/api/listings", headers={"Sec-Fetch-Site": "cross-site"}
    )
    assert response.status_code == 200  # safe method is allowed


async def test_upload_image(client):
    png = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32
    assert (
        await client.post("/api/uploads", files={"file": ("a.png", png, "image/png")})
    ).status_code == 401

    await client.post("/api/register", json=CREDS)
    ok = await client.post(
        "/api/uploads", files={"file": ("a.png", png, "image/png")}
    )
    assert ok.status_code == 200
    assert ok.json()["url"].startswith("/media/")

    bad = await client.post(
        "/api/uploads", files={"file": ("a.txt", b"not an image", "text/plain")}
    )
    assert bad.status_code == 400


async def test_auth_rate_limit(client):
    settings = get_settings()
    original = settings.auth_rate_limit
    settings.auth_rate_limit = 2
    try:
        statuses = []
        for _ in range(3):
            response = await client.post(
                "/api/login",
                json={"email": "absent@example.test", "password": "WrongPassword123"},
            )
            statuses.append(response.status_code)
        assert statuses[-1] == 429
    finally:
        settings.auth_rate_limit = original


@pytest.mark.parametrize(
    "payload",
    [
        {"email": "invalid", "password": "1234567890"},
        {"email": "a@b.cl", "password": "short"},
    ],
)
async def test_register_validation(client, payload):
    response = await client.post("/api/register", json={**payload, "name": "Valido"})
    assert response.status_code == 400
