## Goal

Reduce token waste in reviewer prompt launches by consolidating duplicated "Walk five focus areas" prose, shrinking the read-only preamble in scripts/launch-review.sh, creating a spec-driven renderer for plan-review prompts with vendor-specific styles, and filing research issues for sub-task E.

## Implementation Plan

## Implementation Plan: Reviewer Prompt Consolidation and Vendor Efficiency

### Overview

Token savings across four sub-tasks (A, B, C/D combined), with E as OOS-only. CI invariants are maintained throughout: the slash-separated focus-area enum `code-quality / risk-integration / correctness / architecture / security` must appear in each SKILL.md file that CI checks (`skills/review/SKILL.md`, `skills/design/SKILL.md`, `skills/implement/SKILL.md`), and the literal string `HARD CONSTRAINTS — your role is read-only review` must survive preamble shrinkage (it is the test-harness anchor).

**Plan-review revisions applied:**
- FINDING_1: Renderer called via temp file (not process substitution) to propagate exit status.
- FINDING_2: New test harness wired to Makefile, CI shard, and docs/linting.md.
- FINDING_3: Golden test asserts NO_ISSUES_FOUND instruction IS present (not absent).
- FINDING_4: Cursor preamble keeps explicit compact prohibition sentence.
- FINDING_6: Fallback paths updated to call renderer with fallback vendor/archetype.
- FINDING_7: Drop `--vendor claude` from renderer interface; Claude fallbacks use existing reviewer-templates path.

---

### Step 1: Create `skills/shared/focus-area-prompt.md` (Sub-task A)

Create the canonical compressed focus-area prose file. This file contains:
- A backticked `code-quality` / `risk-integration` / `correctness` / `architecture` / `security` enum in the preamble (satisfying the `BACKTICKED_FILES` CI check once the file is added there).
- A compressed ~40-word version of "Walk five focus areas" that reviewers can reference.
- A "Do NOT modify files" instruction.
- An update-triggers section.

File path: `skills/shared/focus-area-prompt.md`

Compressed content:
  "Walk five focus areas — tag each finding with its focus area (one of `code-quality` / `risk-integration` / `correctness` / `architecture` / `security`): (1) Code Quality: bugs, logic, reuse, tests, backward compat, style. (2) Risk/Integration: breaking changes, side effects, thread safety, deployment risks, regressions, CI. (3) Correctness: logic errors, off-by-one, nil handling, type mismatches, races, error paths. (4) Architecture: separation of concerns, contract boundaries, invariants, semantic boundaries. (5) Security: injection, authn/authz, secret handling, crypto, deserialization, SSRF, path traversal, dependency CVEs."

### Step 2: Update `ci.yaml` to add new shared file (Sub-task A)

In `.github/workflows/ci.yaml`, add `skills/shared/focus-area-prompt.md` to the `BACKTICKED_FILES` array (not `UNQUOTED_FILES`). The backtick form in the shared file satisfies the formal enum check. The unquoted slash-separated check on SKILL.md files is unchanged.

File path: `.github/workflows/ci.yaml`
Change: append `skills/shared/focus-area-prompt.md` to `BACKTICKED_FILES=(...)`.

### Step 3: Compress focus-area prose in review/implement SKILL.md files (Sub-task A)

For each of the inline prompt strings in `skills/review/SKILL.md` (2 Codex generic slots) and `skills/implement/SKILL.md` (3 quick-mode slots):

**Constraint**: the slash-separated enum `code-quality / risk-integration / correctness / architecture / security` MUST remain on the same line as the prompt string in each SKILL.md, because CI's `UNQUOTED_FILES` check greps for it there. NEVER #6 in `skills/implement/SKILL.md` prohibits moving Step 5 quick-mode blocks without extending CI. The enum stays inline.

**Change**: In each prompt string, replace the verbose 5-area body (from "(1) Code Quality: logical flaws..." through "...dependency CVEs." — ~120 words) with the shorter version (from the shared file — ~40 words). The tag instruction "Tag each finding with its focus area (one of code-quality / risk-integration / correctness / architecture / security)" stays inline in the prompt.

Files changed: `skills/review/SKILL.md`, `skills/implement/SKILL.md`.

Note: The 4 Step-3 plan-review blocks in `skills/design/SKILL.md` are handled wholesale in Step 6.

### Step 4: Shrink HARD CONSTRAINTS preambles (Sub-task B)

In `scripts/launch-review.sh`:

**Codex preamble** (`CODEX_REVIEW_HARDENING_PREAMBLE`, delivered via `CODEX_HOME/config.toml`):
Replace 5-bullet list with (anchor line must be preserved):
  "HARD CONSTRAINTS — your role is read-only review. Do not create, edit, delete, or overwrite files, and do not run mutating shell or git commands. The launcher enforces this with --sandbox read-only (CLI rejects writes)."

