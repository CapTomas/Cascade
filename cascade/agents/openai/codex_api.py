"""Codex agent implementation via OpenAI API."""

from __future__ import annotations

import json
import logging
import os
import time
import urllib.error
import urllib.request
from collections.abc import Callable

from cascade.agents.interface import (
    AgentCapabilities,
    AgentCapability,
    AgentConfig,
    AgentInterface,
    AgentResponse,
)

logger = logging.getLogger(__name__)


class CodexApiAgent(AgentInterface):
    """
    Codex agent via OpenAI Responses API.

    Configuration:
    - CODEX_API_KEY (or OPENAI_API_KEY): required
    - CODEX_BASE_URL (or OPENAI_BASE_URL): optional
    - CODEX_MODEL (or OPENAI_MODEL): required
    """

    DEFAULT_TOKEN_LIMIT = 128000

    def __init__(self, config: AgentConfig | None = None):
        super().__init__(config)

    def get_name(self) -> str:
        return "codex-api"

    def get_capabilities(self) -> AgentCapabilities:
        return AgentCapabilities(
            capabilities={
                AgentCapability.CODE_ANALYSIS,
            },
            supports_streaming=False,
            supports_tools=False,
            max_output_tokens=4096,
        )

    def get_token_limit(self) -> int:
        return self.DEFAULT_TOKEN_LIMIT

    def is_available(self) -> bool:
        return bool(self._get_api_key() and self._get_model())

    def execute(
        self,
        prompt: str,
        working_dir: str | None = None,
        callback: Callable[[str], None] | None = None,
    ) -> AgentResponse:
        is_valid, error = self.validate_prompt(prompt)
        if not is_valid:
            return AgentResponse(success=False, content="", error=error)

        # Validate working directory
        is_safe, error = self._validate_working_dir(working_dir)
        if not is_safe:
            return AgentResponse(success=False, content="", error=error)

        api_key = self._get_api_key()
        model = self._get_model()
        if not api_key or not model:
            return AgentResponse(
                success=False,
                content="",
                error="OPENAI_API_KEY and OPENAI_MODEL must be set",
            )

        start_time = time.time()
        url = self._get_base_url().rstrip("/") + "/responses"
        payload = {
            "model": model,
            "input": prompt,
        }

        data = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(  # noqa: S310
            url,
            data=data,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        max_retries = self.config.max_retries
        retry_delay = 1.0

        for attempt in range(max_retries + 1):
            try:
                # Allow custom schemes like https for API calls
                with urllib.request.urlopen(request, timeout=self.config.timeout_seconds) as resp:  # noqa: S310
                    raw = resp.read().decode("utf-8")
                    break
            except urllib.error.HTTPError as exc:
                if attempt < max_retries and exc.code in (429, 500, 502, 503, 504):
                    logger.warning(
                        f"Codex API temporary failure ({exc.code}). Retrying in {retry_delay}s..."
                    )
                    time.sleep(retry_delay)
                    retry_delay *= 2
                    continue
                try:
                    body = exc.read().decode("utf-8")
                    error_details = json.loads(body).get("error", {}).get("message", body)
                except Exception:
                    error_details = exc.reason
                return AgentResponse(
                    success=False,
                    content="",
                    error=f"HTTP {exc.code}: {error_details}",
                    execution_time_ms=int((time.time() - start_time) * 1000),
                    raw_output=body if "body" in locals() else str(exc),
                )
            except (urllib.error.URLError, TimeoutError) as exc:
                if attempt < max_retries:
                    time.sleep(retry_delay)
                    retry_delay *= 2
                    continue
                return AgentResponse(
                    success=False,
                    content="",
                    error=f"Network Error: {exc}",
                    execution_time_ms=int((time.time() - start_time) * 1000),
                )
            except Exception as exc:
                logger.exception("Unexpected error executing Codex agent")
                return AgentResponse(
                    success=False,
                    content="",
                    error=f"Unexpected error: {exc}",
                    execution_time_ms=int((time.time() - start_time) * 1000),
                )

        execution_time = int((time.time() - start_time) * 1000)
        content = self._extract_text(raw)

        return AgentResponse(
            success=True,
            content=content,
            execution_time_ms=execution_time,
            raw_output=raw,
        )

    def _get_api_key(self) -> str | None:
        return (
            self.config.environment.get("CODEX_API_KEY")
            or os.environ.get("CODEX_API_KEY")
            or self.config.environment.get("OPENAI_API_KEY")
            or os.environ.get("OPENAI_API_KEY")
        )

    def _get_model(self) -> str | None:
        return (
            self.config.environment.get("CODEX_MODEL")
            or os.environ.get("CODEX_MODEL")
            or self.config.environment.get("OPENAI_MODEL")
            or os.environ.get("OPENAI_MODEL")
        )

    def _get_base_url(self) -> str:
        return (
            self.config.environment.get("CODEX_BASE_URL")
            or os.environ.get("CODEX_BASE_URL")
            or self.config.environment.get("OPENAI_BASE_URL")
            or os.environ.get("OPENAI_BASE_URL")
            or "https://api.openai.com/v1"
        )

    def _extract_text(self, raw: str) -> str:
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return raw

        # Responses API typically returns "output_text"
        output_text = data.get("output_text")
        if isinstance(output_text, str) and output_text.strip():
            return output_text

        # Fallback: try to read the first output content
        output = data.get("output", [])
        if output and isinstance(output, list):
            first = output[0] if output else {}
            content = first.get("content", [])
            if content and isinstance(content, list):
                text = content[0].get("text")
                if isinstance(text, str):
                    return text

        return raw
