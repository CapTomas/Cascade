# Configuration

Cascade project configuration is stored in `.cascade/config.yaml`. This file is created automatically when you run `cascade init`.

## Complete Configuration Reference

Below is a complete configuration file with all available options:

```yaml
# Project Information
project:
  name: "My Project"
  description: "A brief description of the project"
  tech_stack: ["python", "fastapi", "postgresql"]

# Agent Configuration
agent:
  # Default agent for ticket execution
  # Options: claude-code, antigravity, codex, generic, manual
  default: claude-code

  # Fallback agent if default is unavailable
  fallback: manual

# Context Settings
context:
  # Starting context mode: minimal, standard, or full
  default_mode: minimal

  # Token limits per mode
  max_tokens:
    minimal: 2000      # Ticket + conventions only
    standard: 5000     # + patterns + ADRs
    full: 10000        # + similar tickets

# Quality Gates
quality_gates:
  static_analysis:
    enabled: true
    fail_on_error: true
    tools:
      python:
        linter: "ruff"
        type_checker: "mypy"
      typescript:
        linter: "eslint"
        type_checker: "tsc"

  unit_tests:
    enabled: true
    fail_on_error: true
    min_coverage: 80        # Optional coverage threshold
    command: "pytest"       # Or "npm test" for JS projects

  security_scan:
    enabled: true
    fail_on_critical: true
    fail_on_high: false
    tools:
      python: ["bandit", "safety"]
      typescript: ["npm audit"]

# Constraints
constraints:
  max_gate_retries: 3       # Max retries per quality gate
  max_open_tickets: 100     # Maximum open tickets
  max_blocking_depth: 3     # Maximum dependency chain depth

# Logging
logging:
  level: "INFO"             # DEBUG, INFO, WARNING, ERROR
  file: ".cascade/logs/cascade.log"
```

## Agent-Specific Environment Variables

Each agent requires specific environment variables for authentication:

### Antigravity
```bash
export ANTIGRAVITY_API_KEY="your-api-key"

# Optional overrides
export ANTIGRAVITY_BASE_URL="https://api.antigravity.ai/v1"
export ANTIGRAVITY_MODEL="antigravity-pro-1"
```

### Claude Code
```bash
# No environment variables needed - uses claude CLI
# Make sure to run: claude login
```

### Codex (OpenAI)
```bash
export OPENAI_API_KEY="sk-your-api-key"
export OPENAI_MODEL="gpt-4"  # Required - no default

# Optional override
export OPENAI_BASE_URL="https://api.openai.com/v1"
```

### Generic Agent
```bash
export CASCADE_GENERIC_AGENT_CMD="python /path/to/my_agent.py"
```

### Manual Agent
No environment variables needed. The manual agent prompts you to copy/paste prompts to your preferred AI interface.

## CLI Configuration Commands

### View Configuration
```bash
# Show entire configuration
cascade config show

# Get a specific value
cascade config get agent.default
cascade config get quality_gates.unit_tests.enabled
```

### Update Configuration
```bash
# Set the default agent
cascade config set agent.default antigravity

# Enable/disable quality gates
cascade config set quality_gates.static_analysis.enabled false

# Set token limits
cascade config set context.max_tokens.minimal 3000
```

## Configuration Precedence

Configuration values are resolved in this order (highest priority first):

1. **Command-line flags** (e.g., `--agent antigravity`)
2. **Environment variables** (for agent credentials)
3. **Project config** (`.cascade/config.yaml`)
4. **Default values** (built into Cascade)

## Validation

Cascade validates your configuration on startup. Common validation errors:

- **Unknown agent**: The specified agent name doesn't match any known agent
- **Missing required fields**: `project.name` and `project.tech_stack` are required
- **Invalid enum values**: Status, severity, and mode values must match allowed options

Run `cascade status --health` to verify your configuration is valid.
