-- The "practice" app: a built-in tracker for a consulting business (our own company hub).
-- Data is entered in the hub's forms. Nothing is ever hard-deleted from the screens; records are archived.
CREATE SCHEMA IF NOT EXISTS practice;

CREATE TABLE IF NOT EXISTS practice.companies (
    id serial PRIMARY KEY,
    name text NOT NULL,
    kind text NOT NULL DEFAULT 'prospect' CHECK (kind IN ('prospect', 'client', 'partner', 'past_client')),
    stage text NOT NULL DEFAULT 'lead'
        CHECK (stage IN ('lead', 'contacted', 'conversation', 'proposal', 'won', 'lost', 'not_now')),
    industry text, size_note text, city text, website text,
    contact_name text, contact_title text, contact_email text, contact_phone text,
    source text,                                      -- how we met: referral, LinkedIn, event, cold outreach...
    referred_by integer REFERENCES practice.companies(id) ON DELETE SET NULL,
    est_value numeric(12, 2),                         -- first-year value if it closes
    next_step text, next_step_date date,
    notes text,
    archived boolean NOT NULL DEFAULT false,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS practice.activities (
    id serial PRIMARY KEY,
    company_id integer NOT NULL REFERENCES practice.companies(id) ON DELETE CASCADE,
    happened_on date NOT NULL,
    kind text NOT NULL CHECK (kind IN ('call', 'meeting', 'email', 'linkedin', 'event', 'note')),
    summary text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS activities_company ON practice.activities (company_id, happened_on);

CREATE TABLE IF NOT EXISTS practice.engagements (
    id serial PRIMARY KEY,
    company_id integer NOT NULL REFERENCES practice.companies(id) ON DELETE CASCADE,
    offer text NOT NULL CHECK (offer IN ('health_report', 'assessment', 'build', 'retainer', 'other')),
    name text NOT NULL,
    status text NOT NULL DEFAULT 'proposed' CHECK (status IN ('proposed', 'active', 'done', 'cancelled')),
    price numeric(12, 2),            -- fixed fee
    monthly_fee numeric(12, 2),      -- retainers
    hours_budget numeric(8, 2),
    start_date date, end_date date,
    notes text,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS practice.time_entries (
    id serial PRIMARY KEY,
    company_id integer REFERENCES practice.companies(id) ON DELETE SET NULL,  -- NULL = running the business
    engagement_id integer REFERENCES practice.engagements(id) ON DELETE SET NULL,
    work_date date NOT NULL,
    hours numeric(5, 2) NOT NULL CHECK (hours > 0 AND hours <= 24),
    billable boolean NOT NULL DEFAULT true,
    note text,
    created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS time_entries_date ON practice.time_entries (work_date);

CREATE TABLE IF NOT EXISTS practice.invoices (
    id serial PRIMARY KEY,
    company_id integer NOT NULL REFERENCES practice.companies(id) ON DELETE RESTRICT,
    engagement_id integer REFERENCES practice.engagements(id) ON DELETE SET NULL,
    number text NOT NULL UNIQUE,
    issued_date date NOT NULL,
    due_date date NOT NULL,
    amount numeric(12, 2) NOT NULL CHECK (amount >= 0),
    paid_date date,
    note text,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS practice.expenses (
    id serial PRIMARY KEY,
    spent_date date NOT NULL,
    category text NOT NULL,
    vendor text,
    amount numeric(12, 2) NOT NULL CHECK (amount >= 0),
    note text,
    created_at timestamptz NOT NULL DEFAULT now()
);
