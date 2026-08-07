-- pw-ai-training schema + seed data.
-- Run via scripts/setup_db.sh (which also mints the live API token).

CREATE TABLE api_tokens (
    id          serial PRIMARY KEY,
    token_hash  text NOT NULL UNIQUE,          -- sha256 hex of the plaintext token
    owner       text NOT NULL,
    created_at  timestamptz NOT NULL DEFAULT now(),
    expires_at  timestamptz,
    revoked     boolean NOT NULL DEFAULT false
);

-- Two demo tokens for the auth-failure demo. Plaintext values are the hashed
-- literals below; swap one into .env's API_TOKEN to show the failure.
INSERT INTO api_tokens (token_hash, owner, created_at, expires_at, revoked) VALUES
    (encode(sha256('pwtrain_expired_demo_token'::bytea), 'hex'),
     'old-intern', now() - interval '90 days', now() - interval '30 days', false),
    (encode(sha256('pwtrain_revoked_demo_token'::bytea), 'hex'),
     'contractor', now() - interval '60 days', now() + interval '300 days', true);

CREATE TABLE tickets (
    id          serial PRIMARY KEY,
    title       text NOT NULL,
    description text NOT NULL,
    reporter    text NOT NULL,
    assignee    text,
    team        text NOT NULL,
    status      text NOT NULL CHECK (status IN ('open', 'in_progress', 'blocked', 'resolved', 'closed')),
    urgency     text NOT NULL CHECK (urgency IN ('low', 'medium', 'high', 'critical')),
    category    text NOT NULL CHECK (category IN ('access-request', 'hardware', 'software', 'network', 'billing')),
    created_at  timestamptz NOT NULL,
    updated_at  timestamptz NOT NULL,
    resolved_at timestamptz
);

SELECT setseed(0.42);

-- ~80 filler tickets (ids 1-80): random-ish but plausible background noise.
INSERT INTO tickets (title, description, reporter, assignee, team, status, urgency, category,
                     created_at, updated_at, resolved_at)
SELECT
    initcap(replace(cat, '-', ' ')) || ' request #' || g,
    'Auto-generated ' || cat || ' ticket used as background data for training queries.',
    reporter,
    assignee,
    team,
    status,
    urgency,
    cat,
    created,
    LEAST(now(), created + (random() * interval '5 days')),
    CASE WHEN status IN ('resolved', 'closed')
         THEN LEAST(now(), created + (random() * interval '10 days'))
         ELSE NULL END
FROM (
    SELECT g,
        (ARRAY['access-request', 'hardware', 'software', 'network', 'billing'])[1 + floor(random() * 5)::int] AS cat,
        (ARRAY['jdoe', 'ssingh', 'lgarcia', 'rpatel', 'tkim', 'avaldez', 'bwong', 'mchen'])[1 + floor(random() * 8)::int] AS reporter,
        (ARRAY['jdoe', 'ssingh', 'lgarcia', 'rpatel', 'tkim', 'mchen'])[1 + floor(random() * 6)::int] AS assignee,
        (ARRAY['it-support', 'infrastructure', 'security', 'apps'])[1 + floor(random() * 4)::int] AS team,
        (ARRAY['open', 'in_progress', 'resolved', 'closed', 'closed', 'resolved'])[1 + floor(random() * 6)::int] AS status,
        (ARRAY['low', 'low', 'medium', 'medium', 'high', 'critical'])[1 + floor(random() * 6)::int] AS urgency,
        now() - (random() * interval '120 days') AS created
    FROM generate_series(1, 80) AS g
) sub;

-- Story rows. Shaped so natural questions have interesting answers.

-- mchen is buried: 8 open criticals assigned to one person.
INSERT INTO tickets (title, description, reporter, assignee, team, status, urgency, category,
                     created_at, updated_at, resolved_at)
SELECT
    'CRITICAL: ' || t.title,
    t.descr,
    t.reporter,
    'mchen',
    t.team,
    'open',
    'critical',
    t.cat,
    now() - (t.age_days || ' days')::interval,
    now() - (t.age_days || ' days')::interval + interval '2 hours',
    NULL
FROM (VALUES
    ('SSO login loop for finance group',        'Finance users bounce between IdP and portal endlessly.',        'jdoe',    'security',       'software',       13),
    ('Payroll export job failing',              'Nightly payroll export has failed 3 nights running.',           'lgarcia', 'apps',           'software',       11),
    ('Badge readers offline in building C',     'No badge-in events since Saturday; door held open manually.',   'rpatel',  'security',       'hardware',        9),
    ('Customer portal 502s under load',         'Portal throws 502 during the 9am spike, every weekday.',        'tkim',    'apps',           'software',        7),
    ('Backup job silently skipping fileshare',  'Last verified restore point for /share is 3 weeks old.',        'ssingh',  'infrastructure', 'software',        6),
    ('VPN split-tunnel leaking DNS',            'Client DNS queries bypass the tunnel on macOS 15.',              'avaldez', 'security',       'network',         4),
    ('License server rejecting checkouts',      'CAD licenses show in-use=0 but checkouts are refused.',          'bwong',   'apps',           'software',        2),
    ('Storage array predictive failure alert',  'Controller B reports imminent disk failure, no spare on site.', 'jdoe',    'infrastructure', 'hardware',        1)
) AS t(title, descr, reporter, team, cat, age_days);

-- 4 critical tickets nobody owns.
INSERT INTO tickets (title, description, reporter, assignee, team, status, urgency, category,
                     created_at, updated_at, resolved_at)
SELECT
    'UNOWNED: ' || t.title,
    t.descr,
    t.reporter,
    NULL,
    t.team,
    'open',
    'critical',
    t.cat,
    now() - (t.age_days || ' days')::interval,
    now() - (t.age_days || ' days')::interval,
    NULL
