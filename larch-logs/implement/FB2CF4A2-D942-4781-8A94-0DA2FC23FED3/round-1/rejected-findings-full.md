### [rejected] FINDING_15

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_15: Multiline WARN values can diverge result-env and stdout contracts
- **Reviewer(s)**: dyn-kv-warnings-output.txt
- **Severity**: latent
- **Concern**: `WARN=` values are written to the result env without the same newline validation enforced by stdout `emit_kv`. A multiline warning could leave a complete env file but abort stdout emission under `set -euo pipefail`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-kv-warnings-output.txt: Sanitize or split warning text before appending to `WARN_LINES`, validate when building `_kvs`, and/or wrap the WARN `emit_kv` loop in `set +e` with explicit handling so one bad line cannot truncate the contract stream.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_17

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_17: Scoped thin-fence temp file is not cleaned up on failure
- **Reviewer(s)**: dyn-grep-scope-output.txt
- **Severity**: nit
- **Concern**: `assert_thin_fence` writes a scoped slice to an `mktemp` file but removes it only on the success path. Failing assertions can leave debris under `${TMPDIR:-/tmp}`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-grep-scope-output.txt: Use a `trap` on the scoped path (`trap 'rm -f "$subject"' RETURN` or an ERR trap) so cleanup runs on every exit from the function, or wrap scoped checks in a subshell whose temp file is always removed.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_19

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_19: Thin-fence positive checks are too broad
- **Reviewer(s)**: dyn-grep-scope-output.txt
- **Severity**: latent
- **Concern**: The thin-fence positives grep the whole extracted Step 3.6 region for `set +e` and `$?`, including prose after the bash fence. Documentation text could satisfy the check while the real assessor handoff loses rc capture.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-grep-scope-output.txt: Narrow the positive checks to the first fenced bash block (extract lines between the opening and closing ` ```bash ` pair inside the region) or anchor greps near `_assessor_out` / `_assessor_rc`.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_20

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_20: Gate-B bypass helper and markdown pin can drift independently
- **Reviewer(s)**: dyn-grep-scope-output.txt
- **Severity**: latent
- **Concern**: Gate-B bypass coverage is split across hand-maintained copies: the test helper and the markdown substring structural pin. CI does not assert that they remain identical, so one can drift while the other still passes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-grep-scope-output.txt: Have the structural pin source the same literal array the helper uses (shared bash fragment), or add a self-test that runs `assert_gate_b_bypass_branch_sentinels` on a synthetic SKILL snippet with a deliberately stripped bullet and expects failure (mirroring `run_thin_fence_self_tests`).


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_21

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_21: Gate-B bypass structural pin lacks a negative self-test
- **Reviewer(s)**: dyn-grep-scope-output.txt
- **Severity**: latent
- **Concern**: `assert_gate_b_bypass_branch_sentinels` lacks a controlled negative fixture, so delimiter typos or overly narrow extraction could weaken the pin without an explicit sensitivity test.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-grep-scope-output.txt: Add a minimal synthetic markdown fixture to `run_thin_fence_self_tests` (or a sibling function) that must fail when the three `: >` lines are removed from the `plan-size-trigger` bullet only.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_5

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_5: Step 3.6 classification warning visibility is split between stderr and WARN= channels
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Step 3.6 surfaces classification warnings on stderr, while postplan uses stdout `WARN=` KVs. Automated or quiet consumers that parse only `WARN=` may miss Step 3.6 defaulting context, and coverage for the cheap gate warning path is weak.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add apply_step3_6_handoff case asserting warning text on SIMPLE skip with bad classification
  - From cursor-specialist-edge-cases-output.txt: Document dual channels or emit WARN= at Step 3.6 cheap gate too.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_9

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_9: Step 3.6 region marker selection does not detect duplicate markers
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-grep-scope-output.txt
- **Severity**: nit
- **Concern**: Region bounds use the first matching start/end marker without asserting uniqueness. Duplicate or partial marker collisions could silently shrink or mis-aim the guarded region.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Fail unless exactly one start marker (or use paired anchor logic).
  - From dyn-grep-scope-output.txt: After resolving line numbers, assert uniqueness (`grep -cF` equals 1 for each marker) or fail when multiple start matches exist.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

