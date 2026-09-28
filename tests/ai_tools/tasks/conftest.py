import httpx
import pytest

from src.cases.repos.cases_http_client import CasesHttpClient
from tests.cases.conftest import API_KEY, BASE_URL, FakeCasesService


@pytest.fixture
def fake_service() -> FakeCasesService:
    return FakeCasesService()


@pytest.fixture
def client(fake_service: FakeCasesService) -> CasesHttpClient:
    return CasesHttpClient(
        base_url=BASE_URL,
        api_key=API_KEY,
        transport=httpx.MockTransport(fake_service.handle),
    )
