import pytest

from app.services import voice_provider_status as provider_status


@pytest.fixture(autouse=True)
def reset_provider_status_cache():
    provider_status.reset_voice_provider_status_cache()
    yield
    provider_status.reset_voice_provider_status_cache()


@pytest.mark.asyncio
async def test_missing_provider_keys_are_reported(monkeypatch):
    monkeypatch.setattr(provider_status.settings, "GROQ_API_KEY", "", raising=False)
    monkeypatch.setattr(provider_status.settings, "CARTESIA_API_KEY", "", raising=False)

    status = await provider_status.get_voice_provider_status(force_refresh=True)

    assert status["blocking"] is True
    assert any(
        issue["provider"] == "Groq" and issue["status"] == "missing_api_key"
        for issue in status["issues"]
    )
    assert any(
        issue["provider"] == "Cartesia" and issue["status"] == "missing_api_key"
        for issue in status["issues"]
    )


@pytest.mark.asyncio
async def test_groq_limit_reached_blocks_voice_start(monkeypatch):
    async def fake_groq_check(_api_key):
        return provider_status._build_issue(
            provider="Groq",
            env_var="GROQ_API_KEY",
            status="limit_reached",
            severity="blocking",
            message="Groq API limit is reached or quota is over.",
        )

    async def fake_cartesia_check(_api_key):
        return None

    monkeypatch.setattr(provider_status.settings, "GROQ_API_KEY", "gsk_test", raising=False)
    monkeypatch.setattr(provider_status.settings, "CARTESIA_API_KEY", "cartesia_test", raising=False)
    monkeypatch.setattr(provider_status, "_check_groq_provider", fake_groq_check)
    monkeypatch.setattr(provider_status, "_check_cartesia_provider", fake_cartesia_check)

    status = await provider_status.get_voice_provider_status(force_refresh=True)

    assert status["blocking"] is True
    assert provider_status.get_voice_provider_error_http_status(status) == 429


@pytest.mark.asyncio
async def test_cartesia_issue_is_warning_when_groq_is_available(monkeypatch):
    async def fake_groq_check(_api_key):
        return None

    async def fake_cartesia_check(_api_key):
        return provider_status._build_issue(
            provider="Cartesia",
            env_var="CARTESIA_API_KEY",
            status="limit_reached",
            severity="warning",
            message="Cartesia API limit is reached or quota is over. Voice will fall back to Groq TTS.",
        )

    monkeypatch.setattr(provider_status.settings, "GROQ_API_KEY", "gsk_test", raising=False)
    monkeypatch.setattr(provider_status.settings, "CARTESIA_API_KEY", "cartesia_test", raising=False)
    monkeypatch.setattr(provider_status, "_check_groq_provider", fake_groq_check)
    monkeypatch.setattr(provider_status, "_check_cartesia_provider", fake_cartesia_check)

    status = await provider_status.get_voice_provider_status(force_refresh=True)

    assert status["blocking"] is False
    assert status["issues"] == [
        {
            "provider": "Cartesia",
            "env_var": "CARTESIA_API_KEY",
            "status": "limit_reached",
            "severity": "warning",
            "message": "Cartesia API limit is reached or quota is over. Voice will fall back to Groq TTS.",
        }
    ]
