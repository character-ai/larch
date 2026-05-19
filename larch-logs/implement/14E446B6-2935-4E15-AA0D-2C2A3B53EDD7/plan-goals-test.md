## Goal
Fix three schema gaps in compose-review-findings.sh: reviewer attribution, round_num field, OOS findings capture

## Implementation Plan

Fix three schema gaps in scripts/compose-review-findings.sh and update the regression test harness.

### Gap 1 — Fix reviewer field semantics

Root causes:
- Accepted findings: the header regex captures finding ID and title; `pending_reviewer` stays unset → default `"panel"` is wrong
- `code-review-rejected` with `[rejected]` header: `BASH_REMATCH[2]` = finding ID (e.g. `FINDING_18`), not the reviewer

Fix:
1. Add `extract_reviewer_from_body()` helper (portable awk) that scans the body for `^- **Reviewer**: <value>` and returns the value.
2. In `flush_pending()`, when `pending_reviewer` is empty, call `extract_reviewer_from_body "$pending_body"` and use the result; final fallback stays `"panel"`.
3. In the `code-review-rejected` case, only set `pending_reviewer` from the header when the format is `[Code Review]` (reviewer in header). For `[rejected]` format, leave `pending_reviewer` empty so the body extraction provides it.

Chosen semantics: Option A — replace `reviewer="panel"` with the proposing reviewer's slot when available. `"panel"` remains the fallback when no `- **Reviewer**: ` line is found.

### Gap 2 — Add round attribution

1. Add `round_num` as the 6th parameter to `emit_record()`. Add `--arg round_num "$round_num"` and `round_num: $round_num` to the jq call.
2. Add `round_num` as the 3rd parameter to `parse_artifact()` (default `""`). The inner `flush_pending()` accesses `round_num` via bash dynamic scoping.
3. Dispatch loop: compute `round_num="$(basename "$round_dir" | sed 's/^round-//')"` per round and pass to all `parse_artifact` calls.
4. Plan-review artifact calls (DESIGN_DIR): pass `""` as `round_num`.

### Gap 3 — Capture OOS findings

1. Add `code-review-oos` case to the `case` block: `phase="code-review"; outcome="out_of_scope"; id_prefix="OOS_C"`.
2. Add corresponding accumulation in the while loop (same header pattern as `code-review-accepted`, but using `id_prefix` + counter for sequential `OOS_C1`, `OOS_C2`, ... ids).
3. In the dispatch loop (after accepted-findings.md parse), add `parse_artifact "$round_dir/oos.md" code-review-oos "$round_num"`. OOS is per-round only (no root-level fallback needed).

### Test updates (test-compose-review-findings.sh)

1. Update existing `FINDING_2.reviewer` assertion from `"panel"` to `"Codex-Structure"` (body extraction now works).
2. Update required-fields check to include `round_num`.
3. Add multi-round test: 2 rounds with accepted findings, assert `round_num` fields.
4. Add all-OOS test: round-1/oos.md with 3 findings, assert `outcome="out_of_scope"`, ids `OOS_C1..OOS_C3`.
5. Add rejected-reviewer attribution test: body with `- **Reviewer**: cursor-specialist-testing-output.txt`, assert `reviewer` field.
6. Add accepted-reviewer attribution test (Option A semantics).

### Documentation update (compose-review-findings.md)

- Add `round_num` field to the schema table.
- Add `out_of_scope` to the `outcome` enum.
- Document corrected `reviewer` semantics (body extraction, `"panel"` fallback).


## Test plan

Run `make lint` (which runs `scripts/test-compose-review-findings.sh`) after implementation.

Files modified:
- scripts/compose-review-findings.sh
- scripts/compose-review-findings.md
- scripts/test-compose-review-findings.sh
