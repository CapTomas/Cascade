# Ticket Management

Tickets are the fundamental unit of work in Cascade. Every code change or task should be associated with a ticket.

## Ticket Lifecycle

1. **PROPOSED**: Automatically generated or manually created but not yet ready for work.
2. **READY**: All dependencies are met, and the ticket is ready for execution.
3. **IN PROGRESS**: Currently being executed by an agent.
4. **BLOCKED**: Waiting on another ticket or human input.
5. **DONE**: Execution completed and all quality gates passed.

## Creating Tickets

You can create tickets manually via the CLI:

```bash
cascade ticket create --title "Add user authentication" --type task --severity high
```

## Managing Dependencies

Cascade enforces a linear or branched dependency tree. A ticket cannot be marked **READY** until its parents are **DONE**.

```bash
# Make ticket 5 depend on ticket 4
cascade ticket depends 5 4
```

## Execution Flow

When you run `cascade ticket execute <id>`, Cascade performs the following steps:

1. **Context Collection**: Gathers relevant files and project memory.
2. **Human Confirmation**: Displays the prompt and asks for your permission.
3. **Agent Call**: Sends the request to the configured AI agent.
4. **Post-Processing**: Applies changes to the filesystem.
5. **Validation**: Runs quality gates.
6. **Completion**: Marks the ticket as DONE if gates pass.
