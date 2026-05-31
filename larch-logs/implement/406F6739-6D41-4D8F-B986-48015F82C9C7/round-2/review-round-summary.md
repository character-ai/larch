# Review Round 2

- Mode: `diff`
- 16 accepted, 9 rejected (9 exonerated)

## Accepted Findings

### FINDING_1: Cap-reached short-circuit skips plan-review/round-* cleanup
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt, dyn-shell-state-machine-output.txt
- **Severity**: important
- **Concern**: When `STEP3_REVIEW_CAP_REACHED=true`, the driver emits `cap-reached` without running the symlink-safe `plan-review/round-[0-9]*` cleanup that the pre-refactor inline fence ran on every Step 3 entry before the cap guard. Gate C / Gate A re-entries at cap can leave stale round forensics on disk and confuse later gates or multi-round summaries.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Run cleanup before the cap short-circuit on every entry; add test-run-step3-review cap-reached cleanup assertion
  - From cursor-specialist-edge-cases-output.txt: Hoist symlink-safe round cleanup before the cap-reached branch; add harness asserting round-* removal on cap-reached
  - From dyn-shell-state-machine-output.txt: Run the same symlink-safe `plan-review/round-*` cleanup before the cap-reached branch (or hoist cleanup above the `if [[ "$STEP3_REVIEW_CAP_REACHED" == true ]]` split) so cap-skipped entries match pre-refactor hygiene; add a harness case under `test-run-step3-review.sh` or `test-step3-review-cap.sh` that seeds `plan-review/round-1/` and asserts removal on cap-reached.


### FINDING_11: SECURITY.md omits trust model for `.step3-review-result.env`
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Security documentation still anchors on `.step3-plan-review-result.env` only; the new normalized Step 3 handoff file lacks explicit allowlisted-parse and symlink-refusal rules.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Add SECURITY.md bullet mirroring allowlisted parse + symlink refusal for .step3-review-result.env
  - From cursor-specialist-edge-cases-output.txt: Add bullet mirroring allowlist + symlink refusal for .step3-review-result.env


### FINDING_13: ROUND_NUM missing for main-agent re-tally classification path
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Main-agent re-tally still uses `${ROUNDS_COMPLETED:-$ROUND_NUM}` at SKILL.md:906, but the Step 3 orchestrator fence no longer sets `ROUND_NUM` after extraction. Empty `ROUNDS_COMPLETED` during `main-agent-vote-required` yields `plan-review/round-/findings-classification.tsv` or wrong round targeting.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Add ROUND_NUM to normalized env and orchestrator allowlist, or parse round from round-summary.env
  - From cursor-specialist-plan-fidelity-output.txt: Export inner ROUND_NUM (or equivalent) via .step3-review-result.env from run-step3-review.sh and source it in SKILL; do not use STEP3_REVIEW_ROUND_NUM as a substitute.


### FINDING_14: Driver coerces unexpected plan-review-loop rc+LOOP_STATUS pairs to panel-failed
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-shell-state-machine-output.txt
- **Severity**: important
- **Concern**: When `plan-review-loop.sh` exits non-zero with a `LOOP_STATUS` other than `panel-failed` or `main-agent-vote-required`, the driver overwrites `LOOP_STATUS` to `panel-failed`. Inline `main` only warned and preserved loop-reported statuses (e.g. `revision-failed`, `emit-plan-failed`, `plan-size-trigger`), changing Step 3 branch-matrix / Gate B routing vs stated preserve-observable-behavior acceptance.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Restore warn-only parity or document/test intentional coercion and align TALLY_PLAN_REVIEW_STATUS when forcing panel-failed
  - From dyn-shell-state-machine-output.txt: Either restore warn-only parity with `main`'s fence, or document and test the intentional coercion (and align `run-step3-review.md` + acceptance criteria); if coercion is kept, consider aligning `TALLY_PLAN_REVIEW_STATUS` when forcing `panel-failed`.


### FINDING_15: HARD cursor advance failure may consume cap slot without rollback
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: On HARD `write-cursor` failure the driver exits `1` after persisting a pending review round (incremented `review-round-count.txt`) without rollback. Operator retries can consume a cap slot without a panel run.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Roll back review-round-count on cursor-advance failure if slot consumption is not intended; add harness


### FINDING_18: Missing harness for HARD write-cursor / driver exit 1 failure
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: No CI coverage for HARD round-cursor advance failure (driver exit `1`, normalized env, orchestrator branch). Regression could reintroduce wrong-round launch or wrong abort semantics without signal.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Add stubbed snapshot-plan-round failure test for exit 1 and normalized env
  - From cursor-specialist-testing-output.txt: Stub failing write-cursor; assert driver rc, result env, and orchestrator outcome.
  - From cursor-specialist-plan-fidelity-output.txt: Add a test with a failing write-cursor stub asserting rc=1 and no plan-review-loop invocation.


### FINDING_19: Non-numeric `review-round-count.txt` handling untested
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Bad counter file content could be misread; warn-as-zero behavior at run-step3-review.sh:84-90 lacks harness coverage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Seed abc in review-round-count.txt; assert warn-as-zero and round-1 persist.


### FINDING_2: Driver exit 2 (argv/config failure) treated as panel-failed
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: The orchestrator maps any non-zero `run-step3-review.sh` return code to `LOOP_STATUS=panel-failed` except `main-agent-vote-required`. Driver exit `2` is argv/config failure (e.g. missing `--round-cap`), but Step 3 continues as if the review panel failed, hiding misconfiguration.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Branch on `_plan_review_rc` in SKILL (2=config error exit; 1=cursor/abort or panel-failed per contract; 0=normal)


