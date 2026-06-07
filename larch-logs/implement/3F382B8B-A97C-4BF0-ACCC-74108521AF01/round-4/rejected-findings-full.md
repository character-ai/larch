### [rejected] FINDING_1

**Rejected subtype:** dismissed (0 YES)

### FINDING_1: Multi-round auto-apply defers Gate C approval
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Accepted/voted findings can rewrite `plan.txt` across multiple automatic review rounds before final Gate C operator approval, increasing blast radius for malicious or prompt-injected reviewer prose.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Accept as designed parity with /implement, or add per-round operator checkpoint / security-finding gate before auto-continuation


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_11

**Rejected subtype:** dismissed (0 YES)

### FINDING_11: Continuation-helper failure path is undefined
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: If `plan-review-continuation.sh` exits non-zero, SKILL routing is undefined and may skip required re-review or continue with stale state.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Define fail-closed SKILL routing on exit 2 and add harness coverage.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_14

**Rejected subtype:** dismissed (0 YES)

### FINDING_14: Successful re-tally preserves stale accepted-count env values
- **Reviewer(s)**: dyn-artifacts-output.txt
- **Severity**: latent
- **Concern**: After successful MainAgent re-tally, accepted-count KVs in `.step3-plan-review-result.env` / `.step3-review-result.env` can remain stale even though accepted findings were merged on disk, misleading env-based consumers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-artifacts-output.txt: On the `ok` path, recompute the four accepted-count KVs from `accepted-plan-findings.md` (reuse the counting helpers from `plan-review-loop.sh` or mirror `plan-review-continuation.sh`’s Python block) before writing both result env files; extend `test-persist-retally-step3-env.sh` to assert non-zero counts after a successful merge.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_15

**Rejected subtype:** neutral (YES below acceptance threshold)

### FINDING_15: Cumulative accepted findings use inconsistent deduplication
- **Reviewer(s)**: dyn-artifacts-output.txt
- **Severity**: important
- **Concern**: Automatic accumulation concatenates accepted findings while re-tally merging deduplicates exact byte blocks, allowing duplicate `### FINDING_N:` blocks in `accepted-plan-findings-all.md` and inflated final summary counts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-artifacts-output.txt: Unify cumulation on one idempotent merge (description-key or exact-block dedup, matching the OOS path) in both `_accumulate_round_accepted_all` and `_merge_retally_accepted_all`, and add a loop harness where round 2 re-tally merges a block already present from round 1’s accumulation.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0

### [rejected] FINDING_16

**Rejected subtype:** neutral (YES below acceptance threshold)

### FINDING_16: Multi-round plan-review lifecycle lacks a single normative contract
- **Reviewer(s)**: dyn-contracts-output.txt
- **Severity**: latent
- **Concern**: `plan-review.md` still centers on single-pass review and does not normatively define multi-round predicates, cap behavior, Gate B re-entry flow, or per-round versus cumulative artifact ownership.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-contracts-output.txt: Add a dedicated “Multi-round orchestration” section to `plan-review.md` (or elevate `plan-review-continuation.md` as a cited normative sibling) that documents predicates, cap semantics, Gate B → continuation → Step 3 re-entry flow, and artifact ownership; cross-link from `approval-gates.md` §Gate B shared post-apply pipeline step 9 instead of only pointing at `SKILL.md`.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0

### [rejected] FINDING_17

**Rejected subtype:** dismissed (0 YES)

### FINDING_17: Approval-gates cap prose still references per-tier behavior
- **Reviewer(s)**: dyn-contracts-output.txt
- **Severity**: nit
- **Concern**: `approval-gates.md` says review caps have “per-tier behavior” even though Part C flattened the cap to a uniform 5-round policy.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-contracts-output.txt: Replace “per-tier behavior” with language about uniform tier behavior and orchestrator-owned automatic continuation vs Gate C manual re-run; keep §Review-round cap as the single cap authority.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_18

**Rejected subtype:** dismissed (0 YES)

### FINDING_18: Auto-continuation sentinel hygiene is not covered by pause/resume tests
- **Reviewer(s)**: dyn-contracts-output.txt
- **Severity**: latent
- **Concern**: `--auto-continuation-entry` sentinel cleanup is only unit-tested, not covered by pause/resume, so pausing after Gate B on a continue path could resume into double-apply or skipped-continuation behavior without an end-to-end regression.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-contracts-output.txt: Add a pause/resume scenario that pauses after Gate B on a `PLAN_REVIEW_CONTINUE=true` path and asserts resume re-enters Step 3 without double-applying findings or skipping the continuation check.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_2

**Rejected subtype:** dismissed (0 YES)

