-- Kit tables. Safe to re-run: everything is IF NOT EXISTS.
CREATE SCHEMA IF NOT EXISTS core;
CREATE SCHEMA IF NOT EXISTS crm;
CREATE SCHEMA IF NOT EXISTS acct;
CREATE SCHEMA IF NOT EXISTS rpt;

-- Client settings and reference data, loaded from the client's config.toml.
CREATE TABLE IF NOT EXISTS core.settings (key text PRIMARY KEY, value text NOT NULL);
CREATE TABLE IF NOT EXISTS core.branches (
    code text PRIMARY KEY, name text NOT NULL, region text NOT NULL, active boolean NOT NULL DEFAULT true
);
CREATE TABLE IF NOT EXISTS core.goals (
    metric text NOT NULL, period text NOT NULL, value numeric NOT NULL, PRIMARY KEY (metric, period)
);

-- When each sync (and the backup) last ran and how it went. Health page and alerts read this.
CREATE TABLE IF NOT EXISTS core.sync_state (
    object text PRIMARY KEY,
    source text NOT NULL,
    last_attempt_at timestamptz,
    last_success_at timestamptz,
    last_status text,
    last_message text,
    rows_seen integer,
    rows_upserted integer,
    rows_pruned integer
);

-- People who can sign in to the hub. branches NULL = sees every branch.
CREATE TABLE IF NOT EXISTS core.app_users (
    id serial PRIMARY KEY,
    email text NOT NULL UNIQUE,
    name text NOT NULL,
    password_hash text,
    role text NOT NULL DEFAULT 'viewer' CHECK (role IN ('admin', 'viewer')),
    branches text[],
    active boolean NOT NULL DEFAULT true,
    created_at timestamptz NOT NULL DEFAULT now(),
    last_login_at timestamptz
);
CREATE TABLE IF NOT EXISTS core.sessions (
    id text PRIMARY KEY,
    user_id integer NOT NULL REFERENCES core.app_users(id) ON DELETE CASCADE,
    created_at timestamptz NOT NULL DEFAULT now(),
    expires_at timestamptz NOT NULL
);
CREATE TABLE IF NOT EXISTS core.page_visits (
    id bigserial PRIMARY KEY,
    user_id integer REFERENCES core.app_users(id) ON DELETE SET NULL,
    path text NOT NULL,
    at timestamptz NOT NULL DEFAULT now()
);

CREATE OR REPLACE FUNCTION core.client_tz() RETURNS text LANGUAGE sql STABLE AS
$$ SELECT coalesce((SELECT value FROM core.settings WHERE key = 'timezone'), 'America/Chicago') $$;
CREATE OR REPLACE FUNCTION core.local_today() RETURNS date LANGUAGE sql STABLE AS
$$ SELECT (now() AT TIME ZONE core.client_tz())::date $$;