### FINDING_20: `main-agent-vote-required` with non-zero loop rc untested
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Orchestrator could force `panel-failed` and break 0-judge adjudication when loop returns exit `1` with `LOOP_STATUS=main-agent-vote-required`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Stub LOOP_STATUS=main-agent-vote-required with exit 1; assert status preserved.


### FINDING_22: Structure pin misleading (source vs allowlisted read)
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `scripts/test-design-structure.sh` pin says `source` while SKILL uses allowlisted read of `.step3-review-result.env`, which may invite a future regression.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Rename pin to read allowlisted KVs from .step3-review-result.env


### FINDING_24: Missing `CLAUDE_PLUGIN_ROOT` precedence test for `phase_driver_resolve_plugin_root`
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: Wrong plugin root resolution in multi-plugin setups could load scripts from an unexpected tree; plan calls for precedence coverage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Assert CLAUDE_PLUGIN_ROOT overrides session-env and tree-walk.


### FINDING_3: HARD write-cursor failure no longer hard-stops Step 3; doc/contract drift
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, dyn-driver-orchestrator-boundary-output.txt
- **Severity**: important
- **Concern**: A HARD `write-cursor` I/O failure exits the driver with rc `1` after writing `panel-failed` to the normalized result env, but the SKILL fence overwrites/continues with `panel-failed` short-circuit prose instead of aborting the bash fence as on `main` and as `run-step3-review.md` still describes for exit `1`. Observable failure semantics and plan/doc parity diverge.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Reconcile with plan: keep orchestrator exit 1 on driver rc 1 or driver exit 0 with explicit status; document in run-step3-review.md
  - From cursor-specialist-correctness-output.txt: Align plan and doc with panel-failed continuation, or exit 1 from orchestrator fence on driver rc=1 cursor failure
  - From cursor-specialist-testing-output.txt: Align SKILL.md with intended contract; add harness for write-cursor failure asserting exit/branch behavior.
  - From dyn-driver-orchestrator-boundary-output.txt: Align `run-step3-review.md` (and any harness comments) with actual orchestrator behavior—exit `1` is a controlled `panel-failed` handoff, not a hard stop—or have the driver exit `0` after writing the normalized failure env so the rc override is unnecessary.


### FINDING_6: plan-review-loop.sh collector/FIFO change outside extract scope
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `plan-review-loop.sh` collector stderr FIFO / early-return changes are outside the stated Step 3 driver extract-only scope, expanding PR blast radius and coupling unrelated collector behavior to the driver refactor.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Revert here or split to a dedicated PR with its own harness justification
  - From cursor-specialist-plan-fidelity-output.txt: Split the collector change to its own PR or update the plan/acceptance to document and test it explicitly.


### FINDING_7: Collector non-zero exit changes LOOP_STATUS / round-count semantics vs main
- **Reviewer(s)**: dyn-fifo-rc-propagation-output.txt
- **Severity**: important
- **Concern**: Non-zero `collect-agent-results.sh` exit now triggers early `return` from `_run_plan_review_round`, mapping to `LOOP_STATUS=panel-failed` instead of allowing the exit-0 / zero-OK-slots path that could yield `degraded-empty-collector` on `main`. `run-step3-review.sh` rolls back `review-round-count.txt` for `degraded-empty-collector` but not `panel-failed`, so hard collector failures can consume a review round where they previously might not.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-fifo-rc-propagation-output.txt: Decide explicitly whether hard collector exit should be `panel-failed` or `degraded-empty-collector`; if parity with `main` is required, remove the early `return` and let the existing post-collect path classify (or map specific `_collect_rc` values to `degraded-empty-collector` before return). Document the chosen contract in `plan-review-loop.md` and add a harness case (stub collector `exit 1` with empty stdout) asserting `LOOP_STATUS` and `run-step3-review.sh` round-count rollback.
  - From dyn-fifo-rc-propagation-output.txt: Add a “Collector invocation” subsection describing the FIFO+`tee` stderr path, that non-zero collector exit aborts the round before aggregation/tally, and how that differs from exit-0 / all-slots-failed (still `degraded-empty-collector` via `test-plan-review-loop.sh:927-954).


### FINDING_8: Harness gaps for collector hard-fail / FIFO cleanup path
- **Reviewer(s)**: cursor-specialist-testing-output.txt, dyn-fifo-rc-propagation-output.txt
- **Severity**: latent
- **Concern**: New collector stderr/FIFO and `collect_rc` early-return paths lack failure-path tests (non-zero collect exit, fifo removal, `LOOP_STATUS` / round-summary propagation).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Stub collect exit 2; assert loop rc and skipped downstream steps.
  - From dyn-fifo-rc-propagation-output.txt: Add a case with a stub collector that `exit 1` before emitting records; assert `LOOP_STATUS=panel-failed`, absence of the fifo file, and (if preserving new semantics) that `run-step3-review` / round-count behavior matches the documented contract.


### FINDING_9: Duplicate cap-reached branch after re-sourcing `.step3-review-cap.env`
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: After writing cap state at lines 99–116, the non-cap branch re-sources `CAP_ENV` and repeats a cap-reached block (lines 147–150) that is unreachable in normal flow, adding duplicate skip breadcrumbs and harder-to-follow control flow in the highest-traffic driver.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Remove inner cap re-check; use state from lines 93-118 only
  - From cursor-specialist-correctness-output.txt: Remove block or document corruption-only guard


