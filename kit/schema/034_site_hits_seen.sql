-- A visit counts only once the browser proves it is real: each page carries a tiny invisible image (/seen.gif) that real
-- browsers load and most bots don't. The page view and the image share a random `token`; kind 'seen' is the image arriving.
ALTER TABLE practice.site_hits ADD COLUMN IF NOT EXISTS token text;
ALTER TABLE practice.site_hits DROP CONSTRAINT IF EXISTS site_hits_kind_check;
ALTER TABLE practice.site_hits ADD CONSTRAINT site_hits_kind_check CHECK (kind IN ('view', 'tour_play', 'seen'));
CREATE INDEX IF NOT EXISTS site_hits_token ON practice.site_hits (token) WHERE token IS NOT NULL;
