# Review Round 1

- Mode: `diff`
- 4 accepted, 11 rejected (3 neutral)

## Accepted Findings

### FINDING_10: Final-summary glue lacks direct Review Phase Detail regression coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Existing tests can pass even if `render-final-summary.sh` fails to append the required Review Phase Detail section after plan-review rounds.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add a harness case with plan-review/round-1 artifacts + timing ledger; run render-final-summary.sh --post-publish-only; assert final-summary.md contains ## Review Phase Detail and expected table rows.
  - From codex-specialist-testing-output.txt: Add a render-final-summary harness fixture that asserts the final summary contains the Review Phase Detail section and representative row.


### FINDING_17: Unguarded `jq` makes both-externals-absent dispatch fail hard
- **Reviewer(s)**: dyn-code-robustness-output.txt
- **Severity**: important
- **Concern**: The new manifest row path in `dispatch-plan-review-panel.sh` calls `jq -nc` under `set -euo pipefail` without a guard, introducing a hard dependency in a degraded path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-code-robustness-output.txt: Guard with `command -v jq` and fall back to a small Python NDJSON append (or printf a single known-safe JSON line) before exiting, matching the best-effort posture used elsewhere.


### FINDING_2: Security OOS aggregate counts can leak into public final summary
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: important
- **Concern**: Security-tagged accepted OOS prose is held back from public artifacts, but aggregate OOS accepted/rejected counts can still be written into round metadata and surfaced in the GitHub-visible Review Phase Detail.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: When deriving tally keys in `write-design-round-meta.sh` (or when composing the renderer input), exclude security-tagged OOS rows using the same `is_security_block` logic as tally/compose, or subtract them from `OOS_ACCEPTED_COUNT` / `OOS_REJECTED_COUNT` before writing `round-meta.json`.


### FINDING_7: Malformed `voting-tally.md` prevents TSV fallback and yields zero counts
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: When `voting-tally.md` exists but is empty, malformed, or unparseable, the writer skips the `findings-classification.tsv` fallback and can emit plausible all-zero Review Phase Detail counts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Fall back to TSV when MD parse is all-zero and TSV has rows, or omit round-meta when sources conflict.
  - From codex-specialist-correctness-output.txt: Have the tally parser report valid-table/data detection and fall back to findings-classification.tsv when the primary tally is absent or unparseable.
  - From codex-specialist-edge-cases-output.txt: Detect unusable tally parsing and fall back to the round-local findings-classification.tsv before emitting zero counts.


