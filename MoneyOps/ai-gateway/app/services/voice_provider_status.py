from __future__ import annotations

import asyncio
import time
from typing import Any, Optional

import httpx

from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

_CACHE_TTL_SECONDS = 60
_CARTESIA_API_VERSION = "2025-04-16"
_cached_status: Optional[dict[str, Any]] = None
_cached_status_expires_at = 0.0


def reset_voice_provider_status_cache() -> None:
    global _cached_status, _cached_status_expires_at
    _cached_status = None
    _cached_status_expires_at = 0.0


def get_voice_provider_error_http_status(provider_status: dict[str, Any]) -> int:
    issues = provider_status.get("issues", [])
    if any(
        issue.get("severity") == "blocking" and issue.get("status") == "limit_reached"
        for issue in issues
    ):
        return 429
    return 503


def get_voice_provider_error_message(provider_status: dict[str, Any]) -> str:
    blocking_issues = [
        issue for issue in provider_status.get("issues", []) if issue.get("severity") == "blocking"
    ]
    if not blocking_issues:
        return "Voice agent could not start because the provider status could not be verified."

    provider_names = ", ".join(issue.get("provider", "Provider") for issue in blocking_issues)
    return f"Voice agent could not start because {provider_names} needs attention."


async def get_voice_provider_status(force_refresh: bool = False) -> dict[str, Any]:
    global _cached_status, _cached_status_expires_at

    now = time.monotonic()
    if not force_refresh and _cached_status is not None and now < _cached_status_expires_at:
        return _cached_status

    issues: list[dict[str, Any]] = []
    tasks: list[asyncio.Task[Optional[dict[str, Any]]]] = []

    groq_key = (settings.GROQ_API_KEY or "").strip()
    cartesia_key = (settings.CARTESIA_API_KEY or "").strip()

    if not groq_key:
        issues.append(
            _build_issue(
                provider="Groq",
                env_var="GROQ_API_KEY",
                status="missing_api_key",
                severity="blocking",
                message="Groq API key is empty. Add GROQ_API_KEY before starting the voice agent.",
            )
        )
    else:
        tasks.append(asyncio.create_task(_check_groq_provider(groq_key)))

    if not cartesia_key:
        issues.append(
            _build_issue(
                provider="Cartesia",
                env_var="CARTESIA_API_KEY",
                status="missing_api_key",
                severity="warning",
                message="Cartesia API key is empty. Voice will fall back to Groq TTS.",
            )
        )
    else:
        tasks.append(asyncio.create_task(_check_cartesia_provider(cartesia_key)))

    if tasks:
        for result in await asyncio.gather(*tasks):
            if result:
                issues.append(result)

    status = {
        "blocking": any(issue.get("severity") == "blocking" for issue in issues),
        "issues": issues,
        "checked_at": int(time.time()),
    }

    _cached_status = status
    _cached_status_expires_at = now + _CACHE_TTL_SECONDS
    return status


def _build_issue(
    *,
    provider: str,
    env_var: str,
    status: str,
    severity: str,
    message: str,
) -> dict[str, Any]:
    return {
        "provider": provider,
        "env_var": env_var,
        "status": status,
        "severity": severity,
        "message": message,
    }


async def _check_groq_provider(api_key: str) -> Optional[dict[str, Any]]:
    response = await _call_provider(
        url="https://api.groq.com/openai/v1/models",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
    )
    return _map_provider_response("Groq", "GROQ_API_KEY", "blocking", response)


async def _check_cartesia_provider(api_key: str) -> Optional[dict[str, Any]]:
    response = await _call_provider(
        url="https://api.cartesia.ai/voices?limit=1",
        headers={
            "Cartesia-Version": _CARTESIA_API_VERSION,
            "X-API-Key": api_key,
        },
    )
    issue = _map_provider_response("Cartesia", "CARTESIA_API_KEY", "warning", response)
    if not issue:
        return None

    if issue["status"] == "limit_reached":
        issue["message"] = "Cartesia API limit is reached or quota is over. Voice will fall back to Groq TTS."
    elif issue["status"] == "invalid_api_key":
        issue["message"] = "Cartesia API key is invalid or unauthorized. Voice will fall back to Groq TTS."
    elif issue["status"] == "provider_unreachable":
        issue["message"] = "Cartesia could not be reached right now. Voice will fall back to Groq TTS."

    return issue


async def _call_provider(*, url: str, headers: dict[str, str]) -> dict[str, Any]:
    timeout = settings.VOICE_PROVIDER_CHECK_TIMEOUT_S
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(url, headers=headers)
        return {
            "status_code": response.status_code,
            "message": _extract_error_message(response),
        }
    except httpx.TimeoutException:
        return {"status_code": None, "message": "Request timed out while checking the provider."}
    except httpx.HTTPError as exc:
        return {"status_code": None, "message": str(exc)}


def _map_provider_response(
    provider: str,
    env_var: str,
    severity: str,
    response: dict[str, Any],
) -> Optional[dict[str, Any]]:
    status_code = response.get("status_code")
    provider_message = (response.get("message") or "").strip()

    if status_code and 200 <= status_code < 300:
        return None

    if status_code == 429:
        message = f"{provider} API limit is reached or quota is over."
        if provider_message:
            message = f"{message} {provider_message}"
        return _build_issue(
            provider=provider,
            env_var=env_var,
            status="limit_reached",
            severity=severity,
            message=message,
        )

    if status_code in {401, 403}:
        message = f"{provider} API key is invalid or unauthorized."
        if provider_message:
            message = f"{message} {provider_message}"
        return _build_issue(
            provider=provider,
            env_var=env_var,
            status="invalid_api_key",
            severity=severity,
            message=message,
        )

    if status_code is None:
        message = f"{provider} could not be reached right now."
        if provider_message:
            message = f"{message} {provider_message}"
        return _build_issue(
            provider=provider,
            env_var=env_var,
            status="provider_unreachable",
            severity=severity,
            message=message,
        )

    message = f"{provider} returned an unexpected status ({status_code})."
    if provider_message:
        message = f"{message} {provider_message}"
    return _build_issue(
        provider=provider,
        env_var=env_var,
        status="provider_error",
        severity=severity,
        message=message,
    )


def _extract_error_message(response: httpx.Response) -> str:
    try:
        payload = response.json()
    except ValueError:
        return (response.text or "").strip()

    if isinstance(payload, dict):
        error = payload.get("error")
        if isinstance(error, dict):
            return str(
                error.get("message")
                or error.get("detail")
                or error.get("type")
                or ""
            ).strip()
        return str(payload.get("message") or payload.get("detail") or "").strip()

    return str(payload).strip()