**Cursor preamble** (`CURSOR_REVIEW_HARDENING_PREAMBLE`, prepended to the outgoing prompt):
Replace 5-bullet list with a compact but explicit form (per FINDING_4 — Cursor lacks sandbox enforcement so explicit prohibition sentence must remain):
  "HARD CONSTRAINTS — your role is read-only review. Do not create, edit, delete, or overwrite files, and do not run mutating shell or git commands. The launcher passes --mode plan to the cursor CLI. Any post-run mutation will be detected by the dirty-tree sidecar."

**Critical**: The anchor string `HARD CONSTRAINTS — your role is read-only review` remains at the start of each preamble — all test assertions use this exact literal. All preamble-count assertions (exactly-1 in retry replay) still hold. No changes to argument structure, retry mechanics, sidecar handling, or prompt file paths.

Update `scripts/launch-review.md` sibling doc to reflect the shorter preamble.

Update `scripts/test-launch-review.sh`:
- Audit for assertions on specific removed bullet text (e.g., checking for "Do not redirect, tee, append" etc.) — remove or update those if they exist.
- Preserve all assertions that check for the anchor string.
- Preserve all preamble-count assertions.
- Add assertion that new compact explicit prohibition sentence is present in config.toml (Codex) and outgoing prompt (Cursor).

### Step 5: Create `skills/design/scripts/render-plan-review-prompt.sh` (Sub-task C + D)

Create a new renderer script with the following interface:
  `render-plan-review-prompt.sh --archetype <arch|edge|innovation|pragmatic> --vendor <codex|cursor> --plan-file <path>`

Note: `--vendor claude` is NOT implemented in this PR (FINDING_7 accepted). Claude fallbacks continue using the existing reviewer-templates path in `plan-review.md`.

The script outputs a complete plan-review prompt to stdout, with:
- Archetype-specific role description (arch = architecture/standards, edge = edge-cases/failure-modes, innovation = innovation/exploration, pragmatic = pragmatism/safety).
- Vendor-specific style:
  - `codex`: terse/imperative. Short role statement + "Walk five focus areas: code-quality / risk-integration / correctness / architecture / security — tag each." + numbered findings format + OOS/NO_ISSUES_FOUND instructions.
  - `cursor`: path/file-list-centric. Full role statement + "Explore the codebase following file paths in the plan." + "Walk five focus areas: code-quality / risk-integration / correctness / architecture / security." + numbered findings format with file:line requirements + OOS/NO_ISSUES_FOUND instructions.

Each rendered prompt always contains the literal string `code-quality / risk-integration / correctness / architecture / security` (the CI anchor).

Script uses `set -euo pipefail`. Validates arguments and exits 2 with error on invalid values.

**CI compatibility in `skills/design/SKILL.md`**: The launch blocks in SKILL.md must contain the CI-required slash-separated enum. Add a comment line immediately before each renderer call:
  `# Focus area enum anchor for CI: code-quality / risk-integration / correctness / architecture / security`
This satisfies the unquoted-enum grep.

Add `skills/design/scripts/render-plan-review-prompt.md` sibling doc.

### Step 6: Update `skills/design/SKILL.md` Step 3 launch blocks (Sub-task C)

In `skills/design/SKILL.md` Step 3, under `### Cursor Archetype Reviewers (2 slots)` and `### Codex Archetype Reviewers (2 slots)`, replace the 4 long inline `--prompt "..."` strings with calls using `--prompt-file`.

**Process substitution NOT used (FINDING_1)**: Render to an explicit temp file first, check renderer exit code, then pass via `--prompt-file`:

```bash
# Focus area enum anchor for CI: code-quality / risk-integration / correctness / architecture / security
_arch_prompt_file="$DESIGN_TMPDIR/render-plan-arch.prompt"
bash "${CLAUDE_PLUGIN_ROOT}/skills/design/scripts/render-plan-review-prompt.sh" \
  --archetype arch --vendor cursor --plan-file "$DESIGN_TMPDIR/plan.txt" \
  > "$_arch_prompt_file"
${CLAUDE_PLUGIN_ROOT}/scripts/launch-review.sh --tool cursor \
  --output "$DESIGN_TMPDIR/cursor-plan-arch-output.txt" \
  --timeout 1800 --timing-task-kind cursor-plan-arch \
  --prompt-file "$_arch_prompt_file"
```

And similarly for cursor-edge, codex-innovation, codex-pragmatic.

