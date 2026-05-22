## Goal
Remove stale post-/design boundary references from sessionstart-health.sh, its doc, and its regression harness

## Implementation Plan
## Plan

Remove all references to the retired post-/design boundary model from the
sessionstart-health script, its doc, and its regression harness.

### Files to modify

**`scripts/sessionstart-health.sh`** (3 lines removed)
- Delete lines 139–141: the comment block "Issue-anchored cutover: …
  design-export/manifest.env … Do not emit the legacy post-design-boundary
  advisory here." The advisory code it described has already been removed; the
  comment itself is the last stale reference.

**`scripts/sessionstart-health.md`** (1 bullet removed + adjacent prose updated)
- Remove the "post-/design" bullet from the "Boundary advisories are emitted
  for:" list (current line 23). Only post-/review and post-/bump-version
  boundaries remain active.

**`scripts/test-sessionstart-health.md`** (1 phrase removed)
- Remove "post-/design manifest detection plus `.boundary-gate-passed` and
  `.run-cleaned-up` suppression," from the boundary-coverage sentence. The
  remaining sentence describes what the harness actually tests.

**`scripts/test-sessionstart-health.sh`** (cases 12 and 12b removed; cases 13,
15, 16 fixture cleanup)
- **Remove** Case 12 ("SessionStart does not emit legacy post-/design boundary
  for manifest.env alone") and Case 12b (".boundary-gate-passed still harmless
  when manifest exists"): these test the absence of an advisory that can no
  longer fire; deleting them removes stale fixture creation
  (`design-export/manifest.env`, `.boundary-gate-passed`).
- **Case 13** (".run-cleaned-up suppresses boundary advisories"): remove the
  `design-export/manifest.env` creation line; add
  `printf 'review summary\n' > "$impl/review-round-summary.md"` so the test
  has an active advisory (post-/review) for `.run-cleaned-up` to suppress.
  This keeps the case meaningful rather than trivially-passing on empty state.
- **Case 15** ("pending post-/bump-version boundary"): remove
  `design-export/manifest.env` creation line and the redundant
  `touch "$impl/.boundary-gate-passed"` (no longer a meaningful precondition
  for the bump advisory).
- **Case 16** ("pending review + bump boundaries concatenate"): remove
  `design-export/manifest.env` creation line; update the case description to
  remove the "no legacy design gate" clause.

### Approach
Minimal targeted removals: 3 comment lines from the .sh; one bullet and a
couple of doc lines from the two .md siblings; delete two test cases and clean
up fixture setup in three remaining cases; one fixture line added to Case 13.

### Edge cases
- Case 15b ("postbump-state.sh suppresses") reuses `impl` from Case 15 — no
  structural change needed, just ensure Case 15's cleanup doesn't break it.
- No `/implement` or other script depends on the removed comment lines.

### Acceptance
- `bash scripts/test-sessionstart-health.sh` passes (all remaining cases).
- `make lint` (which includes `test-sessionstart`) passes.
- `grep -rn "post-design-boundary\|boundary-gate-passed\|manifest\.env" scripts/sessionstart-health.sh scripts/sessionstart-health.md scripts/test-sessionstart-health.sh scripts/test-sessionstart-health.md` returns no hits.

## Acceptance

- `bash scripts/test-sessionstart-health.sh` passes (all remaining cases).
- `make lint` (which includes `test-sessionstart`) passes.
- `grep -rn "post-design-boundary\|boundary-gate-passed\|manifest\.env" scripts/sessionstart-health.sh scripts/sessionstart-health.md scripts/test-sessionstart-health.sh scripts/test-sessionstart-health.md` returns no hits.

diff_lines: 38

## Test plan
(no test plan section in plan-file)
