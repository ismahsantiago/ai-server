---
id: mem-pm-orchestrator-0019
type: decision
scope: project
created: 2026-07-26
ttl_days: null
importance: 3
tags: [concurrency, file-ownership, process]
signature: "006984d4"
---

Ruling 2026-07-25 for concurrent tasks in one tree (TASK-0008, TASK-0009, TASK-0011 live simultaneously): split shared append-mostly files BY BULLET AND BY PAGE, not by file. CHANGELOG.md — each task appends its own task-scoped bullet under [Unreleased], never edits another's. Wiki — split by page; INDEX.md lines are appended, never reordered. scripts/ belongs to TASK-0008; standards/IMPROVEMENT.md APR numbers are taken next-free with a re-read immediately before writing. Whole-file boundaries that stay hard: ai_server_generator/ and tests/test_*.py to TASK-0008; templates/ and tests/golden/ to TASK-0011. General rule: whoever writes second re-reads first, and never caches a read of a shared file across a long execution.
