import json
import os
import time
import urllib.request
import urllib.error
from typing import Optional

from cascade.agents.interface import (
    AgentInterface,
    AgentCapabilities,
    AgentCapability,
    AgentResponse,
    AgentConfig,
)
from cascade.utils.logger import get_logger

logger = get_logger(__name__)


class AntigravityAgent(AgentInterface):
    """
    Antigravity agent implementation.

    This agent integrates with the Antigravity AI platform via its REST API.
    It is a high-capability agent optimized for complex software engineering
    tasks, including multi-file edits and terminal interactions.

    Configuration:
    - ANTIGRAVITY_API_KEY: required
    - ANTIGRAVITY_BASE_URL: optional (default https://api.antigravity.ai/v1)
    - ANTIGRAVITY_MODEL: optional (default 'antigravity-pro-1')
    """

    DEFAULT_BASE_URL = "https://api.antigravity.ai/v1"
    DEFAULT_MODEL = "antigravity-pro-1"
    DEFAULT_TOKEN_LIMIT = 1000000

    def __init__(self, config: Optional[AgentConfig] = None):
        """
        Initialize Antigravity agent.

        Args:
            config: Agent configuration
        """
        super().__init__(config)

    def get_name(self) -> str:
        """Return agent identifier."""
        return "antigravity"

    def get_capabilities(self) -> AgentCapabilities:
        """Return Antigravity capabilities."""
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
        """Return Antigravity's context window size."""
        return self.DEFAULT_TOKEN_LIMIT

    def is_available(self) -> bool:
        """Check if API key is configured."""
        return bool(self._get_api_key())

    def execute(
        self,
        prompt: str,
        working_dir: Optional[str] = None,
        callback: Optional[callable] = None,
    ) -> AgentResponse:
        """
        Execute prompt via Antigravity API.

        Args:
            prompt: The prompt to execute
            working_dir: Working directory for the command
            callback: Optional callback for streaming partial results

        Returns:
            AgentResponse with execution results
        """
        # Validate
        is_valid, error = self.validate_prompt(prompt)
        if not is_valid:
            return AgentResponse(success=False, content="", error=error)

        # Validate working directory
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
            "stream": False,  # Simplified for this implementation
        }

        max_retries = self.config.max_retries
        retry_delay = 1.0

        for attempt in range(max_retries + 1):
            try:
                data = json.dumps(payload).encode("utf-8")
                request = urllib.request.Request(
                    url,
                    data=data,
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                        "User-Agent": "Cascade/1.0",
                    },
                    method="POST",
                )

                with urllib.request.urlopen(request, timeout=self.config.timeout_seconds) as resp:
                    status_code = resp.getcode()
                    raw_response = resp.read().decode("utf-8")

                    if status_code != 200:
                        if attempt < max_retries and status_code in (429, 500, 502, 503, 504):
                            logger.warning(f"Antigravity API temporary failure ({status_code}). Retrying in {retry_delay}s...")
                            time.sleep(retry_delay)
                            retry_delay *= 2
                            continue

                        try:
                            error_details = json.loads(raw_response).get("error", raw_response)
                        except Exception:
                            error_details = raw_response

                        return AgentResponse(
                            success=False,
                            content="",
                            error=f"API returned status {status_code}: {error_details}",
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
                error_body = e.read().decode("utf-8")
                return AgentResponse(
                    success=False,
                    content="",
                    error=f"HTTP Error {e.code}: {error_body}",
                    execution_time_ms=int((time.time() - start_time) * 1000),
                )
            except (urllib.error.URLError, TimeoutError) as e:
                if attempt < max_retries:
                    time.sleep(retry_delay)
                    retry_delay *= 2
                    continue
                return AgentResponse(
                    success=False,
                    content="",
                    error=f"Network Error: {str(e)}",
                    execution_time_ms=int((time.time() - start_time) * 1000),
                )
            except Exception as e:
                logger.exception("Unexpected error in AntigravityAgent execution")
                return AgentResponse(
                    success=False,
                    content="",
                    error=f"Unexpected error: {str(e)}",
                    execution_time_ms=int((time.time() - start_time) * 1000),
                )

    def _get_api_key(self) -> Optional[str]:
        """Get API key from config or environment."""
        return self.config.environment.get("ANTIGRAVITY_API_KEY") or os.environ.get("ANTIGRAVITY_API_KEY")

    def _get_base_url(self) -> str:
        """Get base URL from environment or default."""
        return os.environ.get("ANTIGRAVITY_BASE_URL", self.DEFAULT_BASE_URL)

    def _get_model(self) -> str:
        """Get model from environment or default."""
        return os.environ.get("ANTIGRAVITY_MODEL", self.DEFAULT_MODEL)
