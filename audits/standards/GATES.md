# Quality gates

These gates apply cumulatively. A later gate does not waive an earlier one.
Record each command, exit code, relevant output, environment, and whether the
evidence is static or live.

## Gate 0 — Start and classify

Before editing:

1. State the task scope, affected product surfaces, risk, and acceptance
   criteria.
2. Load [`README.md`](README.md), [`MANIFESTO.md`](MANIFESTO.md), this file,
   and every standards document selected by the loading table.
3. Identify whether the work affects secrets, LAN, auth, untrusted input,
   filesystem replacement, containers, dependencies, model artifacts, agent
   permissions, distribution, or runtime claims.
4. Declare the evidence plan as static, live, or both. Name any model, Docker
   daemon, network control, scanner, or host capability that is unavailable.
5. For PM Harness work, confirm that the task has an approved plan before
   execution and preserve task ownership boundaries.

Gate 0 fails when scope is ambiguous, required standards are not loaded, a
destructive boundary is unresolved, or planned evidence cannot support the
intended claim.

## Gate 1 — Change or pull request

Run the current stack checks from the repository root:

```sh
docker --version
python3 --version
python3 -m pip --version
python3 -m unittest
python3 -m pip check
docker compose config --quiet
for script in scripts/*.sh; do bash -n "$script"; done
for template in templates/chat/scripts/*.j2; do bash -n "$template"; done
python3 .pm-harness/bin/harness.py validate
python3 .pm-harness/bin/harness.py agents check
python3 .pm-harness/bin/harness.py wiki check
python3 .pm-harness/bin/harness.py plan check TASK-0007
```

For later tasks, replace `TASK-0007` with the active task ID. When documented
product behavior changes, also run:

```sh
python3 .pm-harness/bin/harness.py changelog check --task TASK-0007
```

Every required command must exit `0`. Missing tools, missing modules, daemon
unavailability, and dependency conflicts are failures or explicitly approved,
time-bounded exceptions; they are not passes. Generated Compose files and
generated shell helpers affected by a change must receive the equivalent
parse/syntax checks.

### Security review

The reviewer must confirm, as applicable:

- no fixed, weak, logged, or broadly readable secret is introduced;
- LAN remains disabled unless TLS, authentication, CIDR enforcement, and
  backend isolation are implemented and verified;
- untrusted values are grammar-validated and structurally serialized;
- writes remain within the approved output root and replacement is recoverable;
- containers run least-privileged with explicit resource bounds;
- images and dependencies are pinned, inventoried, and scanned;
- logs, fixtures, manifests, and gate output contain no credentials or
  sensitive prompt data;
- harness permissions match role authority and workers cannot delegate or
  write another role's memory.

Retain the reviewer, result, exceptions, and evidence location in the task or
pull request.

## Gate 2 — Release

Before release:

1. Re-run Gate 1 from a clean checkout on every supported Python version and
   supported harness host.
2. Build from locked dependencies and immutable image digests; retain SBOM,
   vulnerability scan, model provenance, licenses, and artifact checksums.
3. Generate and validate representative workspaces, including negative cases
   for missing model, invalid input, unsafe destination, weak secret, and
   incomplete LAN controls.
4. On an identified host, exercise every affected runtime path: start with
   bounded readiness, strict semantic smoke, stop, failed startup, rollback,
   backup/restore, and incident containment. Record model hash/quantization,
   image digest, CPU/RAM, configuration, p50/p95 latency, throughput, and peak
   memory where performance is claimed.
5. Confirm documentation and the capability matrix describe only implemented
   behavior and distinguish `structure valid`, `host ready`, and
   `runtime healthy`.

Release is blocked by a mutable dependency, unresolved critical/high finding,
failed recovery drill, unverified LAN control, misleading readiness claim, or
an exception without owner and expiry.

## Evidence honesty

Static parsing, unit tests, and source inspection may establish structure and
contract behavior only. They do not establish that an image exists, a model
loads, a process is healthy, a firewall rule is effective, credentials are
protected on the network, performance fits a host, or recovery works. Label
such results `NOT RUN` or `NOT VERIFIED` until live evidence exists. Never
convert tool absence, swallowed errors, placeholder metrics, or a written
report into a passing result.

## Periodic independent audit

Run a fresh independent audit at least monthly, before a production/LAN
release, after a major dependency/runtime/harness change, and after a security
or recovery incident. Audit the current checkout from zero; do not use prior
findings as the audit scope or mark findings as persistent/fixed. Record
platform, agent, model, operator, commit and dirty state, commands, static/live
limitations, severity counts, and artifact paths in `audits/INDEX.md`.

Every newly observed defect not covered by a standard must produce exactly one
tracked standards-improvement disposition: add a rule, strengthen a gate,
clarify a rule, retire a rule, or record only with rationale.
