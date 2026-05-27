## Plan


## Dependency note

`scripts/lint-readability-preamble.sh` was introduced in commit `f915719e` on branch `sergey-zhupanov/implementing-brainstorm-how-to-add-a-ste-2828` (PR #3051, still OPEN as of design time). The script does not yet exist on `main`. `/implement` for #3050 must therefore be sequenced **after** PR #3051 merges. If `/implement` starts and the script is absent, Preflight should refuse with a clear "target file missing — rebase on main once #3051 merges" message rather than re-creating the script.

## Files to modify/create

### UPDATED: `scripts/lint-readability-preamble.sh`

Add a per-file expected directive **count** to every `orchestrator-inline` row in `manifest_rows`, mirroring the existing `external-prompt:<count>:<kind>` pattern. Use `grep -Ec` against `orchestrator_style_re` and compare to the expected count.

Concrete edits:

1. Replace the seven `orchestrator-inline` rows in `manifest_rows`:
   - `skills/design/SKILL.md:orchestrator-inline` → `skills/design/SKILL.md:orchestrator-inline:4`
   - `skills/design/references/design-outline.md:orchestrator-inline` → `:orchestrator-inline:1`
   - `skills/design/references/brainstorm.md:orchestrator-inline` → `:orchestrator-inline:1`
   - `skills/design/references/sketch-launch.md:orchestrator-inline` → `:orchestrator-inline:1`
   - `skills/design/references/dialectic-execution.md:orchestrator-inline` → `:orchestrator-inline:1`
   - `skills/design/references/approval-gates.md:orchestrator-inline` → `:orchestrator-inline:1`
   - `skills/design/references/discussion-rounds.md:orchestrator-inline` → `:orchestrator-inline:1`

2. Initialize `count=0` at the start of each `manifest_rows` loop iteration (before the existing `if [ -f "$file" ]` check) so the orchestrator-inline error path never reads a stale value from a previous iteration or aborts under `set -u`. This mirrors the existing external-prompt arm's `count=0` initialization.

3. In the `orchestrator-inline` `case` arm, replace:
   ```sh
   if grep -Eq "$orchestrator_style_re" "$file"; then
       ok=true
   fi
   ```
   with:
   ```sh
   count=$(grep -Ec "$orchestrator_style_re" "$file" || true)
   if [ "$count" = "${expected_count:-1}" ]; then
       ok=true
   fi
   ```
   `expected_count` is already populated by the existing `IFS=':' read -r path variant expected_count prompt_kind` line (the third colon-separated field). The `${expected_count:-1}` default keeps behavior safe if a row is malformed.

4. Emit a more specific error when the orchestrator-inline branch fails **and the file exists** (count mismatch). The specific message belongs only inside the file-existence branch so that a missing target file continues to surface via the generic `<path>: missing orchestrator-inline readability-style directive` line. Concretely, inside the `orchestrator-inline)` arm and after the count comparison, when `ok != true` print `<path>: expected ${expected_count:-1} orchestrator-inline readability-style directives, found ${count:-0}` and set a local flag (e.g. `count_message_emitted=true`) so the outer `if [ "$ok" != true ]; then printf 'missing ...'` block does not also fire on this row. Leave the `external-prompt` error wording unchanged. Keep `missing=1` and the final `exit "$missing"` semantics intact. The `${count:-0}` and `${expected_count:-1}` defaults are belt-and-suspenders — `count=0` initialization at the top of the loop is the primary guarantee.

### UPDATED: `scripts/test-lint-readability-preamble.sh`

Update the offline harness to enforce the new per-file counts and add a regression case for the multi-directive SKILL.md case.

Concrete edits:

1. In `populate_fixture`, when writing `orchestrator_paths`, emit **4** copies of `$orchestrator_style_line` to `skills/design/SKILL.md` and **1** copy to each other orchestrator file. Use the existing `repeat_line` helper (already used for the external-prompt block) so no new helper is needed.

2. Extend the existing `populate_fixture` signature with an optional fourth argument `partial_orchestrator` (file path). When non-empty, that file is written with `repeat_line "$orchestrator_style_line" $partial_count` where `partial_count` is supplied as a fifth argument. The signature becomes `populate_fixture <root> [missing_external] [missing_orchestrator] [partial_orchestrator] [partial_count]`. Existing two-argument and three-argument callers continue to work because bash positional defaults remain empty.

3. Add two new fixtures and assertions:
   - `orchestrator_partial="$TMPROOT/orchestrator-partial"`
   - `populate_fixture "$orchestrator_partial" "" "" "skills/design/SKILL.md" 3` — populates SKILL.md with **3** instead of 4 directives (one per-step site removed).
   - `assert_lint_fails_for orchestrator-partial "$orchestrator_partial" "skills/design/SKILL.md: expected 4 orchestrator-inline readability-style directives, found 3"`
   - `orchestrator_missing_file="$TMPROOT/orchestrator-missing-file"`
   - `populate_fixture "$orchestrator_missing_file"` then `rm -f "$orchestrator_missing_file/skills/design/SKILL.md"` — exercises the truly-absent-file path (no inline composition, no file at all).
   - `assert_lint_fails_for orchestrator-missing-file "$orchestrator_missing_file" "skills/design/SKILL.md: missing orchestrator-inline readability-style directive"` — confirms that the missing-file path still emits the generic message and never the new count-mismatch wording (anchors FINDING_1's "skipped case arm" risk).

4. Update the existing `assert_lint_fails_for orchestrator-bad` substring. Today's `populate_fixture "$orchestrator_bad" "" "skills/design/SKILL.md"` writes SKILL.md with literal text `"Inline composition without the directive."` (file exists, 0 directives), so under the new lint behavior the lint must fail with the **count-mismatch** message, not the generic missing message: `"skills/design/SKILL.md: expected 4 orchestrator-inline readability-style directives, found 0"`.

5. Keep the `compliant` and `external-bad` cases unchanged in intent; the `compliant` fixture now exercises the new 4-directive SKILL.md count via the updated `populate_fixture`. Item 4 above already replaces the existing `orchestrator-bad` substring to match the new wording.

6. Reasonably expect the LOC budget to land slightly above the original ~40 LOC estimate because of the extra test fixture and the count-initialization edit; aim for ~55-60 LOC total across both files. This stays well under the 800-line plan-body / 1500-line diff hard thresholds.

## Approach

Mirror the existing `external-prompt:<count>:<kind>` manifest pattern: extend `orchestrator-inline` rows with the third colon-separated `expected_count` field, switch from `grep -Eq` to `grep -Ec`, and compare. The change is **purely additive**: the manifest gains one new piece of metadata per row, and the count-comparison logic replaces a boolean existence check. No section parsing, no markdown header parsing, no line-range anchors. Existing `IFS=':' read -r path variant expected_count prompt_kind` already captures the third field, so no new bash machinery is required.

The error message tweak ("expected N, found M") makes the regression actionable: if a future edit removes one of SKILL.md's four per-step directives, the lint and harness will both surface "found 3" so the offending edit is easy to locate.

## Edge cases

- **Missing target file** (the manifest-row file does not exist on disk): the outer `if [ -f "$file" ]` branch is skipped entirely, `ok` remains `false`, and the existing generic `<path>: missing <variant> readability-style directive` line fires. The new specific count-mismatch message must NOT fire for this case — it is scoped to inside the file-existence branch.
- **Empty file**: `grep -Ec` returns `0` on a non-matching file, so an empty orchestrator file with `expected_count=1` reports `found 0` (specific message) and fails.
- **`grep -Ec` exit code**: GNU/BSD `grep -c` exit code is 1 when no lines match (still prints `0`). The `|| true` guard mirrors the existing external-prompt arm.
- **Stale loop variable**: addressed by per-iteration `count=0` reset. Without that reset, a row that skips the `[ -f "$file" ]` branch (missing file) followed by a row that takes the orchestrator-inline branch could under `set -u` see a stale `count` from an earlier external-prompt iteration. The reset removes that risk irrespective of the `${count:-0}` default in the error message.
- **Malformed manifest row** (missing count): `${expected_count:-1}` defaults to `1`, so a row left as `path:orchestrator-inline` degrades to today's "at least one" semantics rather than crash. Acceptable safety net; not relied on by any row after this change.
- **Count larger than actual**: e.g., manifest says `:5` but file has `4` directives. Reports `expected 5, found 4` and fails. Maintainer fixes the manifest or the file — both are valid resolutions.
- **Bash 3.2 portability**: `grep -Ec` and `${var:-default}` are POSIX-safe; `IFS=':' read` already in use; no new Bash 4+ constructs introduced (confirmed against `BASH_AUTHORING.md` §3).

## Failure modes

Omitted — this is a lint+harness micro-change with no architectural surfaces.

## Testing strategy

- `bash scripts/test-lint-readability-preamble.sh` — must pass with the updated fixture/assertion set, including the new `orchestrator-partial` regression case.
- `bash scripts/lint-readability-preamble.sh` — must pass against the real repository (SKILL.md continues to carry 4 directives at lines 793, 1081, 1129, 1234 on the implementing branch).
- `make test-lint-readability-preamble` — already wired in `Makefile` on the implementing branch; no Makefile change required.
- Pre-commit registration (`.pre-commit-config.yaml`) already invokes `lint-readability-preamble`; no config change required.


## Acceptance

- `bash scripts/test-lint-readability-preamble.sh` passes including new `orchestrator-partial` and `orchestrator-missing-file` regression cases.
- `bash scripts/lint-readability-preamble.sh` passes against the implementing branch (SKILL.md continues to carry 4 directives at the four per-step composition sites; six references each carry 1).
- The orchestrator-inline branch reports `expected N, found M` only when the file exists but the directive count is wrong, and continues to emit the generic `missing orchestrator-inline readability-style directive` line when the manifest-row file does not exist on disk.
- Removing one of the 4 SKILL.md per-step directives produces a regression-greppable error of the shape `skills/design/SKILL.md: expected 4 orchestrator-inline readability-style directives, found 3`.
- `make test-lint-readability-preamble` passes; pre-commit `lint-readability-preamble` hook passes.
- No new Bash 4+ constructs introduced; `bash scripts/lint-bash32.sh` continues to pass.

diff_lines: 55
