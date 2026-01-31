-- Cascade Database Schema
-- SQLite database for persistent storage

-- Topics for organizing tickets
CREATE TABLE IF NOT EXISTS topics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Core tickets table
CREATE TABLE IF NOT EXISTS tickets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticket_type TEXT NOT NULL CHECK(ticket_type IN ('EPIC', 'STORY', 'TASK', 'BUG', 'SECURITY', 'TEST', 'DOC')),
    title TEXT NOT NULL,
    description TEXT,
    status TEXT NOT NULL CHECK(status IN ('DEFINED', 'READY', 'IN_PROGRESS', 'BLOCKED', 'TESTING', 'DONE', 'ABANDONED')),
    severity TEXT CHECK(severity IN ('CRITICAL', 'HIGH', 'MEDIUM', 'LOW')),
    priority_score REAL DEFAULT 0,
    parent_ticket_id INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    estimated_effort INTEGER,
    actual_effort INTEGER,
    affected_files TEXT,
    acceptance_criteria TEXT,
    context_mode TEXT DEFAULT 'minimal',
    metadata TEXT,
    FOREIGN KEY (parent_ticket_id) REFERENCES tickets(id)
);

-- Ticket-to-topic mapping
CREATE TABLE IF NOT EXISTS ticket_topics (
    ticket_id INTEGER NOT NULL,
    topic_id INTEGER NOT NULL,
    PRIMARY KEY (ticket_id, topic_id),
    FOREIGN KEY (ticket_id) REFERENCES tickets(id) ON DELETE CASCADE,
    FOREIGN KEY (topic_id) REFERENCES topics(id) ON DELETE CASCADE
);

-- Ticket dependencies
CREATE TABLE IF NOT EXISTS ticket_dependencies (
    ticket_id INTEGER NOT NULL,
    depends_on_ticket_id INTEGER NOT NULL,
    dependency_type TEXT DEFAULT 'blocks',
    PRIMARY KEY (ticket_id, depends_on_ticket_id),
    FOREIGN KEY (ticket_id) REFERENCES tickets(id) ON DELETE CASCADE,
    FOREIGN KEY (depends_on_ticket_id) REFERENCES tickets(id) ON DELETE CASCADE
);

-- Issues discovered during execution
CREATE TABLE IF NOT EXISTS issues (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    issue_type TEXT NOT NULL,
    severity TEXT NOT NULL,
    description TEXT NOT NULL,
    found_in_ticket_id INTEGER,
    created_ticket_id INTEGER,
    status TEXT DEFAULT 'OPEN',
    file_path TEXT,
    line_number INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    resolution TEXT,
    FOREIGN KEY (found_in_ticket_id) REFERENCES tickets(id),
    FOREIGN KEY (created_ticket_id) REFERENCES tickets(id)
);

-- Architecture Decision Records
CREATE TABLE IF NOT EXISTS adrs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    adr_number INTEGER UNIQUE NOT NULL,
    title TEXT NOT NULL,
    status TEXT DEFAULT 'PROPOSED' CHECK(status IN ('PROPOSED', 'APPROVED', 'REJECTED', 'SUPERSEDED')),
    context TEXT NOT NULL,
    decision TEXT NOT NULL,
    rationale TEXT NOT NULL,
    consequences TEXT,
    alternatives_considered TEXT,
    created_by_ticket_id INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    approved_at TIMESTAMP,
    FOREIGN KEY (created_by_ticket_id) REFERENCES tickets(id)
);

-- Reusable patterns
CREATE TABLE IF NOT EXISTS patterns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pattern_name TEXT UNIQUE NOT NULL,
    description TEXT NOT NULL,
    code_template TEXT,
    applies_to_tags TEXT,
    learned_from_ticket_id INTEGER,
    status TEXT DEFAULT 'PROPOSED' CHECK(status IN ('PROPOSED', 'APPROVED', 'REJECTED')),
    reuse_count INTEGER DEFAULT 0,
    file_examples TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    approved_at TIMESTAMP,
    FOREIGN KEY (learned_from_ticket_id) REFERENCES tickets(id)
);

-- Project conventions (always loaded)
CREATE TABLE IF NOT EXISTS conventions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category TEXT NOT NULL,
    convention_key TEXT NOT NULL,
    convention_value TEXT NOT NULL,
    rationale TEXT,
    priority INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(category, convention_key)
);

-- Quality gate results
CREATE TABLE IF NOT EXISTS quality_gates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticket_id INTEGER NOT NULL,
    gate_name TEXT NOT NULL,
    passed BOOLEAN NOT NULL,
    output TEXT,
    context_mode TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    retry_count INTEGER DEFAULT 0,
    FOREIGN KEY (ticket_id) REFERENCES tickets(id) ON DELETE CASCADE
);

-- Execution log
CREATE TABLE IF NOT EXISTS execution_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticket_id INTEGER,
    action TEXT NOT NULL,
    agent TEXT,
    context_mode TEXT,
    details TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    token_count INTEGER,
    execution_time_ms INTEGER,
    FOREIGN KEY (ticket_id) REFERENCES tickets(id)
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_tickets_status ON tickets(status);
CREATE INDEX IF NOT EXISTS idx_tickets_type ON tickets(ticket_type);
CREATE INDEX IF NOT EXISTS idx_tickets_parent ON tickets(parent_ticket_id);
CREATE INDEX IF NOT EXISTS idx_ticket_topics_ticket ON ticket_topics(ticket_id);
CREATE INDEX IF NOT EXISTS idx_ticket_topics_topic ON ticket_topics(topic_id);
CREATE INDEX IF NOT EXISTS idx_issues_ticket ON issues(found_in_ticket_id);
CREATE INDEX IF NOT EXISTS idx_quality_gates_ticket ON quality_gates(ticket_id);
CREATE INDEX IF NOT EXISTS idx_patterns_status ON patterns(status);
CREATE INDEX IF NOT EXISTS idx_adrs_status ON adrs(status);
CREATE INDEX IF NOT EXISTS idx_conventions_category ON conventions(category);
