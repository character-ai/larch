## Goal
Remove dormant SESSION_ENV_PATH nested-mode branches and --caller-env argv plumbing from skills/design/SKILL.md and its subtree

## Implementation Plan
## Plan

Remove dormant nested-mode logic from `/design` SKILL.md and the `/design` subtree, while closing a latent `CLAUDE_PLUGIN_ROOT` availability gap that the cleanup would otherwise expose. The on-disk SKILL.md cannot rely on a `SESSION_ENV_PATH`-gated awk recovery snippet (always unreachable in standalone mode) to populate `CLAUDE_PLUGIN_ROOT`; Step 0a must establish it explicitly before `session-setup.sh` runs.

### Files to modify

#### Primary target

1. **`skills/design/SKILL.md`** (~840 lines → ~720 net)
   - **Step 0a opening Bash block**: insert `export CLAUDE_PLUGIN_ROOT='${CLAUDE_PLUGIN_ROOT}'` as the first line of the Bash block, BEFORE the `timing-ledger.sh mark` call. The on-disk SKILL.md carries the literal `'${CLAUDE_PLUGIN_ROOT}'` template token; Claude Code expands `${CLAUDE_PLUGIN_ROOT}` to the install-time absolute path when loading the SKILL.md, so the orchestrator sees an expanded value and the variable is non-empty for the rest of the session. Verify by inspecting `$DESIGN_TMPDIR/source-env.sh` after Step 0a — must contain `export CLAUDE_PLUGIN_ROOT=<absolute-path>` (no literal `${` token).
   - **Step 0a opening Bash block**: delete the leading awk `LARCH_CLAUDE_PLUGIN_ROOT` recovery snippet (the `if [ -z ... ] && [ -n "${SESSION_ENV_PATH:-}" ] ...; export CLAUDE_PLUGIN_ROOT` block).
   - **Step 0a Bash block**: remove the `if [ -n "${SESSION_ENV_PATH:-}" ]; then _ss_args+=(--caller-env "$SESSION_ENV_PATH"); fi` conditional. `_ss_args` becomes `(--prefix claude-design --skip-branch-check --skip-repo-check --check-reviewers)` unconditionally.
   - **Step 0a prose**: rewrite "include `--caller-env "$SESSION_ENV_PATH"` only when that variable is non-empty — Anti-pattern #4" to drop the parenthetical. Delete the paragraph beginning "Only include `--caller-env "$SESSION_ENV_PATH"` in `_ss_args` when…"
   - **Execution-issues logging paragraphs**: collapse the "for nested runs" and "for standalone" paragraphs into one. Always log to `$DESIGN_TMPDIR/execution-issues.md`. Drop the `$(dirname "$SESSION_ENV_PATH")/execution-issues.md` fallback throughout the file.
   - **Step 0b sub-steps 3.2-3.6, Step 5b sub-steps 3-7**: drop `when SESSION_ENV_PATH is non-empty` qualifiers; use the standalone log target everywhere.
   - **Anti-patterns section**: delete rule #4 (NEVER pass `--caller-env`...) and rule #7 (NEVER emit step breadcrumbs...). Renumber: rule 5 → 4, rule 6 → 5. No surviving rule cross-references #4 or #7.
   - **Per-Bash-block recovery prelude (19 occurrences in Steps 0c, 1c, 1d, 1e, 2a, 2a.5, 2b, 3, 3.5, 3b, 4, 4b, 5)**: delete the `if [ -z "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -n "${SESSION_ENV_PATH:-}" ]...; export CLAUDE_PLUGIN_ROOT` block following the source-line in every Bash prelude. The single source-line `[ -f ~/.cache/larch/sessions/current-design-env-$PPID.sh ] && source ~/.cache/larch/sessions/current-design-env-$PPID.sh` becomes the entire prelude.
   - **Bash block prelude prose paragraph**: rewrite to drop awk and nested-mode references. New contract: "Step 0a writes `$DESIGN_TMPDIR/source-env.sh` containing `DESIGN_TMPDIR`, `SESSION_TMPDIR`, `SESSION_ID`, `CLAUDE_PLUGIN_ROOT`, and reviewer presence/availability booleans. Every later Bash block prepends the source line."
   - **Step 3 / 3.5 / 3b token-ledger rehydration**: delete the `LARCH_TOKEN_SESSION_ID=$("...read-session-env-key.sh"...)` + `LARCH_CLAUDE_SOURCE_FILE=...` + `export ...` + `token-ledger.sh mark` block. Keep only `timing-ledger.sh mark`.
   - **Step 3 plan-review tally caller**: drop `--session-env-path "$SESSION_ENV_PATH"` from the `ACTION=TALLY ARGS=...` `printf` line. Also drop the same flag from the `dispatch-plan-voters.sh` invocation in Step 3 (both call sites). The dispatcher continues to accept the flag (used by `/review` and `/implement`), but `/design` no longer passes it.
   - **Step 3 prose**: drop the "when SESSION_ENV_PATH is non-empty, accepted non-security OOS is also written…" subordinate clause; drop the inline-print conditional. Always print the tally inline.
   - **Step 5b sub-steps 3-7**: drop conditional logging-target branches. `append-tool-failure.sh --log` target is always `$DESIGN_TMPDIR/execution-issues.md`. Preserve `${REPO:+--repo "$REPO"}`.
   - **Step 5c prose**: drop the conditional-publish-target predicate; keep the simpler standalone predicate: cleanup runs when `PLAN_WRITE_OK=true` AND `STANDALONE_HEAVY_FAILED` is unset/false AND (`SESSION_ID` empty OR `PUBLISH_OK=true`).
   - **`## Progress Reporting` and `## Verbosity Control` sections**: rewrite sentences gated on `SESSION_ENV_PATH`-non-empty (e.g., "When `SESSION_ENV_PATH` is non-empty (nested under another skill)…"). Replace with standalone-only behavior. Drop the "nested mode" carve-out paragraph entirely.
   - **`timing-ledger.sh` and `token-ledger.sh` invocations**: drop the leading `SESSION_ENV_PATH="$SESSION_ENV_PATH"` env-prefix from all `mark` calls (~7 occurrences).
   - **Binding sweep rule**: after the enumerated bullets, the implementer MUST run `grep -n SESSION_ENV_PATH skills/design/SKILL.md` and `grep -n -- '--caller-env' skills/design/SKILL.md`; both greps must return zero lines. The enumerated bullets are non-exhaustive examples; the sweep result is binding.

