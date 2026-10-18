-- The forecast tool: each open deal's forecast call (Commit / Best case / Pipeline / Omit), set by a person.
-- Deals without a row use a default from their stage probability (kit/watch.py).
CREATE TABLE IF NOT EXISTS core.forecast_calls (
    deal_id text PRIMARY KEY,
    call text NOT NULL CHECK (call IN ('commit', 'best', 'pipeline', 'omit')),
    updated_by text,
    updated_at timestamptz NOT NULL DEFAULT now()
);
