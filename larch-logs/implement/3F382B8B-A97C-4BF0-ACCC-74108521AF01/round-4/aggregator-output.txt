### FINDING_1: Multi-round auto-apply defers Gate C approval
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Accepted/voted findings can rewrite `plan.txt` across multiple automatic review rounds before final Gate C operator approval, increasing blast radius for malicious or prompt-injected reviewer prose.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Accept as designed parity with /implement, or add per-round operator checkpoint / security-finding gate before auto-continuation

### FINDING_2: Free-form concern text can falsely drive “high/important” continuation
- **Reviewer(s)**: cursor-specialist-security-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-contracts-output.txt
- **Severity**: latent
- **Concern**: Continuation recomputes high/important counts using mutable reviewer prose and fallback keyword matching, so text such as “not high priority” or unstructured severity can trigger another round and diverge from structured `IMPORTANT_ACCEPTED_COUNT`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Limit continuation to structured severity fields; compute size signals from trusted emit output not plan.txt; cap rounds when only fallback heuristics fire
  - From cursor-specialist-correctness-output.txt: Tighten fallback patterns or require structured Severity lines.
  - From cursor-specialist-edge-cases-output.txt: Tighten fallback to structured severity/title markers or negate patterns like not high.
  - From dyn-contracts-output.txt: Reuse the same counting function as `plan-review-loop.sh` for structured severity, or read `IMPORTANT_ACCEPTED_COUNT` from `.step3-review-result.env` and only apply concern-text fallback when that KV is absent; add a harness case where concern-text fallback fires but `IMPORTANT_ACCEPTED_COUNT=0` to lock expected behavior.

### FINDING_3: Mutable plan-size signals can force unnecessary continuation
- **Reviewer(s)**: cursor-specialist-security-output.txt, cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: The continuation heuristic can use mutable `plan.txt`-derived size/trailer signals, including `plan_lines > 120`, to classify SIMPLE plans as structural/large and force another round even when `/implement` would rely on diff-based structural signals.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Limit continuation to structured severity fields; compute size signals from trusted emit output not plan.txt; cap rounds when only fallback heuristics fire
  - From cursor-specialist-correctness-output.txt: Align with implement diff-based structural signal or document and test SIMPLE long-plan behavior.

### FINDING_4: [OUT_OF_SCOPE] Security OOS detector misses bold Focus area field
- **Reviewer(s)**: codex-specialist-security-output.txt
- **Severity**: important
- **Concern**: The security OOS detector may fail to hold accepted OOS blocks using the documented `- **Focus area**: security` form, allowing security OOS material into public artifacts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-security-output.txt: Recognize the documented bold Focus area field in is_security_block and add a regression fixture using the exact accepted OOS template.

### FINDING_5: [OUT_OF_SCOPE] Single-important continuation threshold diverges from `/implement`
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, dyn-stateflow-output.txt, dyn-artifacts-output.txt, dyn-contracts-output.txt
- **Severity**: important
- **Concern**: The continuation predicate fires on one important/high finding (`HIGH_ACCEPTED_COUNT > 0`) while the referenced `/implement` heuristic and issue plan use `important-accepted >= 2`, increasing automatic rounds and cost for small otherwise-converged changes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Use HIGH_ACCEPTED_COUNT >= 2 and add harness coverage for the boundary.
  - From cursor-specialist-correctness-output.txt: Add test-plan-review-continuation cases or extend test-step3-review-cap.sh.
  - From dyn-stateflow-output.txt: Align the predicate with `/implement` (`HIGH_ACCEPTED_COUNT >= 2`, optionally plus plan-size/`diff_lines` analogues), or document the asymmetry as a deliberate `/design` policy and add a harness case for the 1-important-finding stop/continue boundary.
  - From dyn-contracts-output.txt: Align thresholds with `/implement` (at minimum `HIGH_ACCEPTED_COUNT >= 2`), add an accepted-count ≥ 8 continue path, and replace plan-metadata “structural” with a post–Gate-B delta signal (e.g., `diff_lines` / `diff_added` delta after apply) closer to `structural_loc >= 100`; update `SKILL.md`, `plan-review-continuation.md`, and `test-step3-review-cap.sh` together.

### FINDING_6: Degraded zero-finding panels can consume all auto-review rounds
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-stateflow-output.txt
- **Severity**: important
- **Concern**: A degraded panel can schedule another full review round even when no findings were accepted, allowing repeated timeout/degraded rounds to burn the cap and cost without plan movement.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Continue on degraded only when the round produced accepted findings or a non-aborted tally; else stop.
  - From cursor-specialist-edge-cases-output.txt: Continue on degraded only when there are accepted non-nit findings or a single degraded retry budget; align with /implement in-round retry semantics.
  - From dyn-stateflow-output.txt: Gate the `degraded-panel` continue predicate on evidence that the round produced actionable output (e.g. `ACCEPTED_COUNT > 0` or `NON_NIT_ACCEPTED_COUNT > 0`), or cap degraded-only auto-continuations to one follow-up round before requiring operator action at Gate C.

