---
name: llm-wiki
description: "Maintain the project's LLM Wiki (.pm-harness/wiki/): compile source documents into cross-referenced Markdown pages per WIKI-SCHEMA.md, update INDEX.md, flag contradictions, and validate with 'harness.py wiki check'. Use when ingesting new project docs, when closing a task that changes documented behavior, or when 'wiki check' reports gaps."
allowed-tools:
  - "bash"
  - "read"
  - "write"
  - "edit"
  - "glob"
  - "grep"
---

# llm-wiki — compile project knowledge into the wiki

The contract lives in `.pm-harness/wiki/WIKI-SCHEMA.md` (SPEC §9);
read it first and follow it verbatim. This skill is the procedure.

## Procedure

1. **Scope the delta.** Identify which sources are new or changed (compare
   `INDEX.md → Sources` against reality) or which closed task changed
   documented behavior.
2. **Compile, don't copy.** For each affected topic, create or update ONE page
   in `wiki/pages/` with the schema frontmatter (`title`, `kind`, `sources`,
   `updated`). Dense English prose, facts with citations, `[[links]]` to
   related pages. Never edit a source document.
3. **Flag contradictions.** Conflicting claims across sources are recorded
   side by side under `## Contradiction` (or a `kind: contradiction` page) —
   never silently resolved. Escalate product-relevant contradictions through
   the normal chain.
4. **Update the index.** Every touched page and every ingested source gets its
   line in `INDEX.md`.
5. **Validate.** `python3 .pm-harness/bin/harness.py wiki check` must exit 0.
   Unresolved `[[links]]` it reports are the backlog of pages worth writing —
   either write them now or leave them as visible gaps, never delete the link
   to silence the check.

## QA Scenarios

### Happy path
**Input**: "ingest docs/07-pricing.md into the wiki".
**Expected**: page(s) created/updated with correct frontmatter and citations,
`INDEX.md` lists the source and pages, validator clean.
**Verify**: `python3 .pm-harness/bin/harness.py wiki check` exits 0 and
`grep -q "07-pricing" .pm-harness/wiki/INDEX.md`.

### Error path
**Input**: two sources state incompatible retention policies.
**Expected**: both claims recorded with citations under a contradiction flag;
no silent winner; contradiction surfaced to the owner/Director.
**Verify**: the affected page contains a `## Contradiction` section citing
both sources.
