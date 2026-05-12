## Goal

Align Codex plan-reviewer prompts with Cursor in `render-plan-review-prompt.sh` by switching `short_role` to `full_role` and adding the TSV structured-record block; update `plan-review.md` collection calls to enable `--structured-reviewer-validation` for Codex; extend test coverage.

## Implementation Plan

### Files to modify

1. `skills/design/scripts/render-plan-review-prompt.sh` — remove the vendor-specific Codex branch; unify on a single `full_role`-based prompt with TSV block for both vendors.
2. `skills/design/references/plan-review.md` — merge the two `collect-agent-results.sh` invocations into one with `--structured-reviewer-validation` for all archetype slots.
3. `skills/design/scripts/render-plan-review-prompt.md` — update Invariants to reflect unified output format.
4. `skills/design/scripts/test-plan-review-prompt.sh` — replace Codex-specific terse/no-TSV assertions with assertions for `full_role` prose and TSV header.
5. `skills/design/scripts/test-plan-review-prompt.md` — update to reflect expanded Codex test coverage.
6. `CHANGELOG.md` — add entry.

### Approach

The Cursor branch in `render-plan-review-prompt.sh` is the template. Remove the vendor-specific `if/else` and use a single `cat <<EOF` block with `${full_role}` and the TSV contract for both vendors.

### Testing strategy

Run `bash skills/design/scripts/test-plan-review-prompt.sh`. New assertions verify Codex produces full_role prose and TSV-structured output. Run `/relevant-checks` for full CI.

## Test plan

Run `bash skills/design/scripts/test-plan-review-prompt.sh` to verify all archetypes x vendors. Run `/relevant-checks` for full CI.
