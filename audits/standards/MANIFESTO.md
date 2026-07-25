# ai-server quality manifesto

ai-server must make local model serving understandable, reproducible, and safe
for an operator on constrained hardware. Convenience never upgrades incomplete
evidence into a readiness or security claim.

## Product invariants

1. **Local-first, LAN fail-closed.** Localhost is the default. LAN is unavailable
   until strong external secrets, authenticated TLS, an enforced CIDR policy,
   backend isolation, and a verifiable preflight are all present.
2. **Generated output cannot destroy project-owned data.** Ordinary writes stay
   below `generated/`. Replacement requires generator ownership, rejects
   symlinks and boundary escapes, and is staged, atomic, and recoverable.
3. **The selected model is the model the container can load.** Host and
   container paths, artifact identity, quantization, checksum, and memory
   requirements form one validated contract before startup.
4. **Readiness claims match evidence.** `structure valid`, `host ready`, and
   `runtime healthy` are distinct. Smoke checks fail on transport, HTTP, auth,
   or semantic errors; static review never implies live success.
5. **Runs are attributable and recoverable.** Dependencies and images are
   pinned, measurements identify model/runtime/host configuration, and release
   procedures include tested stop, rollback, restore, and incident response.

## Principles

- Fail closed at trust, filesystem, network, and readiness boundaries.
- Prefer structured parsing and serialization over textual interpolation.
- Treat exit codes, manifests, generated files, and documentation as public
  product contracts.
- Grant each container and harness role only the privileges it needs.
- Preserve evidence honestly: `NOT RUN` and `NOT MEASURED` are valid outcomes;
  placeholders are not proof.

## Definition of Done

A change is done only when its applicable standards are loaded, acceptance
criteria and adversarial cases are tested, Gate 1 passes, security review is
recorded where applicable, documentation matches executable behavior, and
evidence identifies whether checks were static or live. A release additionally
passes Gate 2 with pinned provenance, runtime evidence for affected serving
paths, and recovery evidence. Known failures, unchecked requirements, or
unverified LAN/runtime claims keep the change incomplete.