2. **`skills/design/references/approval-gates.md`** (2 SESSION_ENV_PATH refs)
   - Line 80: drop the `even when SESSION_ENV_PATH is non-empty` qualifier and the `omit the optional rejected/OOS context blocks` nested-mode clause from the Gate B "Always show the table" paragraph.
   - Line 115: drop the Gate C presentation conditional. Always print the plan under `## Final Design Plan`.

3. **`skills/design/references/plan-review-quick.md`** (4 SESSION_ENV_PATH refs) — drop all 4 conditional branches.

4. **`skills/design/references/dialectic-execution.md`** (1 SESSION_ENV_PATH ref) — drop the conditional.

5. **`skills/design/references/sketch-launch.md`** (2 SESSION_ENV_PATH refs at lines 17, 21) — rewrite "Launch failure logging" to remove the `when SESSION_ENV_PATH is non-empty` clause. Replace `--log "$(dirname "$SESSION_ENV_PATH")/execution-issues.md"` with `--log "$DESIGN_TMPDIR/execution-issues.md"` in the code example.

6. **`skills/design/references/plan-review.md`** (7 SESSION_ENV_PATH refs)
   - Drop all 7 conditional branches.
   - **Lines 105-112** (the `dispatch-plan-voters.sh` example): drop `--session-env-path "$SESSION_ENV_PATH"` from the example.

#### Helper script and its sibling doc

7. **`skills/design/scripts/tally-plan-review.sh`** (8 SESSION_ENV_PATH refs)
   - Drop the `SESSION_ENV_PATH="${SESSION_ENV_PATH:-}"` initializer (line 17), the `--session-env-path` argv case (line 43), the parent-tmpdir `oos-accepted-design.md` branch (lines 97-98), the `read_session_env_key` helper (lines 123-137), the `PREV_IMPLEMENT_TMPDIR` / `POST_PLAN_WORKFLOW_PATH` resolution, and the downstream `/implement` tally-batch flushing branch.
   - Update usage/help text.

