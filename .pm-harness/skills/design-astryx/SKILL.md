---
name: design-astryx
description: "Default design-system workflow for web UI work: build frontends with Astryx (https://astryx.atmeta.com/ — Meta's open-source, agent-ready React + StyleX design system) via its CLI and MCP server. Use when scaffolding UI, adding components/pages/themes, or when the design area starts any web frontend task. Not for: non-web UIs or projects where the Director chose another design system."
allowed-tools:
  - "bash"
  - "read"
  - "write"
  - "edit"
  - "glob"
  - "grep"
---

# design-astryx — Astryx-first web UI workflow

Astryx is the harness **default** for web UI (HARNESS-SPEC, design area
defaults): 160+ accessible, themeable React components on StyleX, with
agent-readable docs, a self-describing CLI, and an MCP server. Deviating from
this default is a Director decision recorded in the kickoff/spec.

## Setup (once per project)

```bash
npm install @astryxdesign/core @astryxdesign/theme-neutral
npm install -D @astryxdesign/cli
```

Add the CLI script to `package.json` so agents invoke it without path errors:

```json
"scripts": { "astryx": "node node_modules/@astryxdesign/cli/bin/astryx.mjs" }
```

## Agent workflow (CLI-first — deterministic, no scraping)

1. **Discover**: `npm run astryx -- manifest --json` returns the
   self-describing command spec (every command, flag, and response type).
   Trust it over any memorized command list.
2. **Component docs**: `npm run astryx -- component <Name>` (full docs +
   composition hints); `npm run astryx -- component --list` to enumerate.
3. **Scaffold pages**: `npm run astryx -- template <name>` emits full page
   source for production-ready templates (dashboards, settings, etc.).
4. **Customize**: `npm run astryx -- swizzle <Component>` to take ownership of
   a component; themes via the theme packages / theme generator.
5. **Verify**: the project's normal build/lint/test gates (Gate 1) — Astryx
   needs no build plugin, only CSS imports plus the theme provider.

## MCP server (optional, richer for interactive sessions)

Astryx ships an HTTP MCP server exposing docs/components to MCP-compatible
agents. To wire it, get the current endpoint from the official docs
(https://astryx.atmeta.com/ → AI/agent tooling) — do not hardcode a guessed
URL — then register it project-locally (e.g. `.mcp.json` on Claude Code, the
platform's MCP config elsewhere). The CLI workflow above is the fallback and
must always work without the MCP server.

## Rules

- Prefer composing existing Astryx components over hand-rolled CSS; swizzle
  before forking.
- Respect the theme cascade: brand changes go through theme tokens, not
  per-component overrides.
- Accessibility comes from using the components as documented — do not strip
  their aria/keyboard behavior.

## QA Scenarios

### Happy path
**Input**: "scaffold a settings page for the web app".
**Expected**: Astryx installed (or already present), page generated from an
Astryx template, themed, passing the project's build/lint gates.
**Verify**: `npm run astryx -- manifest --json` exits 0 and the build gate
passes with the new page.

### Error path
**Input**: the target project is a CLI tool with no web frontend.
**Expected**: skill declines and returns the task — Astryx does not apply;
the design area proposes the appropriate surface instead.
**Verify**: no Astryx packages added to `package.json`.
