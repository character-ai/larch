## Proposed Design Outline

### Goals
- Close the six scope-anchor coverage and delimiter-hygiene gaps from issue #3547 in one pass.
- Make the staged scope anchor the single feature-context source across the plan-review pipeline.
- Bring pre-existing prompt-assembly paths up to the redact + untrusted-framing standard.

### Non-goals
- No changes to PR #3548 itself; this work lands after that PR merges (hard dependency).
- No new scope-anchor features beyond coverage of the existing pipeline.
- No behavior change for `[SCOPE-REDUCTION]` detection semantics — only detector dedup.

### Approach sketch
- `assess-plan-round.sh`: prefer `plan-review-scope-anchor.txt` in `resolve_feature_file()`; keep the legacy chain as defensive fallback.
- `tally-plan-review.sh`: accept and re-emit `SCOPE_ANCHOR_FILE` so MainAgent re-tally preservation is mechanical, not prose-dependent.
- `revise-plan-with-waterfall.sh`: wrap `<plan>` / `<findings>` blocks with the branch's untrusted-data framing convention.
- `check-scope-reduction-marker.sh`: collapse the duplicated stdin/`--file` Python detectors into one shared body.
- `launch-claude-subprocess.sh`: pipe `<context_file_N>` content through `redact-secrets.sh` and add untrusted framing.
- `SECURITY.md`: document the scope-anchor trust boundary.

### Surfaces in scope
- `skills/design/scripts/assess-plan-round.sh`, `skills/design/scripts/tally-plan-review.sh` (+ `scripts/lib-vote-tally.sh` if emission lives there)
- `skills/design/scripts/revise-plan-with-waterfall.sh`, `scripts/check-scope-reduction-marker.sh`, `scripts/launch-claude-subprocess.sh`
- `SECURITY.md`, plus the matching offline test harnesses for each touched script

### Open questions
- None.
