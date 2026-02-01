# Cascade 🌊

[![CI](https://github.com/cascade-ai/cascade/actions/workflows/ci.yml/badge.svg)](https://github.com/cascade-ai/cascade/actions/workflows/ci.yml)
[![PyPI version](https://badge.fury.io/py/cascade-ai.svg)](https://badge.fury.io/py/cascade-ai)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**Human-Directed AI Development Orchestration System**

Cascade is a production-grade, agent-agnostic development orchestration system designed to bridge the gap between AI capabilities and professional software engineering standards. It provides persistent project memory, enforces quality standards through configurable quality gates, and structures AI-assisted development while keeping humans in complete control of every decision.

---

## Table of Contents

- [Overview](#overview)
- [Key Features](#key-features)
- [Requirements](#requirements)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Core Concepts](#core-concepts)
- [Command Reference](#command-reference)
- [Agent Configuration](#agent-configuration)
- [Quality Gates](#quality-gates)
- [Knowledge System](#knowledge-system)
- [Project Structure](#project-structure)
- [Development](#development)
- [Contributing](#contributing)
- [License](#license)

---

## Overview

Unlike autonomous AI agents that may produce inconsistent results or drift from project requirements, Cascade operates on the principle of **"AI assists, human directs"**. Every code change is intentional, verified, and documented through a structured ticket-based workflow.

Cascade acts as an orchestration layer between developers and AI agents. It manages context, enforces quality standards, and maintains institutional knowledge across development sessions.

### How It Works

```
+----------+     +-------------+     +-----------------+     +-------------+
|  User    | --> | Cascade CLI | --> | Ticket Executor | --> |  AI Agent   |
+----------+     +-------------+     +-----------------+     +-------------+
                                            |                       |
                                            v                       v
                                    +---------------+       +---------------+
                                    | Context       |       | Proposed      |
                                    | Builder       |       | Changes       |
                                    +---------------+       +-------+-------+
                                                                    |
                                                                    v
                                                           +----------------+
                                                           | Quality Gates  |
                                                           +-------+--------+
                                                                   |
                                            +----------------------+----------------------+
                                            |                                             |
                                            v                                             v
                                    +---------------+                             +---------------+
                                    | Pass: Commit  |                             | Fail: Escalate|
                                    | & Mark Done   |                             | Context Mode  |
                                    +---------------+                             +---------------+
```

---

## Key Features

### Agent Agnostic Architecture

Cascade supports multiple AI agents through a unified interface:

- **Claude**: Anthropic's models via CLI or API
- **Gemini**: Google's models via CLI or API (formerly Antigravity)
- **Codex**: OpenAI's code-focused models via CLI or API
- **Generic Agent**: Interface for custom or unsupported agents
- **Manual Agent**: Human-in-the-loop mode for copy-paste workflows

### Ticket-Based Workflow

Development is structured into discrete, manageable tickets with:

- Hierarchical organization (Epics, Stories, Tasks)
- Clear acceptance criteria
- Dependency tracking
- Status lifecycle management (DEFINED, READY, IN_PROGRESS, BLOCKED, TESTING, DONE, ABANDONED)
- Priority scoring and severity levels

### Intelligent Context Management

Context is built and managed across three escalation levels:

| Mode     | Contents                                   | Use Case                     |
|----------|--------------------------------------------|-----------------------------|
| Minimal  | Conventions, related patterns              | Standard tasks              |
| Standard | Minimal + related files, ADRs             | Complex tasks               |
| Full     | Complete codebase context                  | System-wide changes         |

The executor automatically escalates context when quality gates fail, providing agents with more information for retry attempts.

### Quality Gate Framework

Mandatory verification before any ticket completion:

- **Static Analysis**: Linting and type checking (Ruff, MyPy, ESLint)
- **Unit Tests**: Test execution with optional coverage thresholds
- **Security Scans**: Vulnerability detection (Bandit, npm audit, Trivy)

### Knowledge Persistence

Automatic extraction and management of institutional knowledge:

- **Architecture Decision Records (ADRs)**: Track design decisions with context and rationale
- **Code Patterns**: Reusable templates learned from successful implementations
- **Conventions**: Project-wide coding standards and practices

### Proactive Discovery & Auto-Ticket Creation

AI doesn't just complete tasks - it **actively discovers** and **creates tickets** for follow-up work:

- **🔍 Active Discovery**: While working, AI identifies bugs, security issues, tech debt, and improvements
- **📝 Automatic Ticketing**: Discovered work is automatically converted into categorized, prioritized tickets
- **🎯 Smart Categorization**: Auto-inferred ticket types (BUG, SECURITY, TEST, DOC, TASK) and severity
- **🔗 Contextual Linking**: Created tickets link back to parent ticket for full traceability
- **🧠 Self-Improving Backlog**: Your backlog grows organically with real, discovered issues

**Example**: AI fixes a login bug and auto-creates tickets for:
- Similar validation missing in signup (BUG, HIGH)
- Missing rate limiting on auth endpoints (SECURITY, CRITICAL)
- Integration tests needed for OAuth flow (TEST, MEDIUM)
- Outdated API authentication docs (DOC, MEDIUM)

See [AUTO_TICKET_CREATION.md](AUTO_TICKET_CREATION.md) for details.

---

### Metrics & Analytics

Built-in dashboard for tracking project health:

- **Execution Metrics**: Token usage, cost, and agent performance
- **Ticket Analytics**: Velocity, effort accuracy, and status breakdown
- **Quality Insights**: Pass/fail rates for quality gates

### Git Integration

Seamless version control integration:

- **Automatic Branching**: Creates `ticket-{id}-{title}` branches automatically
- **Automatic Commits**: Commits changes upon ticket completion
- **Safety Checks**: Verifies clean working tree before execution

### Multi-Agent Orchestration

Assign different agents to specific types of work:

- Use **Claude Code** for complex Logic
- Use **Codex** for unit tests
- Use **Generic Agents** for documentation or specialized tasks

---

## Requirements

- Python 3.10 or higher
- SQLite (bundled with Python)
- Access to at least one supported AI agent

### Optional Dependencies

- `ruff` for static analysis quality gates
- `pytest` for unit test quality gates
- `bandit` for Python security scanning

---

## Installation

### From PyPI

```bash
pip install cascade-ai
```

### From Source

```bash
git clone https://github.com/cascade-ai/cascade.git
cd cascade
pip install -e ".[dev]"
```

### Verify Installation

```bash
cascade --version
```

The short alias `ccd` is also available for all commands.

---

## Quick Start

### 1. Initialize a Project

```bash
cd your-project-directory
cascade init "Build a REST API for inventory management"
# OR
cascade init ./requirements.txt
```

This command:

1. Creates the `.cascade/` directory for metadata and database
2. Initializes the SQLite database with the project schema
3. Optionally generates an initial set of topics and tickets based on your description

### 2. Check Project Status

```bash
cascade status
```

The status dashboard displays:

- Project overview and health metrics
- Ticket counts by status
- Knowledge base statistics
- Configured agent information

### 3. Configure Your Agent

```bash
# View available agents
cascade agents list

# Set the default agent
cascade config set agent.default claude-code
```

### 4. Create and Execute Tickets

```bash
# Create a new ticket
cascade ticket create "Implement user authentication endpoint" --type task

# List ready tickets
cascade ticket list --status ready

# View ticket details
cascade ticket show 1

# Execute a ticket
cascade ticket execute 1
```

### 5. Manage Knowledge

```bash
# View pending knowledge items
cascade knowledge pending

# Approve or reject proposed patterns
cascade knowledge approve pattern 1
cascade knowledge reject adr 2 --reason "Superseded by newer approach"
```

---

## Core Concepts

### Tickets

Tickets are the fundamental unit of work in Cascade. Each ticket represents a focused, atomic task for an AI agent to complete.

**Ticket Types:**

| Type     | Description                                      |
|----------|--------------------------------------------------|
| EPIC     | Large feature or initiative containing stories   |
| STORY    | User-facing functionality containing tasks       |
| TASK     | Single implementation unit                       |
| BUG      | Defect requiring investigation and fix           |
| SECURITY | Security vulnerability or hardening task         |
| TEST     | Test coverage expansion                          |
| DOC      | Documentation update                             |

**Ticket Lifecycle:**

```
DEFINED --> READY --> IN_PROGRESS --> TESTING --> DONE
                          |              |
                          v              v
                       BLOCKED      ABANDONED
```

### Topics

Topics provide organizational grouping for related tickets. Examples include "Authentication", "Database", or "API Layer".

### Context Modes

- **MINIMAL**: Includes only conventions and directly relevant patterns. Suitable for isolated, well-defined tasks.
- **STANDARD**: Adds related files and ADRs. Used when tasks require broader awareness.
- **FULL**: Includes comprehensive project context. Reserved for architectural changes.

---

## Command Reference

### Project Commands

| Command                 | Description                              |
|-------------------------|------------------------------------------|
| `cascade init <desc>`   | Initialize a new Cascade project         |
| `cascade init <file>`   | Initialize project from requirements file|
| `cascade destroy`       | Uninitialize project (destructive)       |
| `cascade status`        | Display project dashboard                |
| `cascade config show`   | View current configuration               |
| `cascade config set`    | Update configuration value               |

### Ticket Commands

| Command                        | Description                        |
|--------------------------------|------------------------------------|
| `cascade ticket list`          | List all tickets                   |
| `cascade ticket show <id>`     | Display ticket details             |
| `cascade ticket create <title>`| Create a new ticket                |
| `cascade ticket execute <id>`  | Execute a ticket with AI agent     |
| `cascade next`                 | Execute the next ready ticket      |

### Topic Commands

| Command                         | Description                       |
|---------------------------------|-----------------------------------|
| `cascade topic list`            | List all topics                   |
| `cascade topic create <name>`   | Create a new topic                |

### Knowledge Commands

| Command                                | Description                    |
|----------------------------------------|--------------------------------|
| `cascade knowledge pending`            | View pending knowledge items   |
| `cascade knowledge approve <type> <id>`| Approve a knowledge item       |
| `cascade knowledge reject <type> <id>` | Reject a knowledge item        |
| `cascade knowledge conventions`        | List all conventions           |

### Agent Commands

| Command                      | Description                        |
|------------------------------|------------------------------------|
| `cascade agents list`        | List available agents              |
| `cascade agents show <name>` | Display agent details              |

### Git Commands

| Command                      | Description                        |
|------------------------------|------------------------------------|
| `cascade git status`         | Show repository status             |
| `cascade git branch [name]`  | Create or list branches            |
| `cascade git diff`           | Show changes                       |
| `cascade git commit -m <msg>`| Create a commit                    |

### Metrics Commands

| Command                      | Description                        |
|------------------------------|------------------------------------|
| `cascade metrics`            | Show project overview              |
| `cascade metrics --tickets`  | Detailed ticket analytics          |
| `cascade metrics --quality`  | Quality gate performance           |
| `cascade metrics --activity` | Daily activity log                 |

### Settings Commands

| Command                            | Description                             |
|------------------------------------|-----------------------------------------|
| `cascade settings show`            | Display all configurable settings       |
| `cascade settings agents`          | Configure agent assignments             |
| `cascade settings prompts`         | Configure AI prompts                    |
| `cascade settings quality-gates`   | Configure quality gate settings         |
| `cascade settings edit-config`     | Open config.yaml in editor              |

---

## Sophisticated Prompting System

**New in v2.0**: Cascade features a sophisticated, type-aware prompting system that tailors AI instructions based on ticket type and provides structured response formats for better tracking and knowledge extraction.

### Type-Specific Prompts

Each ticket type (BUG, STORY, TASK, TEST, SECURITY, DOC, EPIC) has optimized prompts that guide the AI agent to:

- **BUG**: Focus on root cause analysis, minimal fixes, and regression tests
- **STORY**: Prioritize user value, acceptance criteria, and UX consistency
- **TASK**: Emphasize clean implementation and following project patterns
- **TEST**: Maximize meaningful coverage, edge cases, and test clarity
- **SECURITY**: Ensure thorough vulnerability elimination and system-wide checking
- **DOC**: Verify technical accuracy and provide clear, practical examples
- **EPIC**: Consider architectural decisions and suggest breakdowns if needed

### Structured Response Format

AI agents are instructed to provide structured responses with:

```xml
<execution_summary>
ROOT_CAUSE: (for BUGs) Brief explanation of what caused the bug
FIX_APPROACH: How you fixed it
FILES_MODIFIED: List of changed files
TESTS_ADDED: Tests added/updated
TICKET_STATUS: COMPLETE | BLOCKED | NEEDS_BREAKDOWN
BLOCKERS: (If BLOCKED) What prevents completion
NEW_TICKETS_NEEDED: (Optional) Related work discovered
</execution_summary>
```

This structured format enables:
- Automatic ticket status tracking
- Knowledge extraction from completed work
- Better visibility into what was accomplished
- Identification of blockers and follow-up work

### Configurable Prompts

All prompts are fully configurable via the `cascade settings` command:

```bash
# Configure prompts interactively
cascade settings prompts

# Configure prompts for specific ticket type
cascade settings prompts --ticket-type bug

# Configure the 'next' command prompt
cascade settings prompts --next

# Reset all prompts to optimized defaults
cascade settings prompts --reset
```

Customize:
- **Task Focus**: The objective/goal statement for each ticket type
- **Instructions**: Step-by-step guidance tailored to the ticket type
- **Response Format**: Expected output structure
- **Next Command**: Prompt used by `cascade next` to suggest tickets

### Agent Orchestration

Assign different AI agents to specific ticket types or commands:

```bash
cascade settings agents
```

This allows you to:
- Use Claude Code for complex logic tasks
- Use Codex for test writing
- Use Gemini for documentation
- Configure a specific agent for the `cascade next` command

Configuration is stored in `.cascade/config.yaml`:

```yaml
agent:
  default: claude-code
  next_command_agent: gemini-cli  # Optional: override for 'next' command
  orchestration:
    bug: codex-api
    test: codex-api
    doc: generic
    story: claude-cli
```

---

## Agent Configuration

New in version 1.0: Cascade supports both CLI and API modes for major providers.

### Anthropic (Claude)

**Mode: CLI (Default)**
Wraps the `claude` CLI tool. Best for development workflows with full tool access.

```bash
# Set mode to CLI
cascade config set agent.configurations.claude.mode cli
```

**Mode: API**
Uses Anthropic API directly. Best for automated tasks or CI/CD.

```bash
# Set mode to API
cascade config set agent.configurations.claude.mode api
export ANTHROPIC_API_KEY=sk-...
```

### Google (Gemini)

**Mode: API (Default)**
Uses Google Generative AI API (formerly Antigravity).

```bash
cascade config set agent.configurations.google.mode api
export ANTIGRAVITY_API_KEY=...
```

**Mode: CLI**
Wraps the `gemini` CLI tool.

```bash
cascade config set agent.configurations.google.mode cli
```

### OpenAI (Codex)

**Mode: API (Default)**
Uses OpenAI API.

```bash
cascade config set agent.configurations.openai.mode api
export OPENAI_API_KEY=sk-...
```

**Mode: CLI**
Wraps the `codex` CLI.

```bash
cascade config set agent.configurations.openai.mode cli
```

### Generic Agent

For custom agents or unsupported systems.

**Environment Variables:**

| Variable                     | Description                              |
|------------------------------|------------------------------------------|
| `CASCADE_GENERIC_AGENT_CMD`  | Command to invoke the agent              |

### Manual Agent

No configuration required. Prompts are copied to clipboard for manual execution with any AI service.

### Multi-Agent Orchestration

Configure different agents for specific ticket types in `.cascade/config.yaml`:

```yaml
agent:
  default: claude-cli
  next_command_agent: gemini-cli  # Optional: specific agent for 'cascade next'
  orchestration:
    bug: codex-api      # Use Codex for bugs
    test: codex-api     # Use Codex for tests
    doc: generic        # Use generic agent for docs
    story: claude-cli   # Use Claude for stories
```

### Prompt Customization

Configure AI prompts in `.cascade/config.yaml`:

```yaml
prompts:
  enabled: true  # Use custom prompts
  include_knowledge_extraction: true  # Include knowledge proposal format

  # Custom prompt for 'next' command
  next_command_prompt: |
    You are a technical project manager...

  # Custom prompts per ticket type
  task_focus:
    BUG: "Custom bug-fixing focus..."

  instructions:
    TEST:
      - "Custom test instruction 1"
      - "Custom test instruction 2"

  response_format:
    STORY: |
      <execution_summary>
      Custom format for stories...
      </execution_summary>
```

Use `cascade settings` for interactive configuration instead of manual YAML editing.

---

## Quality Gates

Quality gates are configurable verification steps that run after each agent execution. Configure them in `.cascade/config.yaml`:

```yaml
quality_gates:
  static_analysis:
    enabled: true
    tools:
      ruff: "ruff check ."
      mypy: "mypy ."

  unit_tests:
    enabled: true
    command: "pytest tests/ -v"
    min_coverage: 80

  security:
    enabled: true
    fail_on_critical: true
    fail_on_high: false
```

### Gate Behavior

When a gate fails:

1. The executor logs the failure with full output
2. Context is escalated to the next level (Minimal -> Standard -> Full)
3. The agent is retried with additional context
4. If all escalation levels fail, the ticket is marked as blocked

---

## Knowledge System

### Architecture Decision Records (ADRs)

ADRs document significant technical decisions with full context:

```markdown
# ADR-001: Use SQLite for Local Storage

## Status
Approved

## Context
Cascade requires persistent storage for tickets, knowledge, and configuration.

## Decision
Use SQLite as the embedded database.

## Rationale
- Zero configuration required
- No external dependencies
- Portable across platforms
- Sufficient for single-user scenarios

## Consequences
- Limited concurrent write performance
- Local storage only (no distributed deployment)
```

### Patterns

Patterns capture reusable code structures learned from successful implementations. They are proposed by the knowledge extractor and require human approval before becoming part of the project context.

### Conventions

Conventions define project-wide standards that are always included in agent context:

```yaml
conventions:
  - category: Naming
    key: Variable Naming
    value: Use snake_case for variables and functions

  - category: Error Handling
    key: Exception Types
    value: Define custom exceptions in core/exceptions.py
```

---

## Project Structure

```
cascade/
├── agents/              # AI agent implementations
│   ├── interface.py     # Abstract agent interface
│   ├── claude_code.py   # Claude Code CLI integration
│   ├── codex.py         # OpenAI Codex integration
│   ├── antigravity.py   # Antigravity agent
│   ├── generic.py       # Generic stdin/stdout agent
│   ├── manual.py        # Human copy-paste agent
│   └── registry.py      # Agent discovery and registration
├── cli/                 # Command-line interface
│   ├── main.py          # Entry point and error handling
│   ├── styles.py        # Rich styling utilities
│   └── commands/        # Subcommand implementations
├── core/                # Business logic
│   ├── context_builder.py    # Context assembly
│   ├── executor.py           # Ticket execution engine
│   ├── knowledge_base.py     # Knowledge CRUD operations
│   ├── knowledge_extractor.py # Pattern/ADR extraction
│   ├── planner.py            # Requirements planning
│   ├── prompt_builder.py     # AI prompt construction
│   ├── quality_gates.py      # Verification framework
│   ├── ticket_manager.py     # Ticket operations
│   └── topic_manager.py      # Topic operations
├── models/              # Data models (Pydantic/dataclass)
├── storage/             # Database layer
│   ├── database.py      # SQLite connection management
│   └── schemas.sql      # Database schema
└── utils/               # Utilities
    ├── logger.py        # Centralized logging
    └── tokens.py        # Token estimation
```

---

## Development

### Setting Up Development Environment

```bash
# Clone the repository
git clone https://github.com/cascade-ai/cascade.git
cd cascade

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install with development dependencies
pip install -e ".[dev]"
```

### Running Tests

```bash
# Run full test suite with coverage
pytest tests/ -v --cov=cascade --cov-report=term-missing

# Run specific test file
pytest tests/test_executor.py -v

# Run tests matching pattern
pytest tests/ -k "test_agent" -v
```

### Code Quality

```bash
# Run linter
ruff check cascade/ tests/

# Run type checker
mypy cascade/

# Auto-format code
ruff format cascade/ tests/
```

### Building Documentation

```bash
# Documentation is in docs/ directory
# View locally with any markdown viewer
```

---

## Contributing

Contributions are welcome. Please read the [Contributing Guidelines](CONTRIBUTING.md) before submitting a pull request.

### Development Workflow

1. Fork the repository
2. Create a feature branch from `main`
3. Make your changes with tests
4. Ensure all tests pass and code quality checks succeed
5. Submit a pull request with a clear description

### Code Standards

- Follow existing code style and conventions
- Write comprehensive docstrings for public interfaces
- Include unit tests for new functionality
- Update documentation for user-facing changes

---

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for the full license text.

---

## Acknowledgments

Cascade is designed to work with AI agents from various providers. The project is independent and not affiliated with Anthropic, OpenAI, or any other AI service provider.
