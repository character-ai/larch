### FINDING_1: Missing committed Step 3 state helper
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-prompt-sync-output.txt
- **Severity**: important
- **Concern**: `skills/design/scripts/design-step3-state.sh` is referenced by SKILL.md and multiple harnesses as an executable runtime helper, but is untracked/absent from HEAD. Fresh clones, CI, or plugin installs can fail Step 3 entry, Gate-B-bypass sentinel writes, direct-review re-entry, and committed-executable structure pins.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-prompt-sync-output.txt: Address the concern above.


### FINDING_10: Missing OOS restore and stale artifact clearing tests
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Failure-path OOS restore and pre-round stale artifact clearing lack tests. Gate-C re-entry or panel/tally failures could truncate cumulative OOS or reuse stale accepted plan findings, affecting later Gate B ballots.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_12: Stale multi-round success banner
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: `scripts/test-design-multi-round-integration.sh` was internally renamed to single-pass but still prints a multi-round success banner.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_13: Drift baseline corruption or tampering can disable drift guard
- **Reviewer(s)**: cursor-specialist-security-output.txt, dyn-drift-fence-output.txt
- **Severity**: latent
- **Concern**: If `drift-baseline.env` is unreadable, malformed, empty, or a symlink, drift evaluation warns and skips without reliably re-seeding or failing closed. A corrupted or tampered baseline can permanently disable the cumulative drift guard for the session.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt, dyn-drift-fence-output.txt: Address the concern above.


### FINDING_14: Revise artifact publish/security boundary remains too permissive
- **Reviewer(s)**: cursor-specialist-security-output.txt, dyn-artifact-boundary-output.txt
- **Severity**: latent
- **Concern**: Step 3 no longer invokes `revise-plan-with-waterfall.sh`, but revise artifact paths, including prompt surfaces under `plan-review/round-N/revise/`, remain allowlisted/documented/pinned for publication. This leaves an asymmetric public-log boundary after top-level rendered plan prompts were denied.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt, dyn-artifact-boundary-output.txt: Address the concern above.


### FINDING_15: Gate-C cap path can erase cumulative OOS
- **Reviewer(s)**: dyn-state-machine-output.txt
- **Severity**: important
- **Concern**: On the outer Gate-C cap path, `run-step3-review.sh` deletes `oos-accepted-design.md` with Gate-B-facing artifacts. Since no new review repopulates it, cumulative accepted OOS can be erased before Step 5b reads it.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-state-machine-output.txt: Address the concern above.


### FINDING_16: Step 3 preview sentinel contract is split and unenforced
- **Reviewer(s)**: dyn-state-machine-output.txt, dyn-prompt-sync-output.txt
- **Severity**: important
- **Concern**: SKILL.md says Step 3 preview is first-entry-only and gated by `.step3-entry-plan-printed`, but the fenced block calls the pure renderer `emit-design-plan-preview.sh --variant step3` directly. Sentinel ownership appears to live in `run-step3-review.sh --preview-only`, so re-entry skip behavior is not mechanically enforced and docs disagree.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-state-machine-output.txt, dyn-prompt-sync-output.txt: Address the concern above.


### FINDING_19: Write-run-params harness docs and removed manual Gate B flag tests are inconsistent
- **Reviewer(s)**: dyn-shell-contract-output.txt
- **Severity**: important
- **Concern**: `scripts/test-write-run-params.md` still documents legacy manual Gate B flag persistence/rejection, but the shell harness removed those cases and only rejects another removed flag. This creates a false regression-test contract for removed manual flag behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-shell-contract-output.txt: Address the concern above.


### FINDING_2: Stale inter-round revise helper remains in active Step 3 prompt surface
- **Reviewer(s)**: cursor-specialist-structure-output.txt, dyn-state-machine-output.txt, dyn-prompt-sync-output.txt
- **Severity**: important
- **Concern**: `skills/design/SKILL.md` still describes `revise-plan-with-waterfall.sh` as a forthcoming between-round integration helper even though Step 3 is now single-pass with Gate B as the only apply point. This can mislead orchestrators into believing inter-round patch-apply remains active.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, dyn-state-machine-output.txt, dyn-prompt-sync-output.txt: Address the concern above.


