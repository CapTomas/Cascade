"""Tests for agent adapter execution paths."""

import json
import subprocess
from unittest.mock import MagicMock, patch

from cascade.agents.interface import (
    AgentCapability,
    AgentConfig,
)


class TestClaudeCodeAgent:
    """Tests for ClaudeCodeAgent execution paths."""

    def test_agent_name(self):
        """Test agent returns correct name."""
        from cascade.agents import ClaudeCodeAgent

        agent = ClaudeCodeAgent()
        assert agent.get_name() == "claude-cli"

    def test_capabilities(self):
        """Test agent declares correct capabilities."""
        from cascade.agents import ClaudeCodeAgent

        agent = ClaudeCodeAgent()
        caps = agent.get_capabilities()

        assert AgentCapability.FILE_EDIT in caps.capabilities
        assert AgentCapability.COMMAND_EXECUTE in caps.capabilities
        assert AgentCapability.CODE_ANALYSIS in caps.capabilities
        assert caps.supports_streaming is True

    def test_token_limit(self):
        """Test agent returns reasonable token limit."""
        from cascade.agents import ClaudeCodeAgent

        agent = ClaudeCodeAgent()
        limit = agent.get_token_limit()

        assert limit == 200000  # Claude's context window

    def test_is_available_when_installed(self):
        """Test is_available returns True when claude CLI is found."""
        from cascade.agents import ClaudeCodeAgent

        with patch("shutil.which") as mock_which:
            mock_which.return_value = "/usr/local/bin/claude"
            agent = ClaudeCodeAgent()
            # Force re-check by not caching
            assert agent.is_available() is True

    def test_is_available_when_not_installed(self):
        """Test is_available returns False when claude CLI not found."""
        from cascade.agents import ClaudeCodeAgent

        with patch("shutil.which") as mock_which:
            mock_which.return_value = None
            agent = ClaudeCodeAgent()
            assert agent.is_available() is False

    def test_execute_empty_prompt_fails(self):
        """Test that empty prompt returns error."""
        from cascade.agents import ClaudeCodeAgent

        agent = ClaudeCodeAgent()

        response = agent.execute("")
        assert response.success is False
        assert "empty" in response.error.lower()

    def test_execute_invalid_working_dir(self, tmp_path):
        """Test that working_dir outside project root fails."""
        from cascade.agents import ClaudeCodeAgent

        agent = ClaudeCodeAgent()

        # Try to use a directory outside current working dir
        with patch("pathlib.Path.cwd") as mock_cwd:
            mock_cwd.return_value = tmp_path
            response = agent.execute(
                "Test prompt",
                working_dir="/etc",  # Outside project
            )
            assert response.success is False
            assert "Security" in response.error or "outside" in response.error.lower()

    def test_execute_success(self, tmp_path):
        """Test successful execution with mocked subprocess.Popen."""
        from cascade.agents import ClaudeCodeAgent

        mock_process = MagicMock()
        mock_process.poll.return_value = 0
        mock_process.returncode = 0
        mock_process.stdout.readline.side_effect = [
            "Task completed successfully.\n",
            "Modified: src/main.py\n",
            "",
        ]
        mock_process.stdout.read.return_value = ""
        mock_process.stderr.readline.return_value = ""
        mock_process.stderr.read.return_value = ""

        with patch("subprocess.Popen", return_value=mock_process):
            with patch("shutil.which", return_value="/usr/local/bin/claude"):
                with patch("pathlib.Path.cwd", return_value=tmp_path):
                    with patch("select.select", return_value=([mock_process.stdout], [], [])):
                        agent = ClaudeCodeAgent()
                        response = agent.execute("Add a hello function", working_dir=str(tmp_path))

                        assert response.success is True
                        assert "completed" in response.content.lower()

    def test_execute_timeout(self, tmp_path):
        """Test execution timeout handling."""
        from cascade.agents import ClaudeCodeAgent

        mock_process = MagicMock()
        mock_process.poll.return_value = None  # Still running
        mock_process.stdout.readline.return_value = "Thinking...\n"

        # Mock time to simulate timeout
        with patch("subprocess.Popen", return_value=mock_process):
            with patch("shutil.which", return_value="/usr/local/bin/claude"):
                with patch("pathlib.Path.cwd", return_value=tmp_path):
                    with patch("select.select", return_value=([mock_process.stdout], [], [])):
                        with patch(
                            "time.time", side_effect=[0, 0, 1000, 1000, 1000, 1000]
                        ):  # Start, loops, timeout, status calls
                            agent = ClaudeCodeAgent(
                                config=AgentConfig(name="claude-code", timeout_seconds=300)
                            )
                            response = agent.execute("Long task", working_dir=str(tmp_path))

                            assert response.success is False
                            assert "timed out" in response.error.lower()
                            mock_process.kill.assert_called_once()

    def test_execute_cli_error(self, tmp_path):
        """Test CLI error handling."""
        from cascade.agents import ClaudeCodeAgent

        mock_process = MagicMock()
        mock_process.poll.return_value = 1
        mock_process.returncode = 1
        mock_process.stdout.readline.return_value = ""
        mock_process.stdout.read.return_value = ""
        mock_process.stderr.readline.side_effect = ["Error: Invalid API key\n", ""]
        mock_process.stderr.read.return_value = ""

        with patch("subprocess.Popen", return_value=mock_process):
            with patch("shutil.which", return_value="/usr/local/bin/claude"):
                with patch("pathlib.Path.cwd", return_value=tmp_path):
                    with patch("select.select", return_value=([mock_process.stderr], [], [])):
                        agent = ClaudeCodeAgent()
                        response = agent.execute("Test", working_dir=str(tmp_path))

                        assert response.success is False
                        assert "Invalid API key" in response.error


