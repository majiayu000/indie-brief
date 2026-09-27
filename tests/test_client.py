import httpx
import pytest

from indie_brief.client import fetch_today
from indie_brief.errors import BriefError


def test_fetch_today_sends_bearer_and_returns_body():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["authorization"] == "Bearer secret"
        assert request.url.params["focus"] == "billing"
        return httpx.Response(200, text='{"arguments":[]}')

    body = fetch_today(
        "billing",
        url="http://brief.test",
        api_key="secret",
        transport=httpx.MockTransport(handler),
    )
    assert body == '{"arguments":[]}'


def test_fetch_today_reports_api_message():
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"code": "NO_SNAPSHOT", "message": "还没有导入简报"})

    with pytest.raises(BriefError) as caught:
        fetch_today(
            "",
            url="http://brief.test",
            api_key="secret",
            transport=httpx.MockTransport(handler),
        )
    assert caught.value.code == "API_ERROR"
    assert "还没有导入简报" in caught.value.message


def test_fetch_today_requires_a_key():
    with pytest.raises(BriefError) as caught:
        fetch_today("", url="http://brief.test", api_key="")
    assert caught.value.code == "NO_KEYS"