8. **`skills/design/scripts/tally-plan-review.md`** (the `.md` sibling required by `.claude/rules/script-md-siblings.md`) — remove documentation of `--session-env-path`, the parent-tmpdir OOS handoff, and the HARD-path `/implement` tally-batch flushing prose. Inspect lines ~14-23, 22, 23, 34.

9. **`skills/design/scripts/test-tally-plan-review.sh`** (2 SESSION_ENV_PATH refs) — delete the test cases exercising `--session-env-path` and parent-directory `oos-accepted-design.md`. Run after edits.

#### CI assertion

10. **`scripts/test-design-structure.sh`** (line 293 + 5 new assertions)
    - Delete the assertion that pins the "Only include `--caller-env`..." sentence.
    - **Add 5 new assertions** using the negative-grep idiom `! grep -Eq` (never `grep -Eqc ... must return 0`, which is semantically inverted):
      - **A1**: `! grep -Eq 'SESSION_ENV_PATH' skills/design/SKILL.md`
      - **A2**: `! grep -Eq -- '--caller-env' skills/design/SKILL.md`
      - **A3**: `! grep -rEq 'SESSION_ENV_PATH' skills/design/`
      - **A4**: `! grep -rEq -- '--caller-env' skills/design/`
      - **A5**: the Step 0a Bash block contains `export CLAUDE_PLUGIN_ROOT='${CLAUDE_PLUGIN_ROOT}'` BEFORE the `session-setup.sh` invocation (capture `step0_section` and run an awk ordering check).

### Approach

Single-pass mechanical removal with one targeted addition (CLAUDE_PLUGIN_ROOT export at Step 0a) and one structural rule (sweep-to-zero is binding). Order:

1. Insert `export CLAUDE_PLUGIN_ROOT='${CLAUDE_PLUGIN_ROOT}'` at top of Step 0a's first Bash block.
2. Edit `skills/design/SKILL.md` deletions; apply the binding sweep rule at the end.
3. Edit each of the 5 references files.
4. Edit `skills/design/scripts/tally-plan-review.sh`.
5. Edit `skills/design/scripts/tally-plan-review.md`.
6. Edit `skills/design/scripts/test-tally-plan-review.sh` and run it.
7. Edit `scripts/test-design-structure.sh` (delete old assertion + add A1-A5 using negative-grep idiom).
8. Run the sweep verification on SKILL.md.
9. Run the subtree verification.
10. Run `bash scripts/test-design-structure.sh`.
11. Run `bash scripts/relevant-checks.sh`.
12. Run `make lint`.

### Tradeoffs and key decisions

1. **CLAUDE_PLUGIN_ROOT template form**: author with the literal `'${CLAUDE_PLUGIN_ROOT}'` template token on disk; Claude Code's loader expands it. Risk: if Claude Code stops expanding `${CLAUDE_PLUGIN_ROOT}` inside Bash string literals, paths fail with exit 127. Static CI assertion (A5) verifies the template-token form is on disk and ordered correctly; it cannot exercise the expansion mechanism itself. PR description should note this limitation honestly.

2. **Negative-grep idiom**: the four new structure assertions use `! grep -Eq PATTERN FILE`. `grep -Eqc ... must return 0` is inverted (since `grep -q` exits 1 on zero matches).

3. **Sweep-to-zero is binding**: per-bullet enumeration is informational; the binding rule is `grep -n SESSION_ENV_PATH skills/design/SKILL.md == 0`. SKILL.md carries 82 occurrences; enumerated bullets cannot catch them all reliably.

4. **`tally-plan-review.md` sibling doc**: `.claude/rules/script-md-siblings.md` requires the sibling to be updated in the same PR.

5. **`dispatch-plan-voters.sh` `--session-env-path` flag retention**: dispatcher's argv parser keeps the flag (used by `/review` and `/implement`); only `/design`'s use is dropped.

6. **Anti-pattern renumbering**: keep the list contiguous (1-5). No surviving rule cross-references #4 or #7.

