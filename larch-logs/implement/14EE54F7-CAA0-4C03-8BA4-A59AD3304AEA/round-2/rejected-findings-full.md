### [rejected] FINDING_12

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_12: Post-rebase verify rc=2 stall not covered end-to-end in ship-pr fix loop
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: Post-rebase verify returning rc=2 → `exit_stall` is tested only on an isolated gate helper, not through full `run_evaluate_failure` / `_stage_and_push` wiring. Regression in mapping rc=2 to stall could ship without failing CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add fix-loop integration expecting STALL_STEP head-changed and no push when verify returns 2 after rebase.
  - From cursor-specialist-plan-fidelity-output.txt: Extend to full ship-pr integration stub asserting exit_stall 10-head-changed/12-head-changed tokens.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_13

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_13: CI-fix push may ignore BEHIND_COUNT_RELIABLE and plain-push on unreliable zero count
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: important
- **Concern**: CI-fix push path may ignore `BEHIND_COUNT_RELIABLE` and treat fail-open `BEHIND_COUNT=0` as authoritative. A network/git/rev-list glitch during `ci-behind-count` fetch could yield unreliable zero and allow plain-push of a fix still behind main without rebase or post-rebase re-verify.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Parse BEHIND_COUNT_RELIABLE; abort push (return 1 / stall) when false; only rebase/push on reliable counts.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_17

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_17: test-ci-behind-count lacks fetch-failure / reliability harness
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: No test covers the default fetch path or fetch failure setting `BEHIND_COUNT_RELIABLE=false`. Fetch regression could break `--no-fetch` delegation assumptions in `ci-status` without harness signal.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add fetch-failure fixture without --no-fetch expecting BEHIND_COUNT_RELIABLE=false.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_18

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_18: hook-anti-read-poll poll state follows TMPDIR
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Poll state directory follows `TMPDIR`. A malicious `TMPDIR` in the same user session could redirect poll-state writes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Pin under ~/.cache/larch/ or validate TMPDIR before use.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_2

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_2: ci-status ignores BEHIND_COUNT_RELIABLE
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `ci-status` parses `BEHIND_COUNT` but not `BEHIND_COUNT_RELIABLE`. After fetch/rev-list failure, `ci-behind-count` can emit `BEHIND_COUNT=0` with `RELIABLE=false`; `ci-wait` / `ci-decide` may proceed or skip rebase while `ship-pr` refuses push on the same repo state, causing poll/fix deadlock or inconsistent routing until refs heal.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Parse BEHIND_COUNT_RELIABLE in ci-status (pending or fail-closed) or document and test intentional split.
  - From cursor-specialist-security-output.txt: Map BEHIND_COUNT_RELIABLE=false to pending / non-actionable behind state.
  - From cursor-specialist-edge-cases-output.txt: Parse BEHIND_COUNT_RELIABLE in ci-status.sh and align routing with ship-pr (pending/wait vs fail-closed push).


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_6

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_6: Plan fail-open behind-count vs ship-pr fail-closed push on unreliable count
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Documented plan/acceptance implies fail-open push when behind-count is unreliable (do not block push on count error), but `ship-pr` CI-fix staging can hard-block when `BEHIND_COUNT_RELIABLE=false` after a verified local fix (e.g., transient `git fetch` failure emits `BEHIND_COUNT=0` unreliable). Operators may expect push despite count errors; behavior is undocumented in tests and contradicts plan wording unless acceptance is updated.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Warn and proceed with behind=0 plain push per acceptance; or update issue acceptance to match documented fail-closed policy.
  - From cursor-specialist-testing-output.txt: Reconcile docs/acceptance with implementation and add ship-pr unreliable-count test.
  - From cursor-specialist-plan-fidelity-output.txt: Restore fail-open push semantics per plan, or amend plan/acceptance to document the reliability gate and add a fetch-failure harness case.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_7

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_7: Missing harness for BEHIND_COUNT_RELIABLE=false push refusal in CI-fix path
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: No end-to-end or fix-loop test asserts that CI-fix push is blocked when `BEHIND_COUNT_RELIABLE=false`. A regression could reintroduce push on fail-open count or remove the refusal branch without CI failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Add fix-loop test with unreliable stub and no push-kind output.
  - From cursor-specialist-correctness-output.txt: Add harness cases for final-attempt pending stall and BEHIND_COUNT_RELIABLE=false.
  - From cursor-specialist-testing-output.txt: Add ci_fix_behind_count_unreliable fix-loop case stubbing unreliable KV and assert no push helpers run.
  - From cursor-specialist-edge-cases-output.txt: Add fix-loop stub asserting push helpers not called when unreliable.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_9

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_9: Local verify failure does not continue waterfall tiers in the same attempt
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: After one vendor success, a local verify failure (e.g., Cursor exits 0 but jobs still fail) returns 1 without trying later waterfall tiers (codex/claude) until the next `_fix_attempt`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: On pre-stage verify failure continue waterfall or rotate start tier before returning 1.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

