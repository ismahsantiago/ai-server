# LAN-Safe Runbook (localhost only; LAN not available)

## Current status: LAN generation is refused

`--access lan`, `--auth bearer-token`, and `--lan-allowlist` are **rejected by
the generator**. There is no supported path to produce a LAN workspace from this
repository today, and the validator refuses any workspace that claims LAN
access, an auth mode other than `none`, or an allowlist.

This is deliberate: the generator could record those values but could not
enforce them, and a workspace that *claims* a control it does not apply is worse
than one that refuses to exist.

## Security default

- The baseline in `docker-compose.yml` binds to `127.0.0.1` only.
- LAN exposure is **disabled and cannot be enabled through the generator**.

## Requirements before LAN could be enabled (not yet implemented)

The checklist below is the design target for future LAN support, not a procedure
that can be completed today. It is retained so the security bar is explicit.
Nothing here is enforced by the generator; treat it as unimplemented work.

1. **Authentication required**
   - Put a reverse proxy in front of the model API (for example Caddy/Nginx/Traefik).
   - Require auth (at minimum a strong static bearer token; preferably mTLS or OIDC).
   - Reject unauthenticated requests before they reach the model container.

2. **Firewall restriction**
   - Allow only trusted RFC1918 source ranges (or specific host IPs).
   - Deny all other inbound traffic to the serving port.

3. **Explicit bind change**
   - Change compose port mapping from:
     - `127.0.0.1:${HOST_PORT}:8000`
   - To a LAN bind only after auth + firewall are in place.

4. **Token handling**
   - Store tokens in local secret storage or `.env` excluded from commits.
   - Rotate tokens on personnel/device changes.

5. **Auditability**
   - Keep access logs in `logs/` with timestamp and source IP.
   - Record the opt-in date and operator in your project notes.

## Validation before LAN use

Run:

```bash
docker compose ps
curl -sS http://127.0.0.1:${HOST_PORT:-8000}/health
./scripts/smoke_benchmark.sh
```

If any check fails, revert to localhost-only mode.