7. **`/implement` tally-batch flushing removal**: dropping `PREV_IMPLEMENT_TMPDIR` and `POST_PLAN_WORKFLOW_PATH` from `tally-plan-review.sh` means `/implement` cannot drive `/design`'s tally back into a log batch. This was already non-functional (since `/design` is standalone-only after #2588); the dead code masked it.

8. **Aggressive simplification**: chosen. Issue acceptance "Bash block prelude shrinks to the single source-line" requires deletion of conditional structure.

9. **Helper-script scope**: `scripts/session-setup.sh` and `scripts/test-session-setup-*.sh` are NOT touched. `--caller-env` remains live for `/review` and `/implement`.

### Edge cases

- Stale CLAUDE_PLUGIN_ROOT in orchestrator shell: the new `export` unconditionally overwrites it. Safe.
- Multiple concurrent `/design` sessions (#2599/#2602 PID-key scenario): unaffected — symlink scheme preserved.
- `$DESIGN_TMPDIR` cleanup on failure: unchanged — standalone log target preserved.
- `tally-plan-review.sh` callers outside SKILL.md: only Step 3 invokes it; safe to drop argv. Test after edits.
- Cross-skill references in `skills/shared/*.md`: mention `--caller-env` for `/review` and `/implement`, not `/design`. Unchanged.
- Plugin upgrade path: in-progress `$DESIGN_TMPDIR` from previous version — single-line prelude `[ -f ... ] && source ...` degrades silently.

### Failure modes

1. **CLAUDE_PLUGIN_ROOT template expansion does not occur**: orchestrator sees the unexpanded `${...}` token; sketch launches fail with exit 127. Earliest warning: next `/design` invocation fails Step 2a launches. Mitigation: A5 verifies the template-token form is on disk and ordered correctly; static CI cannot exercise runtime expansion. Document the limitation in the PR.
2. **Hidden SESSION_ENV_PATH reference in a non-obvious file**: binding subtree sweep + A3/A4 catch this. Earliest warning: `bash scripts/test-design-structure.sh` fails on A3/A4.
3. **`tally-plan-review.sh` consumer in a forgotten code path**: only Step 3 invokes it; verified by grep. Earliest warning: `bash skills/design/scripts/test-tally-plan-review.sh` fails on argv parse.

### Testing strategy

- **Unit**: `bash skills/design/scripts/test-tally-plan-review.sh`.
- **Structure**: `bash scripts/test-design-structure.sh` — A1-A5 assertions.
- **Lint**: `bash scripts/relevant-checks.sh`.
- **Full lint**: `make lint`.
- **End-to-end smoke**: out of scope for this PR (heavy operationally); offline structure tests cover the static contract. Document manual verification in the PR if performed.

## Acceptance

1. `grep -n SESSION_ENV_PATH skills/design/SKILL.md` returns zero lines.
2. `grep -n -- '--caller-env' skills/design/SKILL.md` returns zero lines.
3. `grep -rn SESSION_ENV_PATH skills/design/` returns zero lines.
4. `grep -rn -- '--caller-env' skills/design/` returns zero lines.
5. Bash block prelude in every step is the single source-line `[ -f ~/.cache/larch/sessions/current-design-env-$PPID.sh ] && source ~/.cache/larch/sessions/current-design-env-$PPID.sh` — no awk recovery snippet follows it. Exception: Step 0a's first Bash block has the new `export CLAUDE_PLUGIN_ROOT='${CLAUDE_PLUGIN_ROOT}'` line at the top instead of the source-line.
6. `bash scripts/relevant-checks.sh` passes.
7. `make lint` passes.
8. `bash scripts/test-design-structure.sh` passes with new assertions A1-A5.
9. `bash skills/design/scripts/test-tally-plan-review.sh` passes.
10. Anti-patterns section has 5 rules (1-5), not 7. Rules #4 and #7 deleted; rules #5 and #6 renumbered to #4 and #5.
11. `skills/design/scripts/tally-plan-review.md` no longer documents `--session-env-path`, parent OOS handoff, or HARD-path tally-batch flushing.
12. `skills/design/references/plan-review.md` example at lines 105-112 no longer passes `--session-env-path` to `dispatch-plan-voters.sh`.

diff_lines: 260

## Test plan
(no test plan section in plan-file)
