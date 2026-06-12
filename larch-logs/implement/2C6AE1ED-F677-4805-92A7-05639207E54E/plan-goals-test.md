## Goal
Implement issue #4134: [IMPLEMENTING] [BUG] (URGENT) Restore Codex-first Step 2 coder default (PR #4115 collateral).

## Implementation Plan
[BUG] (URGENT) Restore Codex-first Step 2 coder default (PR #4115 collateral)

## Bug

PR #4115 (issue #4109, commit eda22de63, merged 2026-06-12) flipped the /implement **Step 2 implementer** implicit default from Codex-first to Cursor-first as **unrequested collateral**. Issue #4109 asked to change only the review-fix applier and the findings aggregator/deduplicator. The commit message never mentions the implementer change, and #3704 (2026-06-07) had explicitly pinned: "The initial implementation coder default (Codex) is unchanged — only the review-fix path changes."

**Effect**: every /implement run without an explicit `--coder` now hands the main coding task to Cursor whenever Cursor is available, instead of Codex.

## Fix (full revert surface, three files)

1. `python/bootstrap.py`, `_phase_coder`: swap the two implicit `elif` branches back so `codex_available` is checked before `cursor_available` (restores codex -> cursor -> claude). This is a 4-line revert of the eda22de63 hunk.
2. `python/test_bootstrap.py`, `test_phase_coder_selection_matrix`: restore the implicit-both-available row to `("", "true", "true", "codex", "", False)`.
3. `skills/implement/SKILL.md`, Degraded-tools gate paragraph (Step 0): restore "(codex→cursor→claude per `--coder`)". This re-aligns it with the `phase_coder_select` authority paragraph in the same file, which still reads "Codex, then Cursor, then Claude"; the file currently contradicts itself.

## Do NOT touch (intentional #4109 / #3704 behavior)

- `skills/review-and-fix/scripts/review-and-fix.sh` coder dispatch order (Cursor -> Codex -> Claude main-agent): intentional per #3703/#4109.
- `skills/review/scripts/aggregate-findings.sh` aggregator slot `tool:"cursor"`: intentional per #4109.
- Codex reviewer round policy (specialists round 1 only, generic reviewer rounds 2+): intentional per #4109.
- Scout waterfall Cursor -> Claude: intentional per #3704.

## Validation

- `make py-test` (`test_phase_coder_selection_matrix` passes with the restored row)
- `bash scripts/relevant-checks.sh`

## Context

Third occurrence of this default-order leak: #2400/#2452 flipped cursor-first, #2756/PR #2785 restored Codex-first, now #4115 flipped it again. A per-role default-registry overhaul is being discussed separately; this issue is only the minimal hot fix.

## Test plan
(no test plan section in plan-file)
