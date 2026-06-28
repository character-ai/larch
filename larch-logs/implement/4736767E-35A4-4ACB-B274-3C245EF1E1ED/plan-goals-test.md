## Goal
Implement issue #5688: [IMPLEMENTING] md-to-py-VIII: dedup /implement Step 5 checks-failed blocks and collapse the exit-3 sub-cases to a preflight pointer.

## Implementation Plan
## Plan

Make the minimum prose and harness changes.

- Keep runtime behavior unchanged.
- Keep every `--site` and `--checks-site` token stable.
- Do not move logic into Python for this issue. This is always-loaded `SKILL.md` context cleanup.
- Treat `skills/implement/references/preflight-plan-audit.md` as the authoritative owner of clarify refusal sub-cases.
- Treat `## Checks Failure Entry Macro` as the authoritative owner of checks-failure read and mandatory-reference steps.

## Files to modify/create

### UPDATED: skills/implement/SKILL.md

1. In `## Checks Failure Entry Macro`, add one short sentence that call sites should invoke the macro by name with their pinned site arguments, rather than restating the read and mandatory-reference steps.

2. Collapse the five checks-failed call sites to macro invocations:
   - Step 3: replace the inline `REDACTED_LOG_FILE` read plus mandatory `checks-repair-loop.md` read with `apply **Checks Failure Entry Macro** with pinned --site step3`.
   - Step 5 `main-agent-vote-required`: remove the duplicated blockquote body.
   - Step 5 `coder-main-agent-required`: remove the duplicated blockquote body.
   - Step 6: replace the inline `REDACTED_LOG_FILE` read plus mandatory `checks-repair-loop.md` read with `apply **Checks Failure Entry Macro** with pinned --site step6`.
   - Keep the shared Step 5 `--site step5-mav --checks-site step5-review-fixes` token exactly.

3. For Step 5, keep both branch bullets, but have both fall through to one shared `> **Continue after child returns.**` blockquote placed immediately before the existing `checks-step5-resume` fence.
   - The shared blockquote must cover both `main-agent-vote-required` and `coder-main-agent-required`.
   - It must keep:
     - `NEXT_ACTION=checks-failed`
     - `Checks Failure Entry Macro`
     - `--site step5-mav --checks-site step5-review-fixes`
     - `On checks pass, apply the composite stdout parsing slice and full resume envelope contract below.` (load-bearing success-path continuation before `checks-step5-resume`)
     - `NEXT_ACTION=main-agent-edit`
     - terminal `NEXT_ACTION=stall` routing to the main-agent handoff terminal-stall path
     - `Do **not** re-invoke the Step 5 loop wrapper.`

4. In the `/implement` exit-code table, replace the long exit-code `3` sub-case A/B/C prose with a one-line pointer:
   - `AUDIT=refuse` exits `3`.
   - Follow `${CLAUDE_PLUGIN_ROOT}/skills/implement/references/preflight-plan-audit.md` `## Clarify-request flow after AUDIT=refuse` for post, label, `STATE=ambiguous`, and `STATE=awaiting-response` behavior.
   - Keep the force note that `--force` cannot reach this path.

### UPDATED: skills/implement/references/self-review.md

Replace the checks-failed inline read plus mandatory `checks-repair-loop.md` read with a direct macro invocation using pinned `--site step5-self-review`.

Keep the surrounding continuation, stall, and success routing unchanged.

### UPDATED: scripts/test-implement-structure.sh

Update structural assertions for the prose shape.

Add or adjust checks so the harness:
- Requires the shared Step 5 MAV/coder checks block.
- Requires exactly one `skills/implement/SKILL.md` occurrence of the pinned Step 5 macro token `--site step5-mav --checks-site step5-review-fixes`.
- Requires the shared Step 5 blockquote to pin the checks-pass success continuation: `On checks pass, apply the composite stdout parsing slice and full resume envelope contract below.` (or equivalent wording) immediately before `checks-step5-resume`.
- Forbids the old duplicated inline phrase that combines `REDACTED_LOG_FILE`, the mandatory `checks-repair-loop.md` read, and `then apply **Checks Failure Entry Macro**`.
- Requires the exit-code `3` table to point at `preflight-plan-audit.md` and `Clarify-request flow after AUDIT=refuse`.
- Forbids `Sub-case A`, `Sub-case B`, and `Sub-case C` in `skills/implement/SKILL.md`.
- In the `self_review_text` needle list (currently lines 847–874), replace the three inline-authority needles (`REDACTED_LOG_FILE`, `NOT raw \`LOG_FILE\``, `checks-repair-loop.md`) with macro-based pins:
  - Require `Checks Failure Entry Macro` in `self-review.md`.
  - Require pinned `--site step5-self-review` in `self-review.md`.
  - Forbid the old inline combo of `REDACTED_LOG_FILE` plus mandatory `checks-repair-loop.md` read in `self-review.md`.
  - Keep the existing `> **Continue after child returns.**` opener requirement and composite-launcher timing assertions.

