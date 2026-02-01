from __future__ import annotations

import json
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
from cascade.utils.logger import get_logger

logger = get_logger(__name__)


class GeminiApiAgent(AgentInterface):
    """
    Google Gemini agent implementation via API (formerly Antigravity).

    Configuration:
    - GEMINI_API_KEY (or ANTIGRAVITY_API_KEY): required
    - GEMINI_BASE_URL (or ANTIGRAVITY_BASE_URL): optional
    - GEMINI_MODEL (or ANTIGRAVITY_MODEL): optional
    """

    DEFAULT_BASE_URL = "https://api.antigravity.ai/v1"
    DEFAULT_MODEL = "antigravity-pro-1"
    DEFAULT_TOKEN_LIMIT = 1000000

    def __init__(self, config: AgentConfig | None = None):
        super().__init__(config)

    def get_name(self) -> str:
        return "gemini-api"

    def get_capabilities(self) -> AgentCapabilities:
        return AgentCapabilities(
            capabilities={
                AgentCapability.FILE_READ,
                AgentCapability.FILE_WRITE,
                AgentCapability.FILE_EDIT,
                AgentCapability.COMMAND_EXECUTE,
                AgentCapability.CODE_ANALYSIS,
                AgentCapability.WEB_SEARCH,
            },
            supports_streaming=True,
            supports_tools=True,
            max_output_tokens=8192,
        )

    def get_token_limit(self) -> int:
        return self.DEFAULT_TOKEN_LIMIT

    def is_available(self) -> bool:
        return bool(self._get_api_key())

    def execute(
        self,
        prompt: str,
        working_dir: str | None = None,
        callback: Callable[[str], None] | None = None,
    ) -> AgentResponse:
        is_valid, error = self.validate_prompt(prompt)
        if not is_valid:
            return AgentResponse(success=False, content="", error=error)

        is_safe, error = self._validate_working_dir(working_dir)
        if not is_safe:
            return AgentResponse(success=False, content="", error=error)

        api_key = self._get_api_key()
        if not api_key:
            return AgentResponse(
                success=False,
                content="",
                error="ANTIGRAVITY_API_KEY environment variable not set",
            )

        start_time = time.time()
        url = f"{self._get_base_url().rstrip('/')}/execute"

        payload = {
            "model": self._get_model(),
            "messages": [{"role": "user", "content": prompt}],
            "working_directory": str(working_dir) if working_dir else None,
            "stream": False,
        }

        max_retries = self.config.max_retries
        retry_delay = 1.0

        for attempt in range(max_retries + 1):
            try:
                data = json.dumps(payload).encode("utf-8")
                request = urllib.request.Request(  # noqa: S310
                    url,
                    data=data,
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                        "User-Agent": "Cascade/1.0",
                    },
                    method="POST",
                )

                # Allow custom schemes like https for API calls
                with urllib.request.urlopen(request, timeout=self.config.timeout_seconds) as resp:  # noqa: S310
                    status_code = resp.getcode()
                    raw_response = resp.read().decode("utf-8")

                    if status_code != 200:
                        if attempt < max_retries and status_code in (429, 500, 502, 503, 504):
                            logger.warning(f"API temporary failure ({status_code}). Retrying...")
                            time.sleep(retry_delay)
                            retry_delay *= 2
                            continue

                        return AgentResponse(
                            success=False,
                            content="",
                            error=f"API returned status {status_code}",
                            execution_time_ms=int((time.time() - start_time) * 1000),
                            raw_output=raw_response,
                        )

                    response_data = json.loads(raw_response)
                    execution_time = int((time.time() - start_time) * 1000)

                    return AgentResponse(
                        success=True,
                        content=response_data.get("content", ""),
                        files_modified=response_data.get("files_modified", []),
                        commands_executed=response_data.get("commands_executed", []),
                        token_count=response_data.get("usage", {}).get("total_tokens", 0),
                        execution_time_ms=execution_time,
                        raw_output=raw_response,
                    )

            except urllib.error.HTTPError as e:
                if attempt < max_retries and e.code in (429, 500, 502, 503, 504):
                    time.sleep(retry_delay)
                    retry_delay *= 2
                    continue
                return AgentResponse(
                    success=False,
                    content="",
                    error=f"HTTP Error {e.code}",
                    execution_time_ms=int((time.time() - start_time) * 1000),
                )
            except Exception as e:
                logger.exception("Unexpected error in GeminiApiAgent execution")
                return AgentResponse(
                    success=False,
                    content="",
                    error=f"Unexpected error: {str(e)}",
                    execution_time_ms=int((time.time() - start_time) * 1000),
                )

        return AgentResponse(
            success=False,
            content="",
            error="All execution attempts failed",
        )

    def _get_api_key(self) -> str | None:
        return (
            self.config.environment.get("GEMINI_API_KEY")
            or os.environ.get("GEMINI_API_KEY")
            or self.config.environment.get("ANTIGRAVITY_API_KEY")
            or os.environ.get("ANTIGRAVITY_API_KEY")
        )

    def _get_base_url(self) -> str:
        return (
            os.environ.get("GEMINI_BASE_URL")
            or os.environ.get("ANTIGRAVITY_BASE_URL")
            or self.DEFAULT_BASE_URL
        )

    def _get_model(self) -> str:
        return (
            os.environ.get("GEMINI_MODEL")
            or os.environ.get("ANTIGRAVITY_MODEL")
            or self.DEFAULT_MODEL
        )
