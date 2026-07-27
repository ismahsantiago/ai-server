# escalations/pending/ — queue of escalations to the Director

Only the PM Orchestrator writes here (it is the single filter to the
Director). Note format (frontmatter with channel: session|audio|email,
blocking) and per-level authority limits: `../../HARNESS-SPEC.md` §4. When
resolved, the note moves to `../resolved/` with the decision appended.