### FINDING_2: Free-form concern text can falsely drive “high/important” continuation
- **Reviewer(s)**: cursor-specialist-security-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-contracts-output.txt
- **Severity**: latent
- **Concern**: Continuation recomputes high/important counts using mutable reviewer prose and fallback keyword matching, so text such as “not high priority” or unstructured severity can trigger another round and diverge from structured `IMPORTANT_ACCEPTED_COUNT`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Limit continuation to structured severity fields; compute size signals from trusted emit output not plan.txt; cap rounds when only fallback heuristics fire
  - From cursor-specialist-correctness-output.txt: Tighten fallback patterns or require structured Severity lines.
  - From cursor-specialist-edge-cases-output.txt: Tighten fallback to structured severity/title markers or negate patterns like not high.
  - From dyn-contracts-output.txt: Reuse the same counting function as `plan-review-loop.sh` for structured severity, or read `IMPORTANT_ACCEPTED_COUNT` from `.step3-review-result.env` and only apply concern-text fallback when that KV is absent; add a harness case where concern-text fallback fires but `IMPORTANT_ACCEPTED_COUNT=0` to lock expected behavior.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_3

**Rejected subtype:** dismissed (0 YES)

### FINDING_3: Mutable plan-size signals can force unnecessary continuation
- **Reviewer(s)**: cursor-specialist-security-output.txt, cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: The continuation heuristic can use mutable `plan.txt`-derived size/trailer signals, including `plan_lines > 120`, to classify SIMPLE plans as structural/large and force another round even when `/implement` would rely on diff-based structural signals.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Limit continuation to structured severity fields; compute size signals from trusted emit output not plan.txt; cap rounds when only fallback heuristics fire
  - From cursor-specialist-correctness-output.txt: Align with implement diff-based structural signal or document and test SIMPLE long-plan behavior.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_6

**Rejected subtype:** neutral (YES below acceptance threshold)

### FINDING_6: Degraded zero-finding panels can consume all auto-review rounds
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-stateflow-output.txt
- **Severity**: important
- **Concern**: A degraded panel can schedule another full review round even when no findings were accepted, allowing repeated timeout/degraded rounds to burn the cap and cost without plan movement.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Continue on degraded only when the round produced accepted findings or a non-aborted tally; else stop.
  - From cursor-specialist-edge-cases-output.txt: Continue on degraded only when there are accepted non-nit findings or a single degraded retry budget; align with /implement in-round retry semantics.
  - From dyn-stateflow-output.txt: Gate the `degraded-panel` continue predicate on evidence that the round produced actionable output (e.g. `ACCEPTED_COUNT > 0` or `NON_NIT_ACCEPTED_COUNT > 0`), or cap degraded-only auto-continuations to one follow-up round before requiring operator action at Gate C.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0

### [rejected] FINDING_7

**Rejected subtype:** neutral (YES below acceptance threshold)

### FINDING_7: Prompt-orchestrated multi-round loop lacks end-to-end guardrails
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, dyn-stateflow-output.txt, dyn-contracts-output.txt
- **Severity**: important
- **Concern**: The multi-round controller is prompt-orchestrated rather than enclosed in one driver, and current tests mostly cover helper units; missed orchestration steps could double-apply, skip continuation checks, or bypass Gate C without an integration failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Add stubbed Step3-GateB-continuation integration test.
  - From dyn-stateflow-output.txt: Add an integration harness that simulates two continuation cycles through `run-step3-review.sh` + Gate B sentinel files + `plan-review-continuation.sh`, asserting cap consumption, no duplicate `.gate-b-postapply-ready-*` apply, and preserved `accepted-plan-findings-all.md`.
  - From dyn-contracts-output.txt: Extend `test-design-structure.sh` with grep pins for the continuation block, `--auto-continuation-entry`, and “Do NOT write `.completed/step-3.5` on the continue path,” mirroring existing Gate B / cap contract pins.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0

### [rejected] FINDING_9

**Rejected subtype:** dismissed (0 YES)

### FINDING_9: HARD/default classification is treated as structural-large continuation
- **Reviewer(s)**: codex-specialist-correctness-output.txt, dyn-stateflow-output.txt, dyn-contracts-output.txt
- **Severity**: important
- **Concern**: `HARD` classification, including invalid or missing classification defaulting to `HARD`, can mark a small clean plan as structural/large and force automatic continuation on minimal accepted findings.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Derive structural/large only from concrete size/change signals, not HARD tier alone; add a HARD small-clean stop regression.
  - From dyn-stateflow-output.txt: Default invalid/missing classification to `SIMPLE` (conservative stop) or treat parse failure as `PLAN_REVIEW_CONTINUE=false` with a loud warning in `execution-issues.md`.
  - From dyn-contracts-output.txt: Align thresholds with `/implement` (at minimum `HIGH_ACCEPTED_COUNT >= 2`), add an accepted-count ≥ 8 continue path, and replace plan-metadata “structural” with a post–Gate-B delta signal (e.g., `diff_lines` / `diff_added` delta after apply) closer to `structural_loc >= 100`; update `SKILL.md`, `plan-review-continuation.md`, and `test-step3-review-cap.sh` together.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

