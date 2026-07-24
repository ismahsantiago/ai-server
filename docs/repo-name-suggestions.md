# Repository name suggestions

This document proposes candidate names for this project before public-facing
publication.

## Naming criteria

1. **Intent clarity**: name should signal generator-first local serving.
2. **Scope fit**: broad enough for multiple setups (chat/coding/RAG), not only
   one model.
3. **Memorability**: short, readable, easy to type.
4. **Searchability**: low ambiguity with unrelated projects.
5. **Future-safe**: can survive minor product expansion.

## Candidates

| Candidate | Why it works | Trade-off |
|---|---|---|
| `ai-server-generator` | Most explicit match to current product identity and CLI package focus. | Longer than brand-style names. |
| `local-ai-server-kit` | Communicates practical setup kit for local serving users. | Slightly less explicit about generation workflow. |
| `safe-local-ai-server` | Highlights safety defaults and localhost-first posture. | More policy-oriented, less build-tool oriented. |
| `gen-local-ai-server` | Short, modern, and generation-centric. | Abbreviation (`gen`) may be less clear to some users. |
| `localhost-ai-server` | Emphasizes secure default posture immediately. | May under-signal that LAN mode exists as opt-in. |
| `ai-server-workspace-gen` | Strongly communicates emitted workspace artifact model. | Most verbose option. |

## Recommended choice

**Recommendation: `ai-server-generator`**

Reason:

- It is the clearest statement of what the repository currently does.
- It aligns with existing Python package naming (`ai-server-generator`) and
  module usage (`ai_server_generator`).
- It keeps room for future setup families while staying precise today.

If a shorter brand-style name is needed later, keep this as a clear technical
repository name and add branding in docs/releases rather than reducing clarity
at the repository boundary.
