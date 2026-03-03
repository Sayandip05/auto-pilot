-- ─────────────────────────────────────────────────────────────
--  AUTO-PILOT  ·  PostgreSQL Schema
-- ─────────────────────────────────────────────────────────────

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ── Users ─────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS users (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    telegram_id     BIGINT UNIQUE,
    discord_id      TEXT UNIQUE,
    email           TEXT UNIQUE,
    api_key         TEXT UNIQUE NOT NULL DEFAULT encode(gen_random_bytes(32), 'hex'),
    preferences     JSONB DEFAULT '{}',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ── Tasks ─────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS tasks (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    workflow_type   TEXT NOT NULL,       -- email_to_calendar, price_tracker, etc.
    status          TEXT NOT NULL DEFAULT 'pending',  -- pending|running|completed|failed
    input_data      JSONB NOT NULL DEFAULT '{}',
    output_data     JSONB DEFAULT '{}',
    error_message   TEXT,
    agent_trace_id  TEXT,               -- LangSmith trace ID
    tokens_used     INTEGER DEFAULT 0,
    duration_ms     INTEGER,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at    TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_tasks_user_id ON tasks(user_id);
CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
CREATE INDEX IF NOT EXISTS idx_tasks_workflow_type ON tasks(workflow_type);
CREATE INDEX IF NOT EXISTS idx_tasks_created_at ON tasks(created_at DESC);

-- ── Scheduled Workflows ───────────────────────────────────────
CREATE TABLE IF NOT EXISTS schedules (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    workflow_type   TEXT NOT NULL,
    cron_expression TEXT,               -- NULL = one-time
    next_run_at     TIMESTAMPTZ NOT NULL,
    last_run_at     TIMESTAMPTZ,
    is_active       BOOLEAN NOT NULL DEFAULT true,
    config          JSONB NOT NULL DEFAULT '{}',  -- workflow-specific config
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_schedules_next_run ON schedules(next_run_at) WHERE is_active = true;

-- ── Price Tracker ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS price_tracks (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    schedule_id     UUID REFERENCES schedules(id) ON DELETE SET NULL,
    product_url     TEXT NOT NULL,
    product_name    TEXT,
    baseline_price  NUMERIC(10, 2),
    current_price   NUMERIC(10, 2),
    alert_threshold NUMERIC(10, 2),
    is_active       BOOLEAN NOT NULL DEFAULT true,
    last_checked_at TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ── Price History ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS price_history (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    track_id        UUID NOT NULL REFERENCES price_tracks(id) ON DELETE CASCADE,
    price           NUMERIC(10, 2) NOT NULL,
    recorded_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_price_history_track ON price_history(track_id, recorded_at DESC);

-- ── Audit Logs ────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS audit_logs (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         UUID REFERENCES users(id) ON DELETE SET NULL,
    task_id         UUID REFERENCES tasks(id) ON DELETE SET NULL,
    service         TEXT NOT NULL,      -- gateway|agents|scheduler
    agent_name      TEXT,
    action          TEXT NOT NULL,
    details         JSONB DEFAULT '{}',
    ip_address      TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_audit_logs_user ON audit_logs(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_logs_task ON audit_logs(task_id);

-- ── Auto-update updated_at ─────────────────────────────────────
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER tasks_updated_at
    BEFORE UPDATE ON tasks
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();
