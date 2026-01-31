# Quality Gates

Quality Gates are automated checks that Cascade runs after an agent completes a ticket. They ensure that AI-generated code meets your project's standards.

## Core Gates

Cascade includes several built-in quality gates:

- **Static Analysis**: Runs linters (e.g., Ruff, ESLint) to check for style and common errors.
- **Unit Tests**: Executes your test suite (e.g., Pytest, Jest) to verify functionality.
- **Security Scan**: Checks for hardcoded secrets or known vulnerabilities.
- **Build Check**: Ensures the project still compiles or installs correctly.

## Configuration

Quality gates are configured in your project's `cascade.yaml` (or via `cascade config`):

```yaml
quality_gates:
  enforce_all: true
  gates:
    - name: ruff
      type: linter
      command: "ruff check ."
    - name: pytest
      type: test
      command: "pytest tests/"
```

## Failure Handling

If a quality gate fails:
1. The ticket is **not** marked as DONE.
2. Cascade displays the failure output.
3. You can either fix the issue manually or ask the agent to try again by re-running the ticket.
