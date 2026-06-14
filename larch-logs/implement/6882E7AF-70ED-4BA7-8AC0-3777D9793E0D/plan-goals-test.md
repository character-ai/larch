## Goal
Implement issue #4303: [IMPLEMENTING] [OOS] Implement/orchestrator reference-doc drift + validation/quality fixes — 5 items.

## Implementation Plan
## Plan

- Treat the supplied approach synthesis as `NO_SKETCHES`.
- Use direct repository inspection.
- Keep changes small.
- Do not modify reviewer prompts.
- Preserve existing warning-only behavior for rebalance feasibility.

## Files to modify/create

### UPDATED: skills/shared/orchestrator-never.md

- Extend NEVER #3 with an explicit premature-notification recovery carve-out in the existing application guidance.
- State that the carve-out applies only after a premature empty `<task-notification>` fires while the underlying child process is still running.
- Reuse the pinned recovery wording:
  - `only sanctioned exception to the Bash polling-loop ban is one re-launched immediate-background completion waiter`
  - `one Bash run_in_background task with until <condition>; do sleep N; done`
- State that this exact waiter:
  - is not a progress-observation probe
  - is not a banned backgrounded watcher loop
  - is the sole sanctioned exception to the ZERO-call wait window for this premature-notification recovery case
- Extend NEVER #4 with the matching narrow exception so the same waiter is not classified as a forbidden Bash polling loop or result-file polling loop.
- Keep the existing `ZERO progress-observation tool calls` and other pinned literals intact.

### UPDATED: AGENTS.md

- Change the Monitor/polling bullet cross-reference from `skills/implement/SKILL.md` NEVER #9 to NEVER #8.
- Do not otherwise rewrite the bullet.

### UPDATED: skills/implement/references/stall-recovery.md

- In Step 18a, beside the `protected-path` warning guidance, add `submodule-restricted`.
- Use the current SKILL.md contract, not the stale inline-recovery wording:
  - `FAILURE_CLASS=submodule-restricted`
  - `RESUME_HINT=none`
  - Warning text: `**⚠ /implement: implementer bailed on submodule-restricted path; submodule edits are blocked for Main Claude too. No automatic inline recovery will run.**`
- Update Step 18a sub-step 4 so the first-detection warning policy explicitly authorizes both:
  - the existing `protected-path` first-detection warning
  - the new `submodule-restricted` first-detection warning
- Update Step 18a sub-step 5 so retry semantics stay class-specific:
  - keep existing `protected-path` `step2-impl` retry behavior unchanged
  - state that `submodule-restricted` uses `RESUME_HINT=none`
  - state that `submodule-restricted` does not dispatch `step2-impl`
  - state that no inline Step 2 repair runs for `submodule-restricted`
- Do not leave `submodule-restricted` nested under, or implied by, the `protected-path` recovery path.

### UPDATED: python/research_eval.py

- Add `"blocking"` to `_ALLOWED_SEVERITIES`.
- Leave JSONL and TSV normalization logic unchanged.
- Keep lower-casing behavior for severities.

### UPDATED: python/test_research_eval.py

- Add JSONL coverage for `blocking`.
- Add TSV coverage for `blocking`.
- Assert normalized output keeps `blocking`.
- Prefer extending `test_structured_jsonl_tsv_and_sentinel` or adding a focused test near it.

### UPDATED: .claude/skills/rebalance-test-harnesses/scripts/rebalance.py

- Replace the pre-pack heuristic with a direct post-pack spread check.
- Change `_check_feasibility` to accept packed shards plus timing data, for example:
  - `new_shards: dict[int, list[str]]`
  - `medians: dict[str, float]`
  - `balance_threshold: float`
- Compute each packed shard total with `sum(medians.get(target, 0.0) for target in targets)`.
- Compute `spread = max(totals) - min(totals)`.
- Emit no warning when:
  - there are no shards
  - there are no totals
  - `spread <= balance_threshold`
- Emit the warning when `spread > balance_threshold`.
- Move the call to after `new_shards = pack(...)`.
- Update warning text to report:
  - estimated packed spread
  - configured threshold
  - heaviest shard and total
  - lightest shard and total
