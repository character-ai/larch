# Review Round 1

- Mode: `diff`
- 3 accepted, 0 rejected (0 neutral)

## Accepted Findings

### FINDING_1: Step 6 change-detection failures seed wrong stall step and unallowlisted bail reason
- **Reviewer(s)**: cursor-specialist-correctness, codex-specialist-correctness, dyn-dyn-step6-routing
- **Severity**: important
- **Concern**: On malformed/missing `FILES_CHANGED` or failed `check-changes`, `_step6_entry_seed_stall()` seeds durable stall state with `stall_step="7"` and `bail_reason="review-change-detection-failed"` even though the failure occurs during Step 6 change detection, before the Step 7 commit leg. `stall_recovery._classify_text()` maps only steps `"3"` and `"6"` to `contract-failure`, so these stalls fall through to `unrecoverable` / `fallback` instead of the Step 6 contract path. The bail token is also absent from `STALL_RECOVERY_BAIL_REASON_TOKENS` and related allowlists, so stall reports may redact or reject the real cause. Operators can see a Step 7 stall before the commit leg ran.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Use stall_step=6 with bail_reason=review-change-detection-failed; document in step-6-entry.md; fix test_implement_dispatch.py seed expectation.
  - From codex-specialist-correctness: Reuse an existing allowed bail reason such as orchestrator-envelope-invalid, or add the new token to python/larch/core/config.py and its lint coverage.
  - From dyn-dyn-step6-routing: Seed `stall_step="6"` for change-detection failures, register `review-change-detection-failed` in the stall-recovery bail allowlist, and update `python/test_implement_dispatch.py:2139` plus `step-6-entry.md` to match.


### FINDING_3: Architectural-guidelines harness still pins removed Step 6 skip prose
- **Reviewer(s)**: dyn-dyn-step6-routing
- **Severity**: important
- **Concern**: The Step 6 fold removed the harness-pinned `SKILL.md` sentence (`IMMEDIATELY skip to Step 7a for checks/diagrams; architectural-guidelines Phase A staging runs after Step 7a, not on the Step 6 skip branch.`) and replaced it with shorter skip prose, but `skills/implement/scripts/test-architectural-guidelines-step.sh` still `contains`-requires the old literal. That harness runs under `make test-harnesses-1` / `test-architectural-guidelines-step`, so this branch should fail CI even though equivalent contract text survives elsewhere in `SKILL.md`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-step6-routing: Update the harness pin to the new Step 6 skip wording, or restore an equivalent always-loaded sentence in SKILL.md and keep the harness assertion aligned.


### FINDING_4: Structure harness does not forbid bare Step 6 repair `checks-commit-route` re-entry
- **Reviewer(s)**: dyn-dyn-harness-pins
- **Severity**: important
- **Concern**: The plan called for forbidding bare `checks-commit-route` on Step 6 repair re-entry, but `scripts/test-implement-structure.sh` only `require`s the new `step-6-entry.sh` launchers in `checks-repair-loop.md` and `forbid`s the old launcher in `SKILL.md`. Nothing mechanically blocks reintroducing `python/cli.py implement checks-commit-route --checks-site step6 ...` in `skills/implement/references/checks-repair-loop.md` section 4, which would bypass `--force-checks true` and allow post-repair `FILES_CHANGED=false` to emit `skip-to-7a` without re-running Step 6 checks.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-harness-pins: Add a `forbid(checks_ref, 'python/cli.py implement checks-commit-route --checks-site step6', ...)` (and optionally `forbid(checks_ref, 'checks-commit-route --checks-site step6 --commit-site step7', ...)`) beside the existing Step 6 `require` pins in `test-implement-structure.sh`, mirroring the SKILL-level forbid at line 470.


