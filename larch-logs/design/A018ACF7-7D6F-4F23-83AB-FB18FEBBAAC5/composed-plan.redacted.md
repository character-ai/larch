## Plan

# Implementation Plan — Issue #2678 — Pin canonical YES↔EXONERATE phrase across 4 prose locations

## Approach

Backfill the canonical anchor phrase `When in doubt between YES and EXONERATE, prefer EXONERATE` into the 3 prose locations that currently lack it verbatim (the 4th already has it), then add a numbered structural check in `scripts/test-design-structure.sh` that grep-asserts the phrase in all 4 locations. Doc + test additions only; no logic changes.

The four locations are:
1. `skills/design/references/plan-review.md` — Voter 1 prompt string (Claude subagent voter prompt; currently has proportionality wording).
2. `skills/design/references/plan-review.md` — shared Voter 2/3 prompt string (instruction passed to Codex/Cursor/Claude-replacement voters; currently has proportionality wording).
3. `skills/shared/scripts/render-voter-prompt.sh` — the actual renderer that `scripts/dispatch-plan-voters.sh make_prompt_file()` delegates to (the issue body names `dispatch-plan-voters.sh` but `make_prompt_file()` is a thin wrapper that calls this renderer; the canonical prose belongs in the renderer).
4. `skills/design/references/plan-review-quick.md` — acceptance-guidance line (already has phrase; no edit needed).

## Files to modify/create

### UPDATED: `skills/design/references/plan-review.md`

Two single-sentence additions, both inside backtick-quoted prompt strings:

- **Voter 1 prompt** (the line beginning `- **Voter 1**: **Claude Code Reviewer subagent**`): append ` When in doubt between YES and EXONERATE, prefer EXONERATE.` to the prompt string, immediately before the closing backtick.
- **Shared Voter 2/3 prompt** (the line beginning `For Codex, Cursor, and their Claude replacement voters, instruct each:`): append ` When in doubt between YES and EXONERATE, prefer EXONERATE.` to the prompt string, immediately before the closing backtick.

Both insertions are inside existing single-line prompt strings; no new lines, no structural changes.

### UPDATED: `skills/shared/scripts/render-voter-prompt.sh`

Add exactly one `printf` line after line 46 (the existing `Vote EXONERATE rather than YES...` printf), emitting the canonical phrase as its own line in the rendered prompt:

```sh
printf '%s\n' 'When in doubt between YES and EXONERATE, prefer EXONERATE.'
```

Placement: between the existing `Vote EXONERATE rather than YES when the concern is legitimate...` line and the `Do NOT vote NO solely because...` line. This keeps the rendered prompt's existing structure intact.

### UPDATED: `scripts/test-design-structure.sh`

Append a new numbered check `FINDING_2678` near the end of the file (after the existing `Check FINDING_21` block, before the final `echo "PASS: ..."` line). The check asserts the canonical phrase appears in all four source-level locations:

```bash
# Check FINDING_2678 (#2678): YES↔EXONERATE canonical anchor phrase pinned across 4 prose locations.
CANONICAL_PHRASE='When in doubt between YES and EXONERATE, prefer EXONERATE'
PLAN_REVIEW_MD="$REPO_ROOT/skills/design/references/plan-review.md"
PLAN_REVIEW_QUICK_MD="$REPO_ROOT/skills/design/references/plan-review-quick.md"
RENDER_VOTER_SH="$REPO_ROOT/skills/shared/scripts/render-voter-prompt.sh"

# Location 1: Voter 1 prompt string in plan-review.md (single-line block).
voter1_line=$(grep -n '^- \*\*Voter 1\*\*' "$PLAN_REVIEW_MD" | head -1 | cut -d: -f1 || true)
[[ -n "$voter1_line" ]] || fail "(FINDING_2678) plan-review.md missing '- **Voter 1**' prompt anchor"
voter1_text=$(sed -n "${voter1_line}p" "$PLAN_REVIEW_MD")
grep -Fq "$CANONICAL_PHRASE" <<< "$voter1_text" \
  || fail "(FINDING_2678) plan-review.md Voter 1 prompt missing canonical phrase: $CANONICAL_PHRASE"

# Location 2: shared Voter 2/3 prompt string in plan-review.md (single-line block).
shared_line=$(grep -n '^For Codex, Cursor, and their Claude replacement voters' "$PLAN_REVIEW_MD" | head -1 | cut -d: -f1 || true)
[[ -n "$shared_line" ]] || fail "(FINDING_2678) plan-review.md missing 'For Codex, Cursor, and their Claude replacement voters' shared-voter-prompt anchor"
shared_text=$(sed -n "${shared_line}p" "$PLAN_REVIEW_MD")
grep -Fq "$CANONICAL_PHRASE" <<< "$shared_text" \
  || fail "(FINDING_2678) plan-review.md shared Voter 2/3 prompt missing canonical phrase: $CANONICAL_PHRASE"

# Location 3: render-voter-prompt.sh — the renderer called by dispatch-plan-voters.sh make_prompt_file().
grep -Fq "$CANONICAL_PHRASE" "$RENDER_VOTER_SH" \
  || fail "(FINDING_2678) render-voter-prompt.sh missing canonical phrase (renderer behind dispatch-plan-voters.sh make_prompt_file): $CANONICAL_PHRASE"

# Location 4: plan-review-quick.md acceptance-guidance line.
grep -Fq "$CANONICAL_PHRASE" "$PLAN_REVIEW_QUICK_MD" \
  || fail "(FINDING_2678) plan-review-quick.md missing canonical phrase: $CANONICAL_PHRASE"
```