class TestCodexAgent:
    """Tests for CodexAgent execution paths."""

    def test_agent_name(self):
        """Test agent returns correct name."""
        from cascade.agents import CodexAgent

        agent = CodexAgent()
        assert agent.get_name() == "codex-api"

    def test_capabilities(self):
        """Test agent declares correct capabilities."""
        from cascade.agents import CodexAgent

        agent = CodexAgent()
        caps = agent.get_capabilities()

        assert AgentCapability.CODE_ANALYSIS in caps.capabilities
        assert caps.supports_streaming is False

    def test_is_available_without_config(self):
        """Test is_available returns False without API key."""
        from cascade.agents import CodexAgent

        with patch.dict("os.environ", {}, clear=True):
            agent = CodexAgent()
            assert agent.is_available() is False

    def test_is_available_with_config(self):
        """Test is_available returns True with API key and model."""
        from cascade.agents import CodexAgent

        with patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test", "OPENAI_MODEL": "gpt-4"}):
            agent = CodexAgent()
            assert agent.is_available() is True

    def test_execute_without_api_key(self):
        """Test execution fails without API key."""
        from cascade.agents import CodexAgent

        with patch.dict("os.environ", {}, clear=True):
            agent = CodexAgent()
            response = agent.execute("Test prompt")

            assert response.success is False
            assert "OPENAI_API_KEY" in response.error

    def test_execute_api_success(self, tmp_path):
        """Test successful API execution."""
        from cascade.agents import CodexAgent

        mock_response = MagicMock()
        mock_response.getcode.return_value = 200
        mock_response.read.return_value = json.dumps(
            {"output_text": "Here is the solution..."}
        ).encode()
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test", "OPENAI_MODEL": "gpt-4"}):
            with patch("urllib.request.urlopen", return_value=mock_response):
                with patch("pathlib.Path.cwd", return_value=tmp_path):
                    agent = CodexAgent()
                    response = agent.execute("Write a function", working_dir=str(tmp_path))

                    assert response.success is True
                    assert "solution" in response.content.lower()

    def test_execute_api_error(self, tmp_path):
        """Test API error handling."""
        import urllib.error

        from cascade.agents import CodexAgent

        mock_error = urllib.error.HTTPError(
            url="test",
            code=401,
            msg="Unauthorized",
            hdrs={},
            fp=MagicMock(read=lambda: b'{"error": {"message": "Invalid key"}}'),
        )

        with patch.dict("os.environ", {"OPENAI_API_KEY": "sk-invalid", "OPENAI_MODEL": "gpt-4"}):
            with patch("urllib.request.urlopen", side_effect=mock_error):
                with patch("pathlib.Path.cwd", return_value=tmp_path):
                    agent = CodexAgent()
                    response = agent.execute("Test", working_dir=str(tmp_path))

                    assert response.success is False
                    assert "401" in response.error or "Invalid" in response.error


