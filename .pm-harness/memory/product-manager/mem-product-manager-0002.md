---
id: mem-product-manager-0002
type: feedback
scope: /ai-server/product-manager
created: 2026-07-26
ttl_days: null
importance: 4
tags: [plan-review, acceptance-criteria, self-improvement, TASK-0010]
signature: "a520f8a6"
---

Review-quality pattern observed on TASK-0010, flagged by pm-orchestrator after the executor corrected product-manager twice in one task. Honest assessment: one clear substantive correction, one refinement, and a shared root cause worth naming.

CORRECTION (substantive): product-manager approved a concurrency-guard acceptance criterion asserting 'git status --porcelain ai_server_generator/ profiles/ templates/ tests/' is empty at delivery. product-analyst corrected it to baseline-relative (capture at task start, diff at delivery), because the assertion was ALREADY false at the time it was written - concurrent engineering work on TASK-0008 had modified templates/chat/README.md.j2 and tests/golden/chat-ornith-medium-localhost/README.md. An absolute assertion would have failed at delivery for reasons TASK-0010 could neither cause nor fix, and would have proved nothing about attribution, which was the actual intent. The executor's version was strictly stronger. Adopted.

REFINEMENT: product-manager's finding required the macOS ruling to assert neither branch AND to state engineering's reported detection fact. Under a naive grep those two requirements are in tension. product-analyst split the check into exclusion (no assertion outside branch blocks) plus attribution (every assertion inside the shared-context block must carry a TASK-000 citation). Better mechanics for the same intent.

ROOT CAUSE (the actual pattern, and it is a pattern, not a coincidence): product-manager reviews acceptance criteria for mechanical CHECKABILITY without verifying the ENVIRONMENT those criteria will execute in. An AC can be perfectly well-formed as a command and still be unsatisfiable in the working tree it will run against. Both events share this shape: the reviewer reasoned about the assertion's form, not about the state of the repository at delivery time.

CORRECTIVE RULE for future plan-review passes (SPEC 12.5): before approving any AC that asserts a command's OUTPUT (empty git status, exit code, byte-equality, a count), RUN that command against the current tree and record its actual result. If it does not already hold, the AC must be baseline-relative or conditional, never absolute. This applies with extra force whenever concurrent tasks share the working tree - on TASK-0010 there were three (TASK-0008, TASK-0009, TASK-0011).

Secondary note: the two corrections came from the executor, not from the manager, which is the correct direction for a healthy single-filter review (SPEC 4.1) - the reviewer is not supposed to be the only source of rigor. The concern is not that the executor corrected the manager; it is that both corrections had the same avoidable cause.
