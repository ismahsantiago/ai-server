# ai-server quality standards

This directory is the canonical, version-controlled quality contract for the
generator, generated workspaces, runtime operations, documentation, and PM
Harness integration. Standards are preventive controls: findings from an
independent audit become stable rules, mechanical checks, and release evidence.

## Selective loading protocol

At task start, classify every affected area and load only this file,
[`MANIFESTO.md`](MANIFESTO.md), [`GATES.md`](GATES.md), and the applicable
documents below. Load an additional document whenever a change crosses its
boundary; security and operations are mandatory for any LAN, secret, container,
model, dependency, or release change.

| Change area | Load |
|---|---|
| Input handling, secrets, LAN, auth, containers, dependencies | [`SECURITY.md`](SECURITY.md) |
| Python architecture, rendering, filesystem writes, generated drift | [`CODE.md`](CODE.md) |
| Model sizing, readiness, benchmarks, runtime resources | [`PERFORMANCE.md`](PERFORMANCE.md) |
| CLI/operator interaction and generated helper behavior | [`DESIGN.md`](DESIGN.md) |
| Capability claims, readiness language, destructive product behavior | [`PRODUCT.md`](PRODUCT.md) |
| Compose, CI, observability, recovery, incident response | [`OPS.md`](OPS.md) |
| Distribution, licenses, models, images, third-party obligations | [`LEGAL.md`](LEGAL.md) |
| Routing, agent permissions, materialization, harness conformance | [`HARNESS.md`](HARNESS.md) |

When classification is uncertain, load the broader set and record the reason in
the task or pull request. A reviewer may require another document before Gate 1.

## Stable rule format

Every normative rule uses this shape:

```markdown
## STD-<AREA>-<NNN> — <imperative title>

<One testable requirement using MUST, MUST NOT, SHOULD, or MAY.>

**Verify mechanically:** <exact automated assertion or command where possible>

**Current finding origin:** `<finding-id>`.
```

- Rule IDs never change meaning and are never reused after removal.
- Requirements state observable behavior, not an implementation preference.
- Mechanical verification is mandatory whenever the behavior is machine
  observable. A manual check must name its reviewer and retained evidence.
- Origins point to the finding that established the rule. Rules remain
  normative after that audit artifact becomes historical.
- A change to a rule, command, or exception must be reviewed with the same
  rigor as the product behavior it governs.

## Precedence and evidence

Executable product contracts and the current checkout outrank prose. If a
standard conflicts with current behavior, the change does not silently waive
the standard: fix the behavior, amend the standard through review, or record a
time-bounded exception with owner, rationale, risk, and expiry.

Passing a static check proves only what that check exercised. Do not infer live
model availability, health, LAN safety, firewall enforcement, latency, memory
fit, recovery, or legal permission from static evidence.
