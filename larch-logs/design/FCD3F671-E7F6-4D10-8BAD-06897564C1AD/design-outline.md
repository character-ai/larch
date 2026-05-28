## Proposed Design Outline

### Goals
- Make `/design` plan-revise auto-apply succeed on the two observed LLM patch defects (Cursor prose preamble; Codex off-by-N hunk header).
- Add a single new 4th tier (file-replacement format) so revise has a decisive fallback when all three unified-diff tiers fail validation.
- Surface fallback success distinctly via `REVISE_STATUS=ok-fallback` without changing the per-round contract for unified-diff success.

### Non-goals
- Do NOT pre-wrap long lines in `plan.txt` (fix D rejected — plan format unchanged).
- Do NOT add new regression test fixtures or scenarios (operator directive).
- Do NOT alter the public `--patch-format` CLI surface or change its default (`unified-diff`).

### Approach sketch
- Strip non-diff prose preamble inside `extract_patch()` before validation (fix B).
- Add `--recount` to `git apply --check` and `git apply` in `check_git_apply()` and `apply_patch_file()` (fix A).
- Append a single `attempt_tier 4` call that swaps `PATCH_FORMAT` to `file-replacement`, re-renders the prompt, and internally waterfalls Codex → Cursor → Claude (fix C).
- On tier-4 success emit `REVISE_STATUS=ok-fallback`; update `plan-review-loop.sh` to treat it as success and `plan-review.md` / `revise-plan-with-waterfall.md` to document it.

### Surfaces in scope
- `skills/design/scripts/revise-plan-with-waterfall.sh` (primary)
- `skills/design/scripts/revise-plan-with-waterfall.md` (sibling doc; status enum + 4th-tier prose)
- `skills/design/scripts/plan-review-loop.sh` (consumer: accept `ok-fallback` as success)
- `skills/design/references/plan-review.md` (Revision failures bullet)

### Open questions
- None.
