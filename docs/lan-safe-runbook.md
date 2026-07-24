# LAN-Safe Runbook (localhost default, LAN opt-in)

## Security default

- The baseline in `docker-compose.yml` binds to `127.0.0.1` only.
- LAN exposure is **disabled by default**.

## LAN opt-in checklist (must complete all)

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
