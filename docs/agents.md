# Agents

Cascade supports multiple AI agents through a common interface. Each agent has different setup requirements and capabilities.

## Supported Agents

### Antigravity (`antigravity`)
The high-capability Antigravity AI service. Optimized for complex software engineering tasks.

**Setup:**
- Requires `ANTIGRAVITY_API_KEY` environment variable.
- Optional `ANTIGRAVITY_BASE_URL` (defaults to `https://api.antigravity.ai/v1`).
- Optional `ANTIGRAVITY_MODEL` (defaults to `antigravity-pro-1`).

### Claude Code (`claude-code`)
Anthropic's Claude Code CLI. This agent wraps the local `claude` command.

**Setup:**
- Requires the `claude` CLI tool to be installed and available in your `PATH`.
- Authenticate via `claude login`.

> [!WARNING]
> Cascade uses the `--dangerously-skip-permissions` flag when calling Claude Code. This is necessary for automation but means Claude can execute tools without per-action confirmation. Cascade mitigates this by enforcing strict directory boundaries (preventing operations outside the project root).

### Codex (`codex`)
OpenAI's models via API.

**Setup:**
- Requires `OPENAI_API_KEY` and `OPENAI_MODEL` environment variables.
- Optional `OPENAI_BASE_URL` (defaults to `https://api.openai.com/v1`).

### Generic (`generic`)
A generic stdin/stdout interface for custom agents.

**Setup:**
- Requires `CASCADE_GENERIC_AGENT_CMD` environment variable (e.g., `python my_agent.py`).

### Manual (`manual`)
The bridge between Cascade and your web-based AI subscriptions (ChatGPT Plus, Claude Pro, Gemini Advanced).

**Setup:**
- No environment variables required.
- Requires a human to copy-paste prompts and responses.
- Automatically uses `pbcopy` (macOS) or `xclip`/`xsel` (Linux) if available.

## Configuration

You can set the default agent in your project configuration:

```bash
cascade config set agent.default antigravity
```

View available agents and their status:

```bash
cascade agents list
cascade agents show antigravity
```

## Capabilities

Each agent has different capabilities:

- `file_read`: Read file contents
- `file_write`: Write new files
- `file_edit`: Modify existing files
- `command_execute`: Run shell commands
- `web_search`: Search the web
- `code_analysis`: Analyze codebase