### UPDATED: scripts/test-plan-adequacy-audit.sh

Update the Preflight audit harness to match the new exit-code table.

- Migrate the `STATE=awaiting-response` reachability assertion from `contains "$SKILL"` (line 92) to `contains "$PREFLIGHT_AUDIT_REF"` (or equivalent path to `skills/implement/references/preflight-plan-audit.md`), so state detail ownership stays in the reference after the SKILL collapse.
- Move detailed state ownership expectations to `skills/implement/references/preflight-plan-audit.md`.
- Add a `SKILL.md` assertion for the one-line exit-code `3` pointer.
- Add `SKILL.md` forbids for the collapsed sub-case labels.

### UPDATED: skills/implement/scripts/test-implement-relevant-checks-anti-halt.sh

Update the anti-halt regression harness for macro-based call sites.

- Keep the existing canonical opener check near the three active launcher invocation sites.
- Keep success-continuation guidance checks, including `checks pass`, `NEXT_ACTION=continue`, or `RELEVANT_CHECKS_SKIPPED=true` within five lines before `checks-step5-resume`.
- Add or tighten a pin for the Step 5 shared blockquote success-path line `On checks pass, apply the composite stdout parsing slice and full resume envelope contract below.` near `checks-step5-resume`.
- Replace the per-site inline `REDACTED_LOG_FILE` / `NOT raw LOG_FILE` requirement with a per-site requirement for a nearby `Checks Failure Entry Macro` invocation.
- Add a macro-definition assertion that `## Checks Failure Entry Macro` still contains:
  - `REDACTED_LOG_FILE`
  - `NOT raw LOG_FILE`
  - `checks-repair-loop.md`
  - pinned site guidance
- Keep `EXPECTED_SITES=3` unless the edit accidentally changes launcher count.

### UPDATED: skills/implement/scripts/test-implement-relevant-checks-anti-halt.md

Update the contract text to say the harness now verifies macro-based checks-failed routing, rather than requiring every call site to restate the redacted-log guidance inline.

## Edge cases

- Step 5 MAV and coder branches must still be distinguishable before the shared checks handoff.
- `--site step5-mav --checks-site step5-review-fixes` must not be weakened to only `--site step5-mav`.
- Step 5 terminal `NEXT_ACTION=stall` must still use the special handoff path, not default Step 18 routing.
- Exit code `3` must still mention `--force` reachability, because force skips the audit before `AUDIT=refuse` exists.
- The shared Step 5 blockquote must retain the checks-pass success continuation; dropping it breaks the post-checks resume path and the anti-halt `has_success` check.

## Failure modes

- If the shared Step 5 blockquote moves too far from the `checks-step5-resume` fence, `test-implement-relevant-checks-anti-halt.sh` may fail its nearby-opener check.
- If the shared Step 5 blockquote omits the checks-pass success line, `test-implement-relevant-checks-anti-halt.sh` `has_success` and `test-implement-structure.sh` shared-blockquote pins should fail.
- If the macro invocation drops `REDACTED_LOG_FILE` semantics entirely, the updated anti-halt harness should fail on the macro-definition assertion.
- If `test-implement-structure.sh` still requires inline `REDACTED_LOG_FILE` / `checks-repair-loop.md` in `self-review.md` after the macro collapse, `make test-implement-structure` fails on the correct output.
- If `test-plan-adequacy-audit.sh` still asserts `STATE=awaiting-response` only in `SKILL.md`, the harness fails after the exit-code table collapse.
- If the exit-code table keeps stale sub-case prose, `test-plan-adequacy-audit.sh` should fail.

## Testing strategy

Run focused prose and harness checks:

```bash
bash scripts/test-implement-structure.sh
bash scripts/test-plan-adequacy-audit.sh
bash skills/implement/scripts/test-implement-relevant-checks-anti-halt.sh
bash scripts/test-implement-fence-shape.sh
```

Also run the Make targets that wrap the same harnesses when time permits:

make test-implement-structure
make test-plan-adequacy-audit
make test-implement-relevant-checks-anti-halt
make test-implement-fence-shape

`test-implement-fence-shape` should not require `EXPECTED_OLD` / `EXPECTED_NEW` changes because this plan changes prose only, not Bash fences.

## Acceptance

Run focused prose and harness checks:

```bash
bash scripts/test-implement-structure.sh
bash scripts/test-plan-adequacy-audit.sh
bash skills/implement/scripts/test-implement-relevant-checks-anti-halt.sh
bash scripts/test-implement-fence-shape.sh
```

Also run the Make targets that wrap the same harnesses when time permits:

make test-implement-structure
make test-plan-adequacy-audit
make test-implement-relevant-checks-anti-halt
make test-implement-fence-shape

`test-implement-fence-shape` should not require `EXPECTED_OLD` / `EXPECTED_NEW` changes because this plan changes prose only, not Bash fences.

diff_added: 95
diff_deleted: 95
mechanical_churn: false
diff_lines: 190

## Test plan
(no test plan section in plan-file)
