-- AI layer. Every model call is logged with its tokens and cost, so caps can be enforced
-- and the owner can see exactly what the AI costs.
CREATE TABLE IF NOT EXISTS core.ai_usage (
    id bigserial PRIMARY KEY,
    feature text NOT NULL,                  -- 'chat' or 'insights'
    user_id integer REFERENCES core.app_users(id) ON DELETE SET NULL,
    model text NOT NULL,
    input_tokens integer NOT NULL DEFAULT 0,
    output_tokens integer NOT NULL DEFAULT 0,
    cache_read_tokens integer NOT NULL DEFAULT 0,
    cache_write_tokens integer NOT NULL DEFAULT 0,
    cost_usd numeric(12, 6) NOT NULL DEFAULT 0,
    request_id text,
    at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ai_usage_feature_at ON core.ai_usage (feature, at);

-- One row per chat thread. messages is the exact history sent to the model (append-only).
CREATE TABLE IF NOT EXISTS core.ai_conversations (
    id text PRIMARY KEY,
    user_id integer NOT NULL REFERENCES core.app_users(id) ON DELETE CASCADE,
    messages jsonb NOT NULL DEFAULT '[]',
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

-- Questions run in the background (proxies cut requests at ~60s); the page polls for the answer.
CREATE TABLE IF NOT EXISTS core.ai_jobs (
    id text PRIMARY KEY,
    conversation_id text NOT NULL REFERENCES core.ai_conversations(id) ON DELETE CASCADE,
    user_id integer NOT NULL REFERENCES core.app_users(id) ON DELETE CASCADE,
    question text NOT NULL,
    status text NOT NULL DEFAULT 'running' CHECK (status IN ('running', 'done', 'failed')),
    progress text,
    answer text,
    error text,
    cost_usd numeric(12, 6) NOT NULL DEFAULT 0,
    created_at timestamptz NOT NULL DEFAULT now(),
    finished_at timestamptz
);
CREATE INDEX IF NOT EXISTS ai_jobs_user_created ON core.ai_jobs (user_id, created_at);

-- Proactive insights, written a few times a day by `python -m kit.ai.insights`.
CREATE TABLE IF NOT EXISTS core.ai_insights (
    id bigserial PRIMARY KEY,
    batch_id text NOT NULL,
    position integer NOT NULL,
    headline text NOT NULL,
    detail text NOT NULL,
    link text,
    link_label text,
    created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ai_insights_created ON core.ai_insights (created_at);
