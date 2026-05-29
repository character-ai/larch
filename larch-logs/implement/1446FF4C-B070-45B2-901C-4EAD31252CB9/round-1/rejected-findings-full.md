### [rejected] FINDING_21

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_21: default 180s scout timeout may be too low for `--read-tools` large diffs
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: 180s default timeout may be too low for tool-based reads of large staged diffs. Claude `--read-tools` exceeds 180s; scout fail-opens to 0 dynamic reviewers indistinguishable from intentional empty.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Raise scout timeout for read-tools path, or add logging/status distinguishing timeout-on-large-diff from empty manifest.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_5

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_5: duplicated fenced-JSON probing vs post-winner validation
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: `tier_raw_is_scout_json` duplicates fenced JSON probing that the post-winner validation block repeats. Future probe/validation changes can diverge, causing waterfall to accept raw that later emits parse-failed or vice versa.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Factor one normalization helper shared by probe and post-winner path, or add a harness tying probe success to downstream jq success.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_6

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_6: scout contract doc lost invariant bullets
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Contract doc removed many prior invariant bullets when adding waterfall/staging notes. Contributors lose quick reference for validation-failure semantics, WARN truncation, and raw sidecar behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Restore concise bullets for unchanged post-winner validation and fail-open statuses alongside new waterfall documentation.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_7

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_7: scout waterfall ignores `--cursor-present` (no Cursor tier)
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: Scout waterfall is Codex then Claude only; `--cursor-present` is ignored despite issue acceptance calling for Codex → Cursor → Claude on the scout. `/design` or `/implement` with `--codex-present false` and `--cursor-present true` never runs a Cursor scout tier; only Claude runs, so availability does not match the stated acceptance when Codex is down but Cursor is up.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Implement a Cursor tier when launch-review can read staged context outside the repo, or update issue acceptance to scope Codex to Cursor to Claude to the review panel only.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

