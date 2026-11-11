"""B2-S01, B2-S04: the sign-in throttle is checked and counted atomically, before any factor
is verified, and an address that only knows an e-mail cannot lock its user out.

`pintae_auth_reserve` is one statement: under transaction-scoped advisory locks on the
account key and then the client key, it counts and either refuses or inserts the attempt
as a failure (a reservation) and returns its id. A verified step later marks that row
succeeded. Concurrent requests therefore see each other's reservations.

Limits (TRD 8.1):
- per client address: `client_max` sign-in requests in the window;
- per (account, client address): `pair_max` failures since the account's last success;
- per account: once failures since its last success come from `distinct_max` or more
  client addresses, a delay after the latest failure of `base_s * 2^(n - distinct_max)`
  seconds, capped at `cap_s`. A delay, not a lock: the account opens again by itself.

Revision ID: 0008
Revises: 0007
Create Date: 2026-11-11
"""

import sqlalchemy as sa
from alembic import op

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None

FUNC = r"""
CREATE FUNCTION pintae_auth_reserve(
  p_client bytea, p_account bytea, p_window_min int, p_client_max int, p_pair_max int,
  p_distinct_max int, p_base_s int, p_cap_s int)
RETURNS TABLE (attempt_id uuid, refused text, retry_after int)
LANGUAGE plpgsql SECURITY INVOKER SET search_path = public, pg_temp AS $f$
DECLARE
  since timestamptz := now() - make_interval(mins => p_window_min);
  last_ok timestamptz;
  n_client int;
  n_pair int;
  n_distinct int;
  last_fail timestamptz;
  delay int;
  aid uuid;
BEGIN
  IF p_account IS NOT NULL THEN
    PERFORM pg_advisory_xact_lock(hashtextextended('acct:' || encode(p_account, 'hex'), 0));
  END IF;
  PERFORM pg_advisory_xact_lock(hashtextextended('client:' || encode(p_client, 'hex'), 0));
  SELECT count(*) INTO n_client FROM auth_attempts
   WHERE key_hash = p_client AND kind = 'client' AND at > since;
  INSERT INTO auth_attempts (key_hash, kind, succeeded) VALUES (p_client, 'client', true);
  IF n_client >= p_client_max THEN
    RETURN QUERY SELECT NULL::uuid, 'client'::text, (p_window_min * 60);
    RETURN;
  END IF;
  IF p_account IS NULL THEN
    RETURN QUERY SELECT NULL::uuid, NULL::text, 0;
    RETURN;
  END IF;
  SELECT max(at) INTO last_ok FROM auth_attempts
   WHERE key_hash = p_account AND kind = 'account' AND succeeded;
  SELECT count(*) FILTER (WHERE client_hash = p_client), count(DISTINCT client_hash), max(at)
    INTO n_pair, n_distinct, last_fail
    FROM auth_attempts
   WHERE key_hash = p_account AND kind = 'account' AND NOT succeeded
     AND at > greatest(since, coalesce(last_ok, '-infinity'::timestamptz));
  IF n_pair >= p_pair_max THEN
    RETURN QUERY SELECT NULL::uuid, 'pair'::text, (p_window_min * 60);
    RETURN;
  END IF;
  IF n_distinct >= p_distinct_max THEN
    delay := least(p_cap_s, p_base_s * (2 ^ least(n_distinct - p_distinct_max, 20))::int);
    IF now() < last_fail + make_interval(secs => delay) THEN
      RETURN QUERY SELECT NULL::uuid, 'account_delay'::text,
        greatest(1, ceil(extract(epoch FROM (last_fail + make_interval(secs => delay) - now())))::int);
      RETURN;
    END IF;
  END IF;
  INSERT INTO auth_attempts (key_hash, kind, succeeded, client_hash)
  VALUES (p_account, 'account', false, p_client) RETURNING id INTO aid;
  RETURN QUERY SELECT aid, NULL::text, 0;
END $f$;
REVOKE ALL ON FUNCTION pintae_auth_reserve(bytea, bytea, int, int, int, int, int, int) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION pintae_auth_reserve(bytea, bytea, int, int, int, int, int, int)
  TO pintae_app;
GRANT UPDATE (succeeded) ON auth_attempts TO pintae_app;
"""


def upgrade() -> None:
    op.add_column("auth_attempts", sa.Column("client_hash", sa.LargeBinary(), nullable=True))
    op.execute(FUNC)


def downgrade() -> None:
    op.execute("REVOKE UPDATE (succeeded) ON auth_attempts FROM pintae_app")
    op.execute(
        "DROP FUNCTION IF EXISTS pintae_auth_reserve(bytea, bytea, int, int, int, int, int, int)"
    )
    op.drop_column("auth_attempts", "client_hash")
