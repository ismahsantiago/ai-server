# config/profiles/

Balanced runtime presets for a 12 GB RAM host.

## Canonical path

Profiles should be emitted by the generator into a workspace under
`generated/<preset-profile-access>/config/profiles/` and consumed through the
generated scripts.

## Legacy compatibility copies

The `.env` files in this root path are compatibility/examples kept for older
workflows. Prefer generated equivalents for new runs.

Legacy examples in this folder:

- `medium-fast.env` (lower latency, smaller context)
- `medium.env` (balanced default)
- `good.env` (better quality, higher memory)

Legacy apply helper: `scripts/use_profile.sh <profile-name>`.
