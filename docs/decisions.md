# Architectural decisions

## 001: Single-admin API key
All administrative routes require X-API-Key. Comparison uses constant-time
hmac.compare_digest. The secret is passed via environment variables, never
stored in the repository. Rotate it by changing the environment and restarting.
This deliberately avoids a user-management database.

## 002: Atomic redirect analytics
The redirect increments the link's total via SQL UPDATE and UPSERTs the UTC
daily bucket within one transaction before returning HTTP 302. PostgreSQL
row-level locking and unique (link_id, day) prevent lost increments under
concurrency. Counts represent responses prepared by this server, not confirmed
destination page visits.

## 003: Abuse and privacy
Only authenticated operators can create links. Targets must use http/https,
with no credentials, private IP targets or local hostnames. No server-side
fetching of destination URLs takes place. The app does not store IP addresses,
user agents, or referrers. Counts and last-access timestamps are aggregate
metrics. It does not check malicious-domain reputation or provide a takedown
workflow. Never operate it as an anonymous public shortening service.

## 004: Rate limiting
A thread-safe, in-process, sliding one-minute window protects authenticated
operations per admin principal. It resets on restart and is NOT distributed.
Use an API gateway or shared rate-limit store before horizontally scaling.

## 005: Lifecycle and constraints
Random codes contain seven cryptographically sampled alphanumeric characters.
A database uniqueness constraint and bounded retries handle collisions.
Custom aliases remain unavailable after soft deletion to prevent takeover.
Inactive, expired and deleted links all respond with a public 404.
Analytics for deleted links remain in the database but are not displayed by
administrative reports. No scheduled retention/cleanup task is provided.

## 006: Operations
PostgreSQL is the sole persistence layer. Docker Compose is for local work;
CI uses an ephemeral PostgreSQL service. No production deployment, anonymous
signup, automated publication, Redis or queue is included.

## 007: Privacy-conscious server logs
The default Compose/Docker invocation disables Uvicorn HTTP access logs,
which otherwise include client IP addresses. Keep access logs disabled or
redacted in production and configure the reverse proxy accordingly.

## 008: Connection strings and administrator credentials
Compose supplies the database password as a separate environment variable.
SQLAlchemy constructs and escapes the DSN, so reserved characters in the
password cannot be confused with URL delimiters. An explicit
SHORTLINK_DATABASE_URL remains supported for local/CI use; credentials in
manually configured URLs must already be percent-encoded. Administrator keys
must be ASCII to support safe constant-time comparisons; invalid headers
return 401 rather than server errors.

## 009: Monotonic access timestamps and scalable counters
A conditional SQL greatest/coalesce expression ensures delayed redirects
cannot move last_accessed_at backwards. The counter increment and UTC daily
upsert remain within one PostgreSQL transaction. Alembic revision 0002 widens
the daily_clicks surrogate ID and its serial sequence to bigint; the
migration also upgrades databases already at revision 0001.
