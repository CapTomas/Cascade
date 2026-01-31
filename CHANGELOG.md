# Changelog

All notable changes to Cascade will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-01-31

### Added

#### Core Features
- **Agent-Agnostic Architecture**: Support for multiple AI agents (Claude Code, Antigravity, Codex, Generic, Manual)
- **Ticket-Based Workflow**: EPIC/STORY/TASK/BUG/SECURITY/TEST/DOC ticket types with status tracking
- **Topic Organization**: Group related tickets by feature areas
- **Context Escalation**: Automatic minimal → standard → full context escalation on failures
- **Quality Gates**: Static analysis, unit tests, and security scanning enforcement
- **Knowledge System**: Conventions, Patterns, and ADRs with human approval workflow

#### CLI Commands
- `cascade init` - Initialize projects from requirements
- `cascade ticket` - Manage tickets (create, list, show, execute)
- `cascade topic` - Organize tickets by topic
- `cascade status` - Project overview dashboard
- `cascade config` - Configuration management
- `cascade knowledge` - Manage conventions, patterns, ADRs
- `cascade agents` - List and configure AI agents
- `cascade type` - List tickets by type
- `cascade next` - AI-suggested next ticket

#### Agent Integrations
- **Claude Code**: Full integration via CLI with file editing and command execution
- **Antigravity**: REST API integration with retry logic
- **Codex/OpenAI**: OpenAI Responses API integration
- **Generic**: stdin/stdout adapter for custom agents
- **Manual**: Interactive mode for manual execution

#### Infrastructure
- SQLite database with proper schema and indexes
- YAML-based configuration
- Centralized logging with rotation
- Token counting with tiktoken
- Rich terminal output with themed components

### Security
- Working directory validation to prevent path traversal
- Input sanitization in CLI commands
- Secure API key handling via environment variables

### Documentation
- Getting Started guide
- Command reference
- Agent configuration guide
- Quality gates documentation
- Knowledge system documentation

---

## [Unreleased]

### Planned
- Watch mode for file changes
- Git integration (branch creation, commit linking)
- Multi-agent fallback chains
- Metrics dashboard
- Plugin system for custom gates/agents