Number choice: `FINDING_2678` follows the existing issue-tagged convention (e.g. `FINDING_21`, `Check 17`). The block is placed near the end so future additions append cleanly.

### UPDATED: `scripts/test-design-structure.md`

Append a one-clause mention of the new check to the contract paragraph in the sibling `.md`. Approximately:

> ...and accepted-OOS security exclusion at public-boundary writes [...]; YES↔EXONERATE canonical-phrase pinning across the Voter 1 prompt, shared Voter 2/3 prompt, `render-voter-prompt.sh` renderer, and quick-mode acceptance-guidance line (#2678).

One-line semantic addition; preserves existing prose.

## Edge cases

- **Line-precision regex**: the Voter 1 and shared Voter 2/3 prompts are emitted as **single-line** markdown bullet items in `plan-review.md`. `grep -n` + `sed -n "${line}p"` extracts that single line for substring matching — robust to surrounding line-number drift but fragile if the bullets are ever broken into multiple lines. If a future edit splits the prompt across lines, the anchor line still contains `**Voter 1**` / `For Codex, Cursor, and their Claude replacement voters`, but the canonical phrase may have moved to a subsequent line — the test would correctly fail and surface the structural change for re-review.
- **Quoting in prompt strings**: the canonical phrase contains no characters that require escaping inside a backtick-delimited markdown code span. The two prompt strings in `plan-review.md` are already backtick-quoted; appending a sentence inside the backticks preserves the existing escape structure.
- **render-voter-prompt.sh stdout contract**: that script's top comment warns "Stdout is the prompt payload; lib-quiet redirects stdout after init and would silently empty the rendered prompt when this helper is invoked from quiet-aware parents." Adding one more `printf '%s\n' ...` line follows the existing pattern — no change to stdout/stderr contract.
- **`make_prompt_file()` in dispatch-plan-voters.sh remains unchanged**: the wrapper still calls `render-voter-prompt.sh` and writes the result to `$DESIGN_TMPDIR/${tool}-plan-voter-prompt.txt`. The canonical phrase appears in the rendered output via the renderer; the structural test grep target is the renderer source file (where the prose lives), not the wrapper.
- **No interaction with existing `test-dispatch-plan-voters.sh` assertions**: existing assertions use `grep -Fq` for substrings (OOS rows, FINDING_N grammar, EXONERATE wording) that do not overlap with the new canonical phrase. Adding one printf line does not affect any of them.

## Testing strategy

Run `bash scripts/test-design-structure.sh` and verify the new `FINDING_2678` check passes with all 4 sub-assertions succeeding. Then deliberately mutate one location (e.g. remove the phrase from `render-voter-prompt.sh`) and re-run to confirm the assertion fires with the expected `FAIL:` message naming the offending location. Restore the file.

Also run `make lint` (or `bash scripts/relevant-checks.sh`) to confirm no markdownlint / shell-lint regressions from the prompt-string edits.

Existing test-dispatch-plan-voters.sh assertions remain unchanged; they continue to pass because no existing fixed-string pattern overlaps with the newly added phrase.

## Acceptance

- `bash scripts/test-design-structure.sh` exits 0 with the new `FINDING_2678` check listed in the run output.
- The canonical phrase `When in doubt between YES and EXONERATE, prefer EXONERATE` appears verbatim in:
  - `skills/design/references/plan-review.md` Voter 1 prompt string (the line starting `- **Voter 1**: **Claude Code Reviewer subagent**`).
  - `skills/design/references/plan-review.md` shared Voter 2/3 prompt string (the line starting `For Codex, Cursor, and their Claude replacement voters,`).
  - `skills/shared/scripts/render-voter-prompt.sh` source (a `printf` line emitted in the rendered voter prompt).
  - `skills/design/references/plan-review-quick.md` acceptance-guidance paragraph (already present; verified unchanged).
- `scripts/test-design-structure.md` sibling contract mentions the new YES↔EXONERATE canonical-phrase pinning check.
- `bash scripts/relevant-checks.sh` (or `make lint`) passes after the edits — no markdownlint or shell-lint regressions.
- Existing `bash scripts/test-dispatch-plan-voters.sh` assertions continue to pass (no existing substring assertion overlaps with the newly added phrase).

diff_lines: 30