- Remove the old `ideal_shard` and `threshold_half` heuristic output.

### UPDATED: python/test_rebalance_script.py

- Update `_feasibility_output` to call `pack(...)` or pass packed shard dictionaries directly.
- Replace assertions for `Heaviest packed target`, `Ideal shard time`, and `Threshold half`.
- Add a regression case where a dominant target would trigger the old heuristic but the packed spread is within threshold, and assert no warning.
- Add a case where the packed spread exceeds threshold without relying on the old dominant-singleton heuristic, and assert warning.
- Keep orphan median coverage by asserting shard totals ignore targets not present in the packed shard layout.

### UPDATED: .claude/skills/rebalance-test-harnesses/scripts/rebalance.md

- Update the Feasibility preflight section.
- Show the new call order:
  - select measured workload
  - pack shards
  - check packed spread
- Remove references to heaviest target, ideal shard time, and threshold half.
- State that orphan timing rows remain ignored because totals are computed from packed shard targets.

### UPDATED: .claude/skills/rebalance-test-harnesses/SKILL.md

- Update Step 3 to match the script behavior.
- State that packing runs before the warning-only feasibility check.
- State that the feasibility check evaluates packed shard totals and configured threshold.
- State that orphan timing rows remain ignored because totals come from packed shard targets.
- Keep this prompt aligned with `.claude/skills/rebalance-test-harnesses/scripts/rebalance.md`.

## Edge cases

- `submodule-restricted` must not promise inline recovery. Current `SKILL.md` says Main Claude is also blocked.
- `submodule-restricted` must not inherit `protected-path` `step2-impl` retry semantics.
- Step 18a first-detection warning policy must explicitly include `submodule-restricted`, not only `protected-path`.
- `blocking` must work in both JSONL and TSV structured reviewer paths.
- Rebalance warning must stay warning-only. It must not abort the script.
- Missing timing data for `extras` should contribute `0.0` seconds, matching existing estimated-spread behavior.
- Empty shard data must not raise `ValueError` from `max()` or `min()`.
- The premature-notification waiter exception must apply only after an empty `<task-notification>` fires early while the child is still running.

## Failure modes

- Exact-literal tests may fail if pinned strings in `orchestrator-never.md` change. Add text without removing pinned literals.
- Rebalance tests may become brittle if they assert full warning text. Prefer key substrings.
- The feature text contains stale submodule inline-recovery wording. Follow inspected `SKILL.md` and `stall-recovery-report.sh` behavior.
- Prompt drift can remain if `.claude/skills/rebalance-test-harnesses/SKILL.md` still describes pre-pack feasibility after script changes.
- Stall-recovery drift can remain if Step 18a sub-steps 4 and 5 keep protected-path-only language while a separate `submodule-restricted` bullet is added elsewhere.

## Testing strategy

- Run targeted tests:
  - `python3 -m pytest python/test_research_eval.py python/test_rebalance_script.py`
  - `bash scripts/test-implement-anti-polling-rule.sh`
  - `bash scripts/test-design-structure.sh`
- Run repository-relevant checks:
  - `bash scripts/relevant-checks.sh`

## Acceptance

- `orchestrator-never.md` NEVER #3 contains an explicit premature-notification recovery carve-out with pinned wording.
- `orchestrator-never.md` NEVER #4 contains a matching narrow exception for the same waiter.
- `AGENTS.md` Monitor/polling bullet cross-reference reads "NEVER #8" (was NEVER #9).
- `stall-recovery.md` Step 18a documents `submodule-restricted` with `RESUME_HINT=none` and the correct warning text.
- `python/research_eval.py` `_ALLOWED_SEVERITIES` includes `"blocking"`.
- `python/test_research_eval.py` has JSONL and TSV test cases for `blocking` severity that pass.
- `rebalance.py` `_check_feasibility` runs after `pack()` and uses spread from packed shard totals.
- `test_rebalance_script.py` assertions align with the new post-pack feasibility check.
- `rebalance.md` and `SKILL.md` describe pack-then-check order.
- All targeted tests pass.

diff_lines: 135

## Test plan
(no test plan section in plan-file)
