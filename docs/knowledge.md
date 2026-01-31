# Knowledge System

The Knowledge System allows Cascade to learn from your project's history and architectural decisions.

## ADRs and Patterns

Cascade automatically suggests:
- **Architecture Decision Records (ADRs)**: Documentation of significant architectural choices.
- **Patterns**: Recurring code structures or best practices identified in your codebase.

## How it Works

1. **Extraction**: After a ticket execution, Cascade analyzes the changes and the agent's reasoning.
2. **Proposal**: If a new pattern or decision is identified, Cascade proposes it as "Pending Knowledge."
3. **Human Review**: You review and approve the proposal:
   ```bash
   cascade knowledge list --status pending
   cascade knowledge approve <id>
   ```
4. **Context Injection**: Approved knowledge is automatically injected into the context of future relevant tickets, ensuring consistency across the project.

## Persistent Memory

The knowledge base is stored in your `.cascade/` directory, making it part of your repository. This ensures that the context scales as your project grows.
