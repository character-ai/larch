## Proposed Design Outline

### Goals
- Stop design-log publish from committing raw plan-review reviewer transcripts at the top level of `larch-logs/design/<run-id>/`.
- Align design-log policy with the round-N gate and implement-log policy (#3504): `findings.md` / `voting-tally.md` are canonical; raw reviewer transcripts are excluded.
- Remove the dead `codex-plan-*` lib pattern and replace fictional test fixtures with real producer names.

### Non-goals
- No change to round-N staging behavior for real producers (`codex-primary-plan-*` is already excluded via the catch-all).
- No exclusion of HARD-only sketch / dialectic / plan-quality-assessor transcripts (out of scope; a reviewer may file as OOS).
- No flip of the top-level denylist to an allowlist; no change to vote-output (`*-vote-output.txt`) inclusion.

### Approach sketch
- Extend `design_artifact_excluded()` (denylist) in `design-log-publish.sh` with explicit patterns for `cursor-plan-*-output.txt`, `codex-primary-plan-*-output.txt`, `claude-plan-*-output.txt` (static + dynamic covered by `*`), plus only the sidecar suffixes real producers actually emit (verify to avoid adding new dead patterns).
- Fix `lib-design-round-artifacts.sh`: dead `codex-plan-*-output.txt` → `codex-primary-plan-*-output.txt`.
- Replace fictional fixtures with real names in `test-lib-design-round-artifacts.sh`; add a top-level exclusion assertion in `test-design-log-publish.sh`.
- Update the two `.md` sibling contracts in the same change.

### Surfaces in scope
- `scripts/design-log-publish.sh`, `scripts/lib-design-round-artifacts.sh`
- `scripts/test-design-log-publish.sh`, `scripts/test-lib-design-round-artifacts.sh`
- `scripts/design-log-publish.md`, `scripts/lib-design-round-artifacts.md`

### Open questions
- None.
