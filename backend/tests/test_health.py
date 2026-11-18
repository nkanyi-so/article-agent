import httpx
import pytest

from app import __version__
from app.main import create_app
from app.settings import Settings


@pytest.fixture
async def client() -> httpx.AsyncClient:
    transport = httpx.ASGITransport(app=create_app(Settings()))
    return httpx.AsyncClient(transport=transport, base_url="http://testserver")


async def test_health_reports_mode_and_version(client: httpx.AsyncClient) -> None:
    response = await client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "mode": "demo", "version": __version__}


async def test_health_is_the_only_route(client: httpx.AsyncClient) -> None:
    response = await client.get("/api/runs")

    assert response.status_code == 404