**Fallback paths updated (FINDING_6)**: For each fallback path (Cursor→Codex, Codex→Cursor), update the prose to call the renderer with the fallback vendor:
  - Cursor-Arch fallback to Codex: `render-plan-review-prompt.sh --archetype arch --vendor codex`
  - Cursor-Edge fallback to Codex: `render-plan-review-prompt.sh --archetype edge --vendor codex`
  - Codex-Innovation fallback to Cursor: `render-plan-review-prompt.sh --archetype innovation --vendor cursor`
  - Codex-Pragmatic fallback to Cursor: `render-plan-review-prompt.sh --archetype pragmatic --vendor cursor`
  - Claude subagent fallbacks: continue using reviewer-templates.md path (not renderer, per FINDING_7).

Update `skills/design/references/plan-review.md` to note that primary and fallback external launch blocks now call `render-plan-review-prompt.sh`, with the collection/voting/finalization procedure unchanged.

### Step 7: Add test harness for renderer (Sub-task C + D)

Create `skills/design/scripts/test-plan-review-prompt.sh`:

For each of the 8 combinations (4 archetypes × 2 vendors: codex/cursor), assert:
  1. Exit code 0.
  2. Output contains `code-quality / risk-integration / correctness / architecture / security` (the CI anchor).
  3. Output contains the instruction "NO_ISSUES_FOUND" (as a sentinel instruction — it tells the reviewer what to output if no issues; the plan content is not pre-populated with this value). (FINDING_3 fix: the instruction MUST be present, not absent.)
  4. Output contains the plan file content reference (path appears or plan content is included).
  5. For codex vendor: output is shorter (fewer characters) than the verbose 200+ word current form — confirms terse style.
  6. For cursor vendor: output references "path" or "file" (path-centric check).
  7. Output does not end with just "NO_ISSUES_FOUND" — it contains role/rubric text.

Test invalid --archetype and --vendor values exit 2 with an error message.
Test missing --plan-file exits 2.
Test renderer invoked via `bash` (no executable bit required).

Create `skills/design/scripts/test-plan-review-prompt.md` sibling stub.

**Makefile wiring (FINDING_2)**: Add `test-plan-review-prompt` to:
- `Makefile`: new target calling `bash skills/design/scripts/test-plan-review-prompt.sh`
- `.PHONY` list
- Appropriate `test-harnesses-N` shard (follow the existing pattern for design tests)
- `docs/linting.md` harness table
- Verify whether `agent-lint.toml` needs exclusion for `.sh`/`.md` in `skills/design/scripts/`

### Step 8: Sub-task E OOS issues

After the implementation is complete, file two GitHub issues via `/issue`:
1. "[Research] Smaller Codex model for reviewer slots" — evaluate whether a smaller/cheaper Codex model can serve reviewer slots without quality loss.
2. "[Research] Session threading for concurrent reviewer launches" — evaluate subprocess or async coordination to reduce total wall-clock time.

These are filed as OOS from the combined issue, not implemented in this PR.

### Step 9: Run relevant-checks and verify CI compatibility

- Run `make test-launch-review` — verify preamble changes pass.
- Run `make test-design-manifest` — verify design manifest scripts.
- Run `bash scripts/test-review-structure.sh` and `bash scripts/test-implement-structure.sh` — confirm focus-area enum checks pass in review/implement SKILL.md.
- Run `bash skills/design/scripts/test-plan-review-prompt.sh` — confirm renderer output.
- Manual verification: `grep 'code-quality / risk-integration / correctness / architecture / security' skills/design/SKILL.md` — finds comment anchors.

### Verification Criteria

1. `grep 'HARD CONSTRAINTS — your role is read-only review' scripts/launch-review.sh` — present in both preamble variables.
2. `grep 'code-quality / risk-integration / correctness / architecture / security' skills/design/SKILL.md` — finds CI anchor comments before each renderer call.
3. `bash skills/design/scripts/test-plan-review-prompt.sh` — all assertions pass.
4. `bash scripts/test-launch-review.sh` — all assertions pass.
5. CI focus-area enum check passes for all three SKILL.md files.
6. `grep 'code-quality / risk-integration / correctness / architecture / security' skills/review/SKILL.md skills/implement/SKILL.md` — enum still present inline (compressed not removed).

### Files Modified Summary

New files:
- `skills/shared/focus-area-prompt.md`
- `skills/design/scripts/render-plan-review-prompt.sh`
- `skills/design/scripts/render-plan-review-prompt.md`
- `skills/design/scripts/test-plan-review-prompt.sh`
- `skills/design/scripts/test-plan-review-prompt.md`

Modified files:
- `.github/workflows/ci.yaml` (add focus-area-prompt.md to BACKTICKED_FILES)
- `scripts/launch-review.sh` (preamble shrinkage, explicit prohibition retained for Cursor)
- `scripts/launch-review.md` (reflect preamble change)
- `scripts/test-launch-review.sh` (update preamble assertions)
[TRUNCATED — plan-goals-test exceeded 14000 chars]
