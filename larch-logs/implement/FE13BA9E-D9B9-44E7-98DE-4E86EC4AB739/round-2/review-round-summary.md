# Review Round 2

- Mode: `diff`
- 8 accepted, 0 rejected (0 neutral)

## Accepted Findings

### FINDING_1: Postplan `clear_stale` deletes raw pending before promotion
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, dyn-dyn-dialectic-lifecycle-output.txt
- **Severity**: important
- **Concern**: When `plan.txt` bytes change during postplan (validator auto-fix, emit drift, inline retry), `clear_stale()` unlinks `.dialectic-raw-pending.json` before `step2b_drafter_main` can call `dialectic-promote-candidates`. Drafter-detected forks are silently dropped; Gate C never debates them despite acceptance requiring post-postplan promotion keyed to the final plan fingerprint.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Do not delete raw pending in clear_stale on plan-rewrite; clear only at drafter start and after successful promotion; promote before clear or re-validate raw JSON against final plan
  - From cursor-specialist-correctness-output.txt: Reorder postplan vs promotion; add integration test for postplan mutation + promotion fingerprint
  - From cursor-specialist-edge-cases-output.txt: Preserve raw pending through postplan rewrite until promote consumes it with final fingerprint; split clear_stale paths for promoted vs pending artifacts
  - From cursor-specialist-testing-output.txt: Promote immediately after POSTPLAN_RC=0 before pre-promotion clear-stale, or make clear_stale preserve RAW_PENDING until promotion succeeds; re-key fingerprint from final plan.txt on promote.
  - From dyn-dyn-dialectic-lifecycle-output.txt: Promote from `.dialectic-raw-pending.json` into `dialectic-clarifier-candidates.json` using the final `plan.txt` fingerprint before calling `dialectic-clear-stale` on hash change, or re-validate and retain the sidecar when only mechanical plan edits occurred; log a warning when a parsed sidecar is discarded.


### FINDING_2: Ambiguous free-form manual debate defaults `drafter_pick` to `option_a`
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, dyn-dyn-dialectic-lifecycle-output.txt
- **Severity**: important
- **Concern**: `_infer_manual_drafter_pick` infers pick via substring search in `plan.txt` and defaults to `option_a` when both option strings appear (common for architectural forks). That mis-binds CHOSEN/ALTERNATIVE ballot semantics and misstates **Drafter pick** / **Panel lean** in the advisory digest when the operator lists the non-plan side first or both options appear in the plan body.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Require debate by candidate-id or fail with shape help; strengthen inference beyond substring presence; never silently default to option_a
  - From cursor-specialist-edge-cases-output.txt: Fail closed with shape help on ambiguous inference or require explicit candidate-id / plan-aligned pick
  - From cursor-specialist-testing-output.txt: Infer pick from plan alignment when both strings match; add ambiguous-case regression test; avoid unconditional option_a default.
  - From dyn-dyn-dialectic-lifecycle-output.txt: Require explicit `drafter_pick` in free-form manual requests, or match only against fingerprint-valid auto candidates (by id/title/option pair) and reject ambiguous free-form shapes instead of defaulting to `option_a`.


### FINDING_3: Missing plan-listed `test_design_lifecycle.py` dialectic integration coverage
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, dyn-dyn-dialectic-lifecycle-output.txt
- **Severity**: important
- **Concern**: `test_design_dialectic.py` covers unit-level promote/clear behavior, but `test_design_lifecycle.py` still lacks assertions on `_compose_drafter_prompt()` dialectic instructions, drafter-start artifact cleanup, `step2b_drafter_main` promoting only after `POSTPLAN_RC=0`, and postplan-mutation fingerprint binding. Regressions in promotion gate or cleanup would pass CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Add plan-specified test_design_lifecycle.py coverage including postplan promotion fingerprint
  - From cursor-specialist-edge-cases-output.txt: Add lifecycle tests for step2b_drafter_main promotion fingerprint and artifact cleanup
  - From cursor-specialist-testing-output.txt: Add lifecycle tests for dialectic prompt text, stale-artifact cleanup at drafter start, and promote-only-on-POSTPLAN_RC=0 with final fingerprint.
  - From dyn-dyn-dialectic-lifecycle-output.txt: Add the plan-listed `test_design_lifecycle.py` cases (prompt excerpt, cleanup of dialectic artifacts at drafter start, promote-only-after-postplan-ok, postplan-mutation fingerprint) as integration tests around `step2b_drafter_main`.


