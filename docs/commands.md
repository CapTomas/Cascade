# Cascade CLI Command Reference

This document provides a comprehensive guide to all commands available in the Cascade CLI.

## Global Options
- `--version`: Show the version and exit.
- `--help`: Show help for any command or group.
- `ccd`: Short alias for the `cascade` command.

---

## Foundation Commands

### `cascade init [DESCRIPTION]`
Initialize a new Cascade project in the current directory.
- `DESCRIPTION`: Optional high-level overview of the project requirements.

### `cascade status`
Displays the current system status, project health, and execution summary.

### `cascade config [SUBCOMMAND]`
Manage system and project-specific configuration.
- `config show`: Display current configuration.
- `config set KEY VALUE`: Update a configuration value.

---

## Ticket Management

### `cascade ticket [SUBCOMMAND]`
Manage the development lifecycle of individual tickets.

- `ticket create`: Interactively create a new ticket.
- `ticket list`: List all tickets (supports `--status`, `--type`, `--limit`).
- `ticket show <id>`: Show detailed information about a specific ticket.
- `ticket update <id>`: Modify ticket fields (title, desc, status, etc.).
- `ticket delete <id>`: Permanently remove a ticket.
- `ticket ready <id>`: Mark a ticket as READY for execution.
- `ticket block <id> --reason <text>`: Mark a ticket as BLOCKED.
- `ticket status <id> <status>`: Directly update ticket status.
- `ticket depends <id> <dependency_id>`: Add a dependency requirement.

#### `cascade ticket execute <id>`
Execute a ticket using an AI agent.
- `--agent, -A`: Override the default agent for this execution.
- `--yes, -y`: Skip initial human confirmation prompt.
- `--dry-run`: Build the context and prompt but do not call the agent (preview mode).

---

## Topic Management

### `cascade topic [SUBCOMMAND]`
Organize tickets into high-level features or domains.

- `topic create <name>`: Create a new topic.
- `topic list`: List all topics with progress metrics.
- `topic show <name>`: Show tickets assigned to a topic.
    - `--next`: Execute the next priority ticket in this topic.
- `topic assign <topic> <id>`: Assign a ticket to a topic.
- `topic unassign <topic> <id>`: Remove a ticket from a topic.
- `topic delete <name>`: Remove a topic (tickets remain).

---

## Intelligent Selection

### `cascade type <type>`
List all tickets of a specific type (EPIC, STORY, TASK, BUG, etc.).
- `--next`: Automatically execute the next priority ticket of this type.

### `cascade next`
AI analyzes all READY tickets and suggests the most logical next step.
- `--topic <name>`: Limit suggestions to a specific topic.
- `--type <type>`: Limit suggestions to a specific ticket type.
- `--agent`: Override the agent used for performing the analysis.

---

## Knowledge & Agents

### `cascade knowledge [SUBCOMMAND]`
Manage persistent project memory (Conventions, Patterns, ADRs).

- `knowledge list`: List all approved ADRs and Patterns.
- `knowledge pending`: Review AI-proposed knowledge items.
- `knowledge approve <id>`: Move a proposal to approved status.
- `knowledge reject <id>`: Dismiss a proposal.
- `knowledge convention list`: View established project conventions.

### `cascade agents`
List all supported AI agents and their availability status.
Shows capabilities (File Edit, Command Execute, etc.) for each agent.
