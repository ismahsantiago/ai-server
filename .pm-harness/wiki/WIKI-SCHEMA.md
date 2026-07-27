# LLM Wiki — schema (how this wiki is maintained)

This directory implements the **LLM Wiki pattern** (Karpathy, 2026): instead of
re-reading and re-synthesizing project documents on every question (RAG-style),
agents **compile** knowledge once into structured, cross-referenced Markdown
pages and answer from the compiled layer. This file is the schema layer: it
tells any agent how to read, extend, and repair the wiki. It is normative
(HARNESS-SPEC §9).

## Three layers

1. **Sources (immutable)** — the project's raw documents: `docs/`, research
   notes, transcripts, specs, READMEs. The wiki NEVER edits sources; it cites
   them. List every ingested source in `INDEX.md → Sources`.
2. **Wiki (compiled)** — `wiki/pages/*.md`: LLM-maintained summaries, entity
   pages, decision pages, cross-references, and contradiction flags. Pages are
   the query surface: answer from here first, open sources only to verify or
   when the wiki is silent.
3. **Schema (this file)** — the maintenance contract. Changes to this file
   require Director approval (it is part of the harness contracts).

## Page contract

Every page in `wiki/pages/` is one topic (entity, concept, decision, area) and
carries this frontmatter:

```markdown
---
title: <topic, unique across the wiki>
kind: entity | concept | decision | area | contradiction
sources:            # every source document this page compiles from
  - docs/03-research.md
updated: YYYY-MM-DD
---
```

Body rules:

- Written in **English**, dense and factual; no filler prose.
- Cross-reference other pages with `[[page-file-name]]` (without `.md`). A
  link to a page that does not exist yet marks a page worth writing — the
  validator reports it so the gap is visible, not silent.
- When two sources contradict each other, do NOT pick a winner silently:
  record both claims with citations under a `## Contradiction` heading (or a
  dedicated `kind: contradiction` page) and flag it for the Director/owner.
- Facts carry their citation: `(source: docs/02-x.md §3)`.

## Maintenance protocol (who writes, when)

- **Compile on ingest**: when a new source document appears (or an existing
  one changes materially), the responsible agent updates the affected pages
  and `INDEX.md` in the same unit of work — synthesis happens once,
  incrementally, not at query time.
- **Compile on close**: closing any TASK that changes documented behavior
  (product rules, architecture, APIs, decisions) requires updating the wiki
  before the task transitions to `closed`. The `llm-wiki` skill
  (`.pm-harness/skills/llm-wiki/SKILL.md`) is the procedure.
- **Single index**: `INDEX.md` lists every page (one line each) and every
  ingested source. Agents load `INDEX.md` first and open only the pages they
  need.
- **Validation**: `python3 .pm-harness/bin/harness.py wiki check` verifies
  frontmatter, index coverage, and `[[link]]` targets. It must be clean (or
  its gaps explicitly accepted) before a documentation-touching task closes.

## What does NOT belong here

- Harness state (tasks, memory, ceremonies) — that lives in its own
  contracts; the wiki is about the *product/project* knowledge.
- Copies of source text — compile, don't duplicate. Quote at most a few lines
  with a citation.
- Secrets, credentials, or personal data from the project's data stores.
