## Plan

## Approach

Implement the minimum hardening from the approved outline.

- Keep the existing trailing metadata scan as the primary source of truth. Extract it into its own strict helper so it stays available, unwidened, for callers that must not be more lenient.
- Add a private whole-document fallback in `difficulty.py`, reached only when the trailing position has no difficulty line at all.
- Before using that fallback, check a permissive trailer-adjacent region (the recognized span when one exists, or the tail of the document when it does not, tolerating blank lines and a legacy `confidence:` line) for a present-but-invalid `difficulty:` line. If one is found there, return empty and do not fall back — a broken trailing difficulty line must never be silently rescued by a valid line found elsewhere in the document. This applies whether or not `_trailing_metadata_span` returns a span at all.
- Do not change `rewrite_plan_difficulty()` placement. It should still write into the true trailing metadata span.
- Do not add a Step 2b hard-fail for a missing sidecar.
- The `LARCH_REQUIRE_PLAN_DIFFICULTY=1` hard-required check in `_plan_quality_commands.py` must keep strict trailing-only semantics — it must not inherit the new whole-document fallback, or "required" would silently start accepting a difficulty line found anywhere in the document instead of in the true final trailer.

## Files to modify/create

### UPDATED: python/larch/calibration/difficulty.py

- Extract today's `plan_difficulty()` body into a new strict helper, `trailing_plan_difficulty(text: str) -> str`, unchanged from current behavior: scan `trailing_plan_metadata_lines(text)` in reverse for a line matching `_PLAN_DIFFICULTY_RE`, return the match or `""`.
- Add a private whole-document fallback helper, for example `_last_plan_difficulty_line(text: str) -> str`, that scans `text.splitlines()` in reverse and returns the first line matching `_PLAN_DIFFICULTY_RE.fullmatch(line.strip())`, or `""` if none.
- Add a helper that checks the permissive trailer-adjacent region for a present-but-invalid `difficulty:` line, for example `_adjacent_invalid_difficulty(text: str) -> bool`:
  - Compute `lines = text.splitlines()` and `span = _trailing_metadata_span(lines)`.
  - Set the walk-start index to `span[0]` when `span is not None`, otherwise `len(lines)`.
  - Walk backward from that index, skipping blank lines and lines matching `_PLAN_TRAILER_LINE_RE` or a legacy `^confidence: .+$` line, until hitting a line that either starts with the literal prefix `difficulty:`, or is none of the above.
  - When the walk hits a `difficulty:`-prefixed line, check it against `_PLAN_DIFFICULTY_RE.fullmatch`: return `True` only when it does NOT match (present but invalid). Return `False` when it DOES match — a valid stranded difficulty line must not be treated as invalid; let the whole-document fallback in step 3 below find it instead.
  - When the walk hits any other line (not blank, not trailer-shaped, not a legacy confidence line, not a difficulty line), stop and return `False` — no adjacent difficulty line was found at all.
  - Bound the walk so it cannot run past index 0.
- Rewrite `plan_difficulty()`:
  1. Return `trailing_plan_difficulty(text)` if non-empty (unchanged primary behavior).
  2. Otherwise, if `_adjacent_invalid_difficulty(text)` is `True`, return `""` (fail closed; do not mask a broken trailing difficulty line).
  3. Otherwise, return `_last_plan_difficulty_line(text)` (the whole-document fallback).

### UPDATED: python/larch/design/_plan_quality_commands.py

- In `validate_plan_main`'s `LARCH_REQUIRE_PLAN_DIFFICULTY` branch (around lines 876-877), replace the `not difficulty.plan_difficulty(plan_text)` check with `not difficulty.trailing_plan_difficulty(plan_text)`, so the hard-required gate keeps strict trailing-only semantics and does not inherit the new whole-document fallback.

### UPDATED: python/tests/calibration/test_difficulty.py

Add focused unit coverage:

- `plan_difficulty()` still prefers a valid difficulty in the trailing block (unchanged case).
- `plan_difficulty()` falls back to a mid-document difficulty when the true trailing block has no difficulty line at all (only `diff_lines:`).
- With multiple valid non-trailing difficulty lines and no trailing one, it chooses the last one in document order.
- When the trailing block contains an invalid `difficulty:` line (e.g. `difficulty: EASY`) immediately before `diff_lines:`, `plan_difficulty()` returns `""` even when a valid difficulty line exists earlier in the document.
- Same invalid-trailing case but with a legacy `confidence: high` line between the invalid `difficulty: EASY` and `diff_lines:` — `plan_difficulty()` still returns `""`, not the earlier valid embedded tier.
- When there is no recognized trailing span at all (`_trailing_metadata_span` returns `None`, e.g. the document ends with a legacy `confidence:` line and no `diff_lines:` at all) and the last non-blank line is an invalid `difficulty:` line, `plan_difficulty()` returns `""`.
- Same no-recognized-span shape, but the stranded difficulty line is valid (e.g. document ends `difficulty: MODERATE` / `confidence: high` with no `diff_lines:` at all) — `plan_difficulty()` must still return `"MODERATE"` via the whole-document fallback, not `""`. This is the case a naive "any adjacent difficulty line means invalid" implementation gets wrong.
- `trailing_plan_difficulty()` exposes exactly today's original `plan_difficulty()` behavior (trailing-only, no fallback, no adjacent-invalid check).
- `trailing_plan_metadata_lines()` remains unchanged. It should still expose only the contiguous final trailer block.