### FINDING_6: Manual-only Gate C re-entry skips cached manual digest
- **Reviewer(s)**: codex-generic-output.txt
- **Severity**: important
- **Concern**: `_run_gatec()` computes `manual_cached`, but returns immediately when auto candidates are absent, so a valid `dialectic-manual-candidates.json` plus `dialectic-clarifier-digest.md` is not printed on Gate C re-entry. Scenario: operator uses `Other` with `debate storage: A vs B` when no drafter auto candidates exist, `dialectic-manual` writes a valid manual digest, then resume/re-entry runs `dialectic-gatec`; the final plan preview appears without the manual clarifier digest.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-generic-output.txt: Check and print `manual_cached` before the `if candidates is None` return, or make the no-auto branch preserve and emit a valid manual cached digest before clearing stale auto artifacts.


### FINDING_7: Slugified candidate IDs are not deduplicated across capped decisions
- **Reviewer(s)**: codex-generic-output.txt
- **Severity**: important
- **Concern**: Two decisions with the same explicit `id`, or titles that slugify to the same value, reuse the same debater output paths and dict keys, and judge vote parsing maps both `DECISION_1` and `DECISION_2` to the same `decision_id`. Scenario: two candidates both slug to `storage`; `dialectic-debater-storage-option_a.txt` is shared, steelmen overwrite each other, and votes for both decisions are counted together.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-generic-output.txt: Reject duplicate normalized IDs during `normalize_candidates_payload()`, or append the decision index when a slug collides so every candidate ID is unique before launch, ballot assembly, and cache-key generation.


### FINDING_8: Manual cache short-circuits auto debate for uncovered auto candidates
- **Reviewer(s)**: dyn-dyn-dialectic-lifecycle-output.txt
- **Severity**: important
- **Concern**: After a successful manual Gate C debate, `_run_gatec()` returns the cached manual digest whenever `manual_cached` is true, without checking whether auto debate completed for the full `dialectic-clarifier-candidates.json` set. If the Step 4 tail auto path fail-opened (budget/launch failure) and the operator then triggered manual `Other` debate for one fork, subsequent `dialectic-gatec` calls (including `resume@4b` tail recovery) never retry auto debate, so remaining drafter-declared forks never get panel coverage until a plan rewrite clears manual artifacts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-dialectic-lifecycle-output.txt: Treat manual cache as authoritative only when it covers the same `ordered_candidate_ids` as live auto candidates (or auto `state` is `complete`/`fallback`); otherwise allow auto `dialectic-gatec` to run for uncovered auto candidates.


### FINDING_9: `dialectic-clear-stale` failures swallowed at settle/postplan choke points
- **Reviewer(s)**: dyn-dyn-dialectic-lifecycle-output.txt
- **Severity**: important
- **Concern**: Post-dedup and post-postplan choke points invoke `dialectic-clear-stale` with `|| true`, swallowing non-zero CLI failures. A failed clear can leave stale `dialectic-clarifier-candidates.json`, digest, and status artifacts attached to a rewritten `plan.txt`, so Gate C may debate obsolete forks or replay stale digests without CI signal. `python/plan_review.py:1721` has the same ignored-return pattern.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-dialectic-lifecycle-output.txt: Drop `|| true`, fail the settle/postplan path when `dialectic-clear-stale` exits non-zero, and add integration tests that assert the hook ran after mocked plan rewrites.


### FINDING_10: Fail-open debate leaves orphan `state=running` status sidecar
- **Reviewer(s)**: dyn-dyn-dialectic-lifecycle-output.txt
- **Severity**: important
- **Concern**: On fail-open debate paths, `_run_gatec()` writes `dialectic-clarifier-status.json` with `state="running"` before launching subprocesses, but `_run_debate()` failure only bumps generation and returns without updating status to `fallback` or clearing the running marker. Orphan `state=running` sidecars can survive across turns while generation has advanced, confusing resume/pause operators and any future logic that keys off status state.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-dialectic-lifecycle-output.txt: On fail-open exit, write `state="fallback"` (or remove status) via `write_if_generation_matches` after the generation bump, matching the disposition enum used elsewhere.