class TestGenericAgent:
    """Tests for GenericAgent execution paths."""

    def test_agent_name(self):
        """Test agent returns correct name."""
        from cascade.agents.generic import GenericAgent

        agent = GenericAgent()
        assert agent.get_name() == "generic"

    def test_is_available_without_command(self):
        """Test is_available returns False without command configured."""
        from cascade.agents.generic import GenericAgent

        with patch.dict("os.environ", {}, clear=True):
            agent = GenericAgent()
            assert agent.is_available() is False

    def test_is_available_with_command(self):
        """Test is_available returns True with command configured."""
        from cascade.agents.generic import GenericAgent

        with patch.dict("os.environ", {"CASCADE_GENERIC_AGENT_CMD": "echo"}):
            agent = GenericAgent()
            assert agent.is_available() is True

    def test_execute_without_command(self):
        """Test execution fails without command configured."""
        from cascade.agents.generic import GenericAgent

        with patch.dict("os.environ", {}, clear=True):
            agent = GenericAgent()
            response = agent.execute("Test prompt")

            assert response.success is False
            assert "CASCADE_GENERIC_AGENT_CMD" in response.error

    def test_execute_success(self, tmp_path):
        """Test successful command execution."""
        from cascade.agents.generic import GenericAgent

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "Command output"
        mock_result.stderr = ""

        with patch.dict("os.environ", {"CASCADE_GENERIC_AGENT_CMD": "echo"}):
            with patch("subprocess.run", return_value=mock_result):
                with patch("pathlib.Path.cwd", return_value=tmp_path):
                    agent = GenericAgent()
                    response = agent.execute("Test", working_dir=str(tmp_path))

                    assert response.success is True
                    assert response.content == "Command output"

    def test_execute_command_failure(self, tmp_path):
        """Test command failure handling."""
        from cascade.agents.generic import GenericAgent

        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_result.stderr = "Command failed"

        with patch.dict("os.environ", {"CASCADE_GENERIC_AGENT_CMD": "failing-cmd"}):
            with patch("subprocess.run", return_value=mock_result):
                with patch("pathlib.Path.cwd", return_value=tmp_path):
                    agent = GenericAgent()
                    response = agent.execute("Test", working_dir=str(tmp_path))

                    assert response.success is False
                    assert "Command failed" in response.error

    def test_execute_timeout(self, tmp_path):
        """Test command timeout handling."""
        from cascade.agents.generic import GenericAgent

        with patch.dict("os.environ", {"CASCADE_GENERIC_AGENT_CMD": "sleep"}):
            with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("cmd", 60)):
                with patch("pathlib.Path.cwd", return_value=tmp_path):
                    agent = GenericAgent()
                    response = agent.execute("Long running", working_dir=str(tmp_path))

                    assert response.success is False
                    assert "timed out" in response.error.lower()


class TestAgentInterface:
    """Tests for the AgentInterface abstract class."""

    def test_validate_prompt_empty(self):
        """Test that empty prompts are rejected."""
        from cascade.agents.manual import ManualAgent  # Concrete implementation

        agent = ManualAgent()
        is_valid, error = agent.validate_prompt("")

        assert is_valid is False
        assert "empty" in error.lower()

    def test_validate_prompt_whitespace(self):
        """Test that whitespace-only prompts are rejected."""
        from cascade.agents.manual import ManualAgent

        agent = ManualAgent()
        is_valid, error = agent.validate_prompt("   \n\t  ")

        assert is_valid is False
        assert "empty" in error.lower()

    def test_validate_prompt_too_long(self):
        """Test that overly long prompts are rejected."""
        from cascade.agents import ClaudeCodeAgent

        agent = ClaudeCodeAgent()
        # ClaudeCodeAgent has 200000 token limit, so 30% is 60k tokens
        # At ~4 chars per token, we need ~240k+ chars to exceed
        huge_prompt = "x" * 250000  # Definitely exceeds 30% of token limit
        is_valid, error = agent.validate_prompt(huge_prompt)

        assert is_valid is False
        assert "too long" in error.lower()

    def test_validate_working_dir_safe(self, tmp_path):
        """Test that working dir within project is allowed."""
        from cascade.agents.manual import ManualAgent

        with patch("pathlib.Path.cwd", return_value=tmp_path):
            agent = ManualAgent()
            subdir = tmp_path / "subdir"
            subdir.mkdir()

            is_valid, error = agent._validate_working_dir(str(subdir))

            assert is_valid is True
            assert error is None

    def test_validate_working_dir_outside_project(self, tmp_path):
        """Test that working dir outside project is rejected."""
        from cascade.agents.manual import ManualAgent

        with patch("pathlib.Path.cwd", return_value=tmp_path):
            agent = ManualAgent()

            is_valid, error = agent._validate_working_dir("/etc")

            assert is_valid is False
            assert "Security" in error

    def test_validate_working_dir_none(self):
        """Test that None working dir is allowed."""
        from cascade.agents.manual import ManualAgent

        agent = ManualAgent()
        is_valid, error = agent._validate_working_dir(None)

        assert is_valid is True
        assert error is None