### FINDING_20: Malformed schema key list in write-run-params contract
- **Reviewer(s)**: dyn-shell-contract-output.txt
- **Severity**: nit
- **Concern**: `scripts/write-run-params.md` has a malformed trailing comma before the period in the schema key list, which can mislead readers or copy-paste edits.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-shell-contract-output.txt: Address the concern above.


### FINDING_23: Validator-failure path misses initial Step 2b drift baseline
- **Reviewer(s)**: dyn-drift-fence-output.txt
- **Severity**: important
- **Concern**: If initial Step 2b exits for validator defects before plan-size and drift snapshot run, the baseline is captured only after Fix-and-retry. Growth from the first draft to the repaired plan is invisible to the drift guard.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-drift-fence-output.txt: Address the concern above.


### FINDING_28: Issue-anchored plan preview contract disagrees with SKILL/config docs
- **Reviewer(s)**: dyn-prompt-sync-output.txt
- **Severity**: latent
- **Concern**: `docs/issue-anchored-plan.md` still names `run-step3-review.sh --preview-only` as the Step 3 preview mechanism, while other docs/SKILL point to direct `emit-design-plan-preview.sh --variant step3`. Auditors and harness authors may follow the wrong sentinel owner.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-prompt-sync-output.txt: Address the concern above.


### FINDING_29: SECURITY preview sentinel owner doc disagrees with SKILL
- **Reviewer(s)**: dyn-prompt-sync-output.txt
- **Severity**: latent
- **Concern**: `SECURITY.md` still documents `run-step3-review.sh --preview-only` as the Step 3 preview sentinel owner, while SKILL uses direct `emit-design-plan-preview.sh`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-prompt-sync-output.txt: Address the concern above.


### FINDING_30: Scope-anchor prose still names revise as a live Step 3 consumer
- **Reviewer(s)**: dyn-prompt-sync-output.txt
- **Severity**: latent
- **Concern**: SKILL.md still lists “revise” among Step 3 scope-anchor consumers, implying a live inter-round revision step after the single-pass removal.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-prompt-sync-output.txt: Address the concern above.


### FINDING_31: SECURITY lacks explicit gitleaks/log posture for orphaned revise artifacts
- **Reviewer(s)**: dyn-artifact-boundary-output.txt
- **Severity**: latent
- **Concern**: SECURITY.md notes historical revise artifacts but does not clearly state gitleaks posture or whether newly published `plan-review/round-N/revise/*` material remains intentionally scannable/allowlisted after inter-round patch-apply was removed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-artifact-boundary-output.txt: Address the concern above.


### FINDING_4: Stale multi-round revise harness comments and env exports
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `test-plan-review-loop.sh` still mentions multi-round revise-plan behavior and exports unused `LARCH_PLAN_REVIEW_REVISE_SH`, confusing future maintenance after single-pass refactor.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


### FINDING_5: Stale Gate-B-bypass pause/resume failure message
- **Reviewer(s)**: cursor-specialist-structure-output.txt, dyn-prompt-sync-output.txt
- **Severity**: nit
- **Concern**: `test-design-pause-resume.sh` still references removed plan-size-trigger `LOOP_STATUS` in a failure message, creating misleading diagnostics for Gate-B-bypass pause tests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, dyn-prompt-sync-output.txt: Address the concern above.


### FINDING_6: Python-missing warning is noisy despite awk fallback
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `check-plan-size.sh` emits an unconditional `python3-unavailable` warning on every call when python3 is missing, even when the awk ratio fallback is usable, causing noisy execution issues.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


### FINDING_8: Missing precedence tests for hard/partition over drift
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Plan-size tests do not pin that hard threshold and partition routing take precedence over drift. A regression could emit exit 14/drift prompting instead of exit 12 hard Split/Cancel or exit 13 partition handling when multiple triggers are true.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_9: Missing invalid drift multiple coercion test
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Invalid `LARCH_DESIGN_DRIFT_MULTIPLE` coercion to default `2` is not regression-tested, so typoed env values could silently alter drift sensitivity or prompts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


