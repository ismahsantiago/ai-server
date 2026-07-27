# ceremonies/ — ceremony minutes

One `{YYYY-MM-DD}-{type}.md` file per ceremony (standup | decision | showcase
| retro), each with its `state/CER-*.json` manifest. Inputs and outputs per
type: `../HARNESS-SPEC.md` §5.

`executive-summary.md` (at the `.pm-harness/` root) is regenerated at the
close of any ceremony or on demand, and must keep these fixed sections:

```
# Executive Summary — {project} · {date}
## One-line status
## Facts
## Pending for the Director
## Next
```