### FINDING_7: Prompt-orchestrated multi-round loop lacks end-to-end guardrails
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, dyn-stateflow-output.txt, dyn-contracts-output.txt
- **Severity**: important
- **Concern**: The multi-round controller is prompt-orchestrated rather than enclosed in one driver, and current tests mostly cover helper units; missed orchestration steps could double-apply, skip continuation checks, or bypass Gate C without an integration failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Add stubbed Step3-GateB-continuation integration test.
  - From dyn-stateflow-output.txt: Add an integration harness that simulates two continuation cycles through `run-step3-review.sh` + Gate B sentinel files + `plan-review-continuation.sh`, asserting cap consumption, no duplicate `.gate-b-postapply-ready-*` apply, and preserved `accepted-plan-findings-all.md`.
  - From dyn-contracts-output.txt: Extend `test-design-structure.sh` with grep pins for the continuation block, `--auto-continuation-entry`, and “Do NOT write `.completed/step-3.5` on the continue path,” mirroring existing Gate B / cap contract pins.

### FINDING_8: [OUT_OF_SCOPE] Automatic continuation deletes prior round snapshots
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, dyn-stateflow-output.txt, dyn-contracts-output.txt
- **Severity**: latent
- **Concern**: Each Step 3 re-entry removes prior `plan-review/round-*` directories, so multi-round runs lose per-round forensic artifacts even though cumulative accepted findings survive.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Consider preserving round dirs on auto-continuation or snapshot before delete.
  - From dyn-stateflow-output.txt: Stop wholesale `rm -rf` of prior `plan-review/round-N/` trees on auto-continuation entry (only remove the upcoming round slot), or snapshot rounds to monotonically numbered directories that are never deleted until design publish.

### FINDING_9: HARD/default classification is treated as structural-large continuation
- **Reviewer(s)**: codex-specialist-correctness-output.txt, dyn-stateflow-output.txt, dyn-contracts-output.txt
- **Severity**: important
- **Concern**: `HARD` classification, including invalid or missing classification defaulting to `HARD`, can mark a small clean plan as structural/large and force automatic continuation on minimal accepted findings.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Derive structural/large only from concrete size/change signals, not HARD tier alone; add a HARD small-clean stop regression.
  - From dyn-stateflow-output.txt: Default invalid/missing classification to `SIMPLE` (conservative stop) or treat parse failure as `PLAN_REVIEW_CONTINUE=false` with a loud warning in `execution-issues.md`.
  - From dyn-contracts-output.txt: Align thresholds with `/implement` (at minimum `HIGH_ACCEPTED_COUNT >= 2`), add an accepted-count ≥ 8 continue path, and replace plan-metadata “structural” with a post–Gate-B delta signal (e.g., `diff_lines` / `diff_added` delta after apply) closer to `structural_loc >= 100`; update `SKILL.md`, `plan-review-continuation.md`, and `test-step3-review-cap.sh` together.

### FINDING_10: Manual Gate C re-run can retain stale cumulative artifacts
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, codex-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Manual Step 3/Gate C re-entry does not consistently reset cumulative in-scope and OOS accepted artifacts, so stale prior-round findings or OOS items can be counted, summarized, or filed after a fresh review.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Clear cumulative accepted/OOS artifacts on manual Step 3 re-entry (new design-step3-state action or Gate C hook); preserve accumulation only for auto-continuation-entry.
  - From codex-specialist-edge-cases-output.txt: Clear oos-accepted-design.md and .oos-accepted-design.prev.md on direct-review-entry while preserving them for auto-continuation-entry.

### FINDING_11: Continuation-helper failure path is undefined
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: If `plan-review-continuation.sh` exits non-zero, SKILL routing is undefined and may skip required re-review or continue with stale state.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Define fail-closed SKILL routing on exit 2 and add harness coverage.

### FINDING_12: New Makefile test target is missing from harness shards
- **Reviewer(s)**: cursor-specialist-testing-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `test-persist-retally-step3-env` is not included in any `test-harnesses-N` shard, so shard coverage and `make lint`/CI can fail or omit the new regression harness.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add test-persist-retally-step3-env to an appropriate harness shard and document in docs/linting.md
  - From codex-specialist-testing-output.txt: Add test-persist-retally-step3-env to an appropriate test-harnesses-N prerequisite and update docs if needed.

