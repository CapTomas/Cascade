# Getting Started with Cascade

Cascade is a human-directed AI development orchestration system. This guide will help you set up and start your first project.

## Prerequisites

- Python 3.10 or higher
- Access to an AI agent (Claude Code, OpenAI, etc.)

## Installation

```bash
pip install cascade-ai
```

## 1. Initialize Your Project

Create a new directory for your project and initialize Cascade:

```bash
mkdir my-new-app
cd my-new-app
cascade init "Build a modern inventory management system with FastAPI"
```

This will:
1. Create a `.cascade/` directory for metadata.
2. Initialize a local SQLite database for tickets.
3. Analyze your requirements and generate an initial set of topics and tickets.

## 2. Configure Your Agent

By default, Cascade uses a generic agent. You can configure it to use your preferred agent:

```bash
# Set default agent
cascade config set agent.default claude-code

# Check available agents
cascade agents list
```

## 3. Understand Your Project Status

Check what Cascade has planned for you:

```bash
cascade status
```

This dashboard shows your progress, ready tickets, and system health.

## 4. Work on Tickets

Cascade follows a strict ticket-based workflow:

1. **List ready tickets**: `cascade ticket list --status ready`
2. **Review a ticket**: `cascade ticket show 1`
3. **Execute execution**: `cascade ticket execute 1`

During execution, Cascade will:
- Prepare the necessary context.
- Ask for your confirmation before calling the agent.
- Run quality gates (tests, linting) after the agent finishes.

## 5. Next Steps

- Explore [managing tickets](tickets.md)
- Learn about [quality gates](quality-gates.md)
- Understand the [knowledge system](knowledge.md)
