-- Enquiries from the public website. `crm` holds the "main systems you use" answer. The website's own database login can only INSERT here; the hub reviews them.
CREATE TABLE IF NOT EXISTS practice.inbound_leads (
    id serial PRIMARY KEY,
    name text NOT NULL,
    email text NOT NULL,
    company text,
    role text,
    company_size text,
    crm text,
    interest text,
    message text,
    source_page text,
    ip_hash text,                       -- hashed, for rate limiting only
    status text NOT NULL DEFAULT 'new' CHECK (status IN ('new', 'added', 'dismissed')),
    company_id integer REFERENCES practice.companies(id) ON DELETE SET NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS inbound_leads_status ON practice.inbound_leads (status, created_at);
