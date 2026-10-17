-- Practice app, part 2: tasks, and the agents' work (runs, and items waiting for approval).
CREATE TABLE IF NOT EXISTS practice.tasks (
    id serial PRIMARY KEY,
    title text NOT NULL,
    category text NOT NULL DEFAULT 'General',
    due_date date,
    company_id integer REFERENCES practice.companies(id) ON DELETE SET NULL,
    done_at timestamptz,
    notes text,
    created_by text NOT NULL DEFAULT 'noah',      -- 'noah' or the agent's key
    created_at timestamptz NOT NULL DEFAULT now()
);

-- One row per agent job run: what it cost and what it produced.
CREATE TABLE IF NOT EXISTS practice.agent_runs (
    id serial PRIMARY KEY,
    agent text NOT NULL,
    job text NOT NULL,
    status text NOT NULL DEFAULT 'running' CHECK (status IN ('running', 'done', 'failed')),
    summary text,
    error text,
    items_created integer NOT NULL DEFAULT 0,
    cost_usd numeric(12, 6) NOT NULL DEFAULT 0,
    started_at timestamptz NOT NULL DEFAULT now(),
    finished_at timestamptz
);
CREATE INDEX IF NOT EXISTS agent_runs_job ON practice.agent_runs (agent, job, started_at);

-- Everything an agent produces waits here until Noah approves or dismisses it. Agents never send anything.
CREATE TABLE IF NOT EXISTS practice.agent_items (
    id serial PRIMARY KEY,
    run_id integer REFERENCES practice.agent_runs(id) ON DELETE SET NULL,
    agent text NOT NULL,
    kind text NOT NULL CHECK (kind IN ('prospect', 'message', 'post', 'brief', 'task', 'note')),
    title text NOT NULL,
    body text,
    data jsonb NOT NULL DEFAULT '{}',
    company_id integer REFERENCES practice.companies(id) ON DELETE SET NULL,
    status text NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'dismissed', 'done')),
    created_at timestamptz NOT NULL DEFAULT now(),
    decided_at timestamptz
);
CREATE INDEX IF NOT EXISTS agent_items_status ON practice.agent_items (status, created_at);
