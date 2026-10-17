-- Problems the alert check has found. One row per problem; it stays until the problem goes away.
CREATE TABLE IF NOT EXISTS core.alerts (
    key text PRIMARY KEY,                 -- e.g. 'sync:crm.opportunities', 'backup', 'agents', 'ai_spend:chat'
    severity text NOT NULL CHECK (severity IN ('warning', 'critical')),
    message text NOT NULL,
    first_seen timestamptz NOT NULL DEFAULT now(),
    last_seen timestamptz NOT NULL DEFAULT now(),
    last_sent timestamptz,
    resolved_at timestamptz
);