### UPDATED: python/tests/design/test_plan_quality.py

Add a regression proving `validate_plan_main`'s `LARCH_REQUIRE_PLAN_DIFFICULTY=1` branch stays strict: a plan whose true trailing block has only `diff_lines:` (no `difficulty:`) but has a valid `difficulty: MODERATE` line earlier in the document must still raise `kind=difficulty-metadata` under `LARCH_REQUIRE_PLAN_DIFFICULTY=1`, proving the required-check calls the strict `trailing_plan_difficulty()` helper rather than the widened `plan_difficulty()`.

### UPDATED: python/tests/design/test_design_publish.py

Add a Step 5c regression for the reported shape:

- Build a design tmpdir with `.completed/step-5b`, `.completed/step-5b.5`, and `.completed/step-3` sentinels (all three; `publish_core` stops before the difficulty logic without `.completed/step-3`).
- Write `.step3-review-result.env` with `STEP3_REVIEW_LOOP_STATUS=complete` and `ROUNDS_COMPLETED=2`.
- Leave `design-difficulty-rating.raw.json` absent — do not write or synthesize it. This is required to actually exercise `_resolve_publish_difficulty_rating()`'s missing-sidecar fallback branch; if the sidecar is present, the new whole-document scan is never reached.
- Write a `plan.txt` fixture with `difficulty: MODERATE` before its own `diff_lines:` trailer, then call the real `_auto_compose_plan_md(design_tmpdir)` from `design_step5c.py` to generate `composed-plan.md`, instead of hand-writing the composed file directly — this proves the fixture matches what the live auto-compose path actually produces, rather than a hand-approximated shape that might drift from reality.
- Keep `.step3-review-result.env` non-empty so `_splice_plan_provenance` actually runs against the real auto-composed text before resolve/rewrite, matching the production Step 5c call order.
- Tighten the local fake `plan validate` helper in this test to require a valid trailing difficulty via `difficulty.trailing_plan_difficulty()` semantics on the final composed text specifically, not a `difficulty:` substring check anywhere in the document and not the widened `plan_difficulty()` — otherwise the test would not prove the publish path actually requires a true trailing tier.
- Run `design publish` through the existing fake CLI harness.
- Assert publish succeeds.
- Assert the final trailing block now includes `review_status: complete`, `rounds_completed: 2`, `difficulty: MODERATE`, then `diff_lines:`, in that order.
- Assert the fake difficulty label and record calls use `MODERATE`.

## Edge cases

- A valid trailing difficulty must win over any older embedded difficulty line.
- A composed plan with no valid difficulty anywhere should still fail under `LARCH_REQUIRE_PLAN_DIFFICULTY=1`.
- Invalid strings such as `difficulty: EASY` should not be accepted by the fallback.
- A trailing block with an invalid `difficulty:` line must fail fast (return `""`), not be rescued by a valid difficulty line found elsewhere in the document — including when a blank line or a legacy `confidence:` line separates the invalid trailing line from `diff_lines:`, and including when no trailing span is recognized at all.
- Conversely, a VALID difficulty line stranded adjacent to the trailing position (e.g. no recognized span at all, document ends `difficulty: MODERATE` / `confidence: high`) must still be found via the fallback, not suppressed as if it were invalid — the adjacent check only fails closed for a genuinely invalid line, never a valid one.
- The fallback may see examples in prose or fenced blocks. This is acceptable for this defense-in-depth path because it runs only when the canonical trailing block lacks any difficulty line, and the line must exactly match the plan trailer grammar.

## Failure modes

- If the fallback replaces the primary scan instead of following it, stale embedded metadata could override the canonical trailing trailer.
- If `_plan_quality_commands.py`'s required-difficulty check keeps calling the widened `plan_difficulty()` instead of the new strict `trailing_plan_difficulty()`, `LARCH_REQUIRE_PLAN_DIFFICULTY=1` silently stops requiring a true trailing tier.
- If the publish regression writes or synthesizes the raw-rating sidecar, or only checks for any `difficulty:` substring, it can miss the original defect entirely. The regression must leave the sidecar absent and check final trailer order specifically.
- If `trailing_plan_metadata_lines()` changes, optional trailer validation may drift. Keep it unchanged.

## Testing strategy

Run targeted tests:

```bash
python3 -m pytest python/tests/calibration/test_difficulty.py python/tests/design/test_design_publish.py python/tests/design/test_plan_quality.py
```

Then run the repo's relevant-checks path for changed files:

```bash
python3 python/cli.py checks run-relevant
```

## Acceptance

Run targeted tests:

```bash
python3 -m pytest python/tests/calibration/test_difficulty.py python/tests/design/test_design_publish.py python/tests/design/test_plan_quality.py
```

Then run the repo's relevant-checks path for changed files:

```bash
python3 python/cli.py checks run-relevant
```

review_status: complete
rounds_completed: 3
difficulty: MODERATE
diff_lines: 90
