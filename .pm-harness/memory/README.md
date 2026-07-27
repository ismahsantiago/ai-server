# memory/ — per-agent memory stores

One `{agent}/` directory per agent, holding `*.md` notes (mandatory
frontmatter: id, type, scope, importance, signature) and a `MEMORY.md` index.
Format, recall score, and ownership rules: `../HARNESS-SPEC.md` §2. Only the
owning agent writes into its own store. Write/recall with
`python3 ../bin/harness.py memory add|recall ...`.