### FINDING_13: MainAgent re-tally can drop prior-round accepted OOS items
- **Reviewer(s)**: dyn-artifacts-output.txt
- **Severity**: important
- **Concern**: On the `main-agent-vote-required` path, successful re-tally rewrites only current-round accepted OOS and lacks the in-scope cumulative merge equivalent, so earlier-round OOS acceptances can disappear from summary and filing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-artifacts-output.txt: After successful MainAgent re-tally, merge `oos-accepted-design.md` into a cumulative OOS artifact the same way in-scope findings are handled (e.g., call `_accumulate_round_oos` with the saved `.oos-accepted-design.prev.md`, or add an OOS merge helper in `persist-retally-step3-env.sh` using the existing description-key dedup), and add a multi-round harness case with prior-round OOS plus a later-round `main-agent-vote-required` re-tally.

### FINDING_14: Successful re-tally preserves stale accepted-count env values
- **Reviewer(s)**: dyn-artifacts-output.txt
- **Severity**: latent
- **Concern**: After successful MainAgent re-tally, accepted-count KVs in `.step3-plan-review-result.env` / `.step3-review-result.env` can remain stale even though accepted findings were merged on disk, misleading env-based consumers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-artifacts-output.txt: On the `ok` path, recompute the four accepted-count KVs from `accepted-plan-findings.md` (reuse the counting helpers from `plan-review-loop.sh` or mirror `plan-review-continuation.sh`’s Python block) before writing both result env files; extend `test-persist-retally-step3-env.sh` to assert non-zero counts after a successful merge.

### FINDING_15: Cumulative accepted findings use inconsistent deduplication
- **Reviewer(s)**: dyn-artifacts-output.txt
- **Severity**: important
- **Concern**: Automatic accumulation concatenates accepted findings while re-tally merging deduplicates exact byte blocks, allowing duplicate `### FINDING_N:` blocks in `accepted-plan-findings-all.md` and inflated final summary counts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-artifacts-output.txt: Unify cumulation on one idempotent merge (description-key or exact-block dedup, matching the OOS path) in both `_accumulate_round_accepted_all` and `_merge_retally_accepted_all`, and add a loop harness where round 2 re-tally merges a block already present from round 1’s accumulation.

### FINDING_16: Multi-round plan-review lifecycle lacks a single normative contract
- **Reviewer(s)**: dyn-contracts-output.txt
- **Severity**: latent
- **Concern**: `plan-review.md` still centers on single-pass review and does not normatively define multi-round predicates, cap behavior, Gate B re-entry flow, or per-round versus cumulative artifact ownership.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-contracts-output.txt: Add a dedicated “Multi-round orchestration” section to `plan-review.md` (or elevate `plan-review-continuation.md` as a cited normative sibling) that documents predicates, cap semantics, Gate B → continuation → Step 3 re-entry flow, and artifact ownership; cross-link from `approval-gates.md` §Gate B shared post-apply pipeline step 9 instead of only pointing at `SKILL.md`.

### FINDING_17: Approval-gates cap prose still references per-tier behavior
- **Reviewer(s)**: dyn-contracts-output.txt
- **Severity**: nit
- **Concern**: `approval-gates.md` says review caps have “per-tier behavior” even though Part C flattened the cap to a uniform 5-round policy.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-contracts-output.txt: Replace “per-tier behavior” with language about uniform tier behavior and orchestrator-owned automatic continuation vs Gate C manual re-run; keep §Review-round cap as the single cap authority.

### FINDING_18: Auto-continuation sentinel hygiene is not covered by pause/resume tests
- **Reviewer(s)**: dyn-contracts-output.txt
- **Severity**: latent
- **Concern**: `--auto-continuation-entry` sentinel cleanup is only unit-tested, not covered by pause/resume, so pausing after Gate B on a continue path could resume into double-apply or skipped-continuation behavior without an end-to-end regression.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-contracts-output.txt: Add a pause/resume scenario that pauses after Gate B on a `PLAN_REVIEW_CONTINUE=true` path and asserts resume re-enters Step 3 without double-applying findings or skipping the continuation check.

### FINDING_19: [OUT_OF_SCOPE] OOS-loss test stub does not match production no-judge behavior
- **Reviewer(s)**: dyn-artifacts-output.txt
- **Severity**: nit
- **Concern**: The `main-agent-vote-required` OOS test pre-writes `oos-accepted-design.md`, so it does not exercise the production path where `tally-plan-review.sh` exits with zero eligible judges without writing OOS.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-artifacts-output.txt: Address the concern above.

### FINDING_20: [OUT_OF_SCOPE] Cap breadcrumb wording is stale
- **Reviewer(s)**: dyn-contracts-output.txt
- **Severity**: nit
- **Concern**: The driver cap breadcrumb still describes continuing to Step 3b/Gate C even though the happy-path cap stop now preserves artifacts via `plan-review-continuation.sh`; only the blocked sixth-entry path should hit cap-reached cleanup.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-contracts-output.txt: Address the concern above.
