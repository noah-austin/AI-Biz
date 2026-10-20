-- Visits to the public website, counted by the website itself: no cookies, no third parties.
-- `visitor` is a one-way code that changes every day (it can't be turned back into an address or followed across days).
-- kind: 'view' (a page was opened) or 'tour_play' (someone pressed play on the What we build video).
CREATE TABLE IF NOT EXISTS practice.site_hits (
    id bigserial PRIMARY KEY,
    at timestamptz NOT NULL DEFAULT now(),
    kind text NOT NULL DEFAULT 'view' CHECK (kind IN ('view', 'tour_play')),
    path text NOT NULL,
    ref_host text,                      -- the site the visitor came from, if another one
    source text,                        -- ?from=... on our own links (e.g. from=email)
    visitor text
);
CREATE INDEX IF NOT EXISTS site_hits_at ON practice.site_hits (at);

-- The website's own database login (website_<hub>) may add hits, nothing else.
DO $$
DECLARE r record;
BEGIN
    FOR r IN SELECT rolname FROM pg_roles WHERE rolname LIKE 'website\_%' LOOP
        EXECUTE format('GRANT INSERT ON practice.site_hits TO %I', r.rolname);
        EXECUTE format('GRANT USAGE ON SEQUENCE practice.site_hits_id_seq TO %I', r.rolname);
    END LOOP;
END$$;