FROM (VALUES
    ('Expired TLS cert on partner API',       'Partner integrations fail hard when the cert lapses Friday.', 'tkim',    'infrastructure', 'network',  3),
    ('Terminated employee still has access',  'Offboarded contractor account shows a login yesterday.',      'ssingh',  'security',       'access-request', 2),
    ('Invoice duplication in billing run',    'July invoices generated twice for ~40 customers.',            'lgarcia', 'apps',           'billing',  5),
    ('Core router fan failure warning',       'Primary datacenter router reports fan tray degraded.',        'rpatel',  'infrastructure', 'hardware', 1)
) AS t(title, descr, reporter, team, cat, age_days);

-- 6 stale open tickets: untouched since creation, 60-120 days old.
INSERT INTO tickets (title, description, reporter, assignee, team, status, urgency, category,
                     created_at, updated_at, resolved_at)
SELECT
    'STALE: ' || t.title,
    t.descr || ' No activity since it was filed.',
    t.reporter,
    t.assignee,
    t.team,
    'open',
    t.urgency,
    t.cat,
    now() - (t.age_days || ' days')::interval,
    now() - (t.age_days || ' days')::interval,
    NULL
FROM (VALUES
    ('Request for second monitor',            'Standard peripheral request.',                     'bwong',   'jdoe',   'it-support', 'low',    'hardware', 112),
    ('Conference room panel unresponsive',    'Room 4B touch panel needs replacement.',           'avaldez', 'rpatel', 'it-support', 'low',    'hardware',  97),
    ('Archive old project fileshares',        'Cleanup task from the Q1 storage review.',          'ssingh',  'tkim',   'infrastructure', 'medium', 'software', 88),
    ('Deprecate legacy FTP endpoint',         'Two vendors still upload via FTP.',                 'jdoe',    'ssingh', 'security',   'medium', 'network',   76),
    ('Guest wifi splash page typo',           'Cosmetic, but embarrassing.',                       'lgarcia', 'jdoe',   'it-support', 'low',    'network',   68),
    ('Update on-call escalation doc',         'Doc still lists people who left the company.',      'tkim',    'lgarcia','infrastructure', 'medium', 'software', 61)
) AS t(title, descr, reporter, assignee, team, urgency, cat, age_days);

-- Network spike: 10 tickets in one week (Jul 6-12, 2026), traced to switch firmware.
INSERT INTO tickets (title, description, reporter, assignee, team, status, urgency, category,
                     created_at, updated_at, resolved_at)
SELECT
    'Network: ' || t.title,
    t.descr || ' (Cluster of reports following the core switch firmware update on 2026-07-06.)',
    t.reporter,
    'ssingh',
    'infrastructure',
    t.status,
    t.urgency,
    'network',
    t.created::timestamptz,
    t.created::timestamptz + interval '1 day',
    CASE WHEN t.status IN ('resolved', 'closed') THEN t.created::timestamptz + interval '3 days' ELSE NULL END
FROM (VALUES
    ('Intermittent packet loss floor 2',   'Users report dropped video calls.',            'jdoe',    'resolved', 'high',   '2026-07-06 09:15'),
    ('VoIP quality degraded',              'Choppy audio on all desk phones.',             'lgarcia', 'resolved', 'high',   '2026-07-06 11:40'),
    ('Wifi roaming disconnects',           'Laptops drop when moving between APs.',        'bwong',   'resolved', 'medium', '2026-07-07 08:05'),
    ('Printers unreachable on VLAN 30',    'Whole print VLAN intermittently dark.',        'avaldez', 'resolved', 'medium', '2026-07-07 14:22'),
    ('Slow SMB transfers',                 'Fileshare copies at 10% of normal speed.',     'tkim',    'resolved', 'medium', '2026-07-08 10:01'),
    ('Video conference rooms offline',     'All Zoom rooms on floor 3 dropped.',           'rpatel',  'resolved', 'high',   '2026-07-08 16:47'),
    ('Monitoring alerts flapping',         'Switch uplink alerts firing and clearing.',    'ssingh',  'resolved', 'high',   '2026-07-09 07:30'),
    ('Badge system timeouts',              'Door controllers timing out to auth server.',  'jdoe',    'resolved', 'high',   '2026-07-10 09:12'),
    ('Lab instruments losing NFS mounts',  'Instrument PCs unmount mid-run.',              'mchen',   'closed',   'medium', '2026-07-11 13:55'),
    ('Residual latency spikes',            'p99 latency still elevated after rollback.',   'tkim',    'open',     'medium', '2026-07-12 15:20')
) AS t(title, descr, reporter, status, urgency, created);

-- 3 blocked tickets that reference other tickets by id.
INSERT INTO tickets (title, description, reporter, assignee, team, status, urgency, category,
                     created_at, updated_at, resolved_at)
VALUES
    ('Onboard new analytics vendor',
     'Cannot proceed until the partner API cert is rotated — blocked by the UNOWNED TLS cert ticket. See also ticket #12.',
     'lgarcia', 'tkim', 'apps', 'blocked', 'high', 'software',
     now() - interval '8 days', now() - interval '2 days', NULL),
    ('Migrate finance share to new array',
     'Waiting on storage array controller replacement; blocked by ticket #27 and the storage predictive-failure ticket.',
     'ssingh', 'rpatel', 'infrastructure', 'blocked', 'medium', 'hardware',
     now() - interval '15 days', now() - interval '6 days', NULL),
    ('Enable MFA for vendor portal',
     'Rollout paused pending SSO loop fix; blocked by ticket #44.',
     'jdoe', 'mchen', 'security', 'blocked', 'high', 'access-request',
     now() - interval '10 days', now() - interval '4 days', NULL);
