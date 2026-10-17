-- Standard ("canonical") source tables. Every connector, whether Salesforce, HubSpot,
-- QuickBooks or the demo, maps into these, so tools are written once.
-- Client-specific fields go in `extra`.

CREATE TABLE IF NOT EXISTS crm.users (
    id text PRIMARY KEY, name text, email text, title text, branch_code text,
    active boolean, extra jsonb NOT NULL DEFAULT '{}', synced_at timestamptz NOT NULL
);
CREATE TABLE IF NOT EXISTS crm.accounts (
    id text PRIMARY KEY, name text, segment text, city text, state text, branch_code text,
    created_at timestamptz, extra jsonb NOT NULL DEFAULT '{}', synced_at timestamptz NOT NULL
);
CREATE TABLE IF NOT EXISTS crm.opportunities (
    id text PRIMARY KEY, name text, account_id text, owner_id text, branch_code text,
    deal_type text, stage text, is_closed boolean, is_won boolean, probability numeric,
    amount numeric, margin_pct numeric, close_date date, created_at timestamptz,
    modified_at timestamptz, loss_reason text, lead_source text,
    exclude_from_reporting boolean NOT NULL DEFAULT false,
    extra jsonb NOT NULL DEFAULT '{}', synced_at timestamptz NOT NULL
);
-- Only ever added to. This is what lets us answer "what changed last week".
CREATE TABLE IF NOT EXISTS crm.opportunity_history (
    id text PRIMARY KEY, opportunity_id text NOT NULL, field text NOT NULL,
    old_value text, new_value text, changed_at timestamptz NOT NULL, synced_at timestamptz NOT NULL
);
CREATE INDEX IF NOT EXISTS opportunity_history_opp ON crm.opportunity_history (opportunity_id);
CREATE INDEX IF NOT EXISTS opportunity_history_at ON crm.opportunity_history (changed_at);

CREATE TABLE IF NOT EXISTS acct.customers (
    id text PRIMARY KEY, name text, crm_account_id text, terms_days integer,
    extra jsonb NOT NULL DEFAULT '{}', synced_at timestamptz NOT NULL
);
CREATE TABLE IF NOT EXISTS acct.invoices (
    id text PRIMARY KEY, number text, customer_id text, invoice_date date, due_date date,
    amount numeric, amount_paid numeric, paid_date date, reference text, memo text,
    extra jsonb NOT NULL DEFAULT '{}', synced_at timestamptz NOT NULL
);
CREATE INDEX IF NOT EXISTS invoices_reference ON acct.invoices (reference);
