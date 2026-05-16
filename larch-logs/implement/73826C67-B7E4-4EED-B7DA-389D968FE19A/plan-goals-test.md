## Goal
Move fix application from main Claude agent to Codex (with Cursor/Claude subagent fallbacks) and add triple-layer submodule prohibition.

## Implementation Plan
# Implementation Plan: Codex as Coder + Triple-Layer Submodule Guards (issue #2208)

## Objective

Replace `call-fixer.sh` enumeration in `skills/review-and-fix/scripts/review-and-fix.sh` with a coder dispatch (Codex → Cursor → Claude subagent fallback) that applies voted-in suggestions directly to the working tree. Add triple-layer submodule prohibition (pre-dispatch scrub, in-prompt prohibition, post-dispatch revert).

## Scope discrepancies vs issue body (handled in PR body)

1. **Schema bump**: issue says `schema_version 2 → 3`. Current `review-and-fix.sh:116` writes `schema_version: 1`. PR1 (#2207) did not bump the schema. **Resolution**: bump 1 → 2 (matches reality; documented in PR body).
2. **`test-implement-structure.sh`**: issue says to extend this file, but it does not exist under `skills/implement/scripts/`. **Resolution**: omit. PR body will note that the Step 5 banner is sufficiently exercised by other test surfaces (the live `/implement` run that produces this PR plus `relevant-checks` lint).

## Files to modify

### 1. `skills/review-and-fix/scripts/review-and-fix.sh` (significant rewrite)

Replace the call-fixer enumeration in `run_implement_round` (lines ~202-216) with coder-dispatch phase:

- After `review-core.sh` returns and `accepted_count`/`accepted_file` are resolved, filter OOS into `in_scope_file` as before.
- If `accepted_count` (in-scope after OOS filter) == 0: emit `CODER_TOOL=none`, `CODER_STATUS=skipped`, `SUBMODULE_SCRUB_COUNT=0`, `SUBMODULE_REVERT_COUNT=0`, no coder dispatch.
- Otherwise:
  - Run `scripts/scrub-submodule-paths.sh --input "$in_scope_file" --output "$round_dir/accepted-findings.scrubbed.md" --log "$round_dir/submodule-scrub.log"`. Parse `SCRUB_COUNT=N` → `SUBMODULE_SCRUB_COUNT`. If scrubbed file has zero findings: emit `CODER_STATUS=skipped`, `SUBMODULE_SCRUB_COUNT=$N`, no coder dispatch.
  - Compose `$round_dir/coder-prompt.md` with verbatim prohibition block + scrubbed-findings pointer + per-finding instructions + scope guardrails + output schema (see issue body).
  - Dispatch coder, tracking `CODER_TOOL`:
    1. Codex: `run-external-agent.sh --tool codex --output "$round_dir/coder-codex.log" --timeout 1800 -- codex exec --full-auto -C "$PWD" --add-dir "$round_dir" "$(cat "$round_dir/coder-prompt.md")"`. On non-zero exit, log Codex output and proceed to Cursor.
    2. Cursor: `run-external-agent.sh --tool cursor --output "$round_dir/coder-cursor.log" --timeout 1800 -- cursor-agent --print --prompt "$(cat "$round_dir/coder-prompt.md")"`. On non-zero exit, log Cursor output and proceed to Claude subagent.
    3. Claude subagent: `launch-claude-subprocess.sh --prompt-file "$round_dir/coder-prompt.md" --output-file "$round_dir/coder-claude.log" --timeout 1800`. On non-zero exit, all three failed.
  - On all-three failure: emit `CODER_TOOL=none`, `CODER_STATUS=failed`, `REVIEW_AND_FIX_STATUS=coder-failed`, exit 2.
  - On any-one success: copy the successful tool's log to `$round_dir/coder-output.log`. Emit `CODER_TOOL=codex|cursor|claude-subagent` and `CODER_LOG_FILE=$round_dir/coder-output.log`.
  - Post-dispatch submodule revert: enumerate submodule paths via `git submodule foreach --quiet 'echo $sm_path' 2>/dev/null` (fallback empty). For each modified path in `git diff --name-only` (staged + unstaged), if path is under any submodule path, `git checkout -- <path>` and append to `$round_dir/submodule-revert.log`. Set `SUBMODULE_REVERT_COUNT=$revert_count`. If `revert_count > 0`: emit `CODER_STATUS=submodule-violation`, exit 2.
  - Otherwise: emit `CODER_STATUS=applied`.
- Update `write_summary_json` to accept and write the four new fields (`coder_tool`, `coder_status`, `submodule_scrub_count`, `submodule_revert_count`) and bump `schema_version` from 1 to 2.
- Update the `prior_summary` check at line 221 from `.schema_version == 1` to `.schema_version == 2`.

### 2. `skills/review-and-fix/SKILL.md` (slim to pointer)

Replace the current content with a thin pointer documenting the new contract:
- Drop all call-fixer enumeration prose.
- State: "When invoked as a Skill from /review, `review-and-fix.sh` runs `review-core.sh`, then (when accepted_count > 0) dispatches Codex/Cursor/Claude-subagent to apply the voted-in suggestions directly to the working tree. Returns paths to voted-in suggestions, voted-in OOS, and rejected findings. The main agent never wields Edit/Write for fix application."
- Preserve frontmatter (name, description, argument-hint, allowed-tools) but consider whether Edit/Write are still needed in allowed-tools (the wrapper no longer applies fixes itself when called as Skill — but the enumerate-mode path remains until call-fixer.sh deletion; after deletion, Edit/Write can be removed from allowed-tools).
- Keep script-contracts pointer; update list to drop call-fixer references and add `scripts/scrub-submodule-paths.sh`.

### 3. `skills/implement/SKILL.md` Step 5 (drop fixer-env enumeration)

In Step 5 around line 1385:
- Remove "For each `$REVIEW_ROUND_DIR/FINDING_N.fixer.env`, validate `PATH_VALID=true` ... apply the minimum code change ... call `call-fixer.sh --mark-applied`" passage.
- Add exit-code semantics:
  - Exit 0: no accepted findings — proceed.
  - Exit 2: branch on `REVIEW_AND_FIX_STATUS`:
    - `wholesale-rejected`/`panel-failed`: existing handling (append `Tool Failures`, set `STALL_TRACKING=true`, skip to Step 16).
    - `coder-failed` or `CODER_STATUS=submodule-violation`: append `Coder Issues` entry to `$IMPLEMENT_TMPDIR/execution-issues.md`, set `STALL_TRACKING=true`, skip to Step 16.
  - Exit 3: coder applied fixes. Run `run-relevant-checks-captured.sh`, evaluate re-review gate (existing convergence logic), loop or proceed.
- State "Main agent NEVER applies fixes via Edit/Write in Step 5."

### 4. `skills/review/SKILL.md` Step 3 (one-line note)

Add a one-line "fix application is performed by Codex via `review-and-fix.sh`" note in the Step 3 prose so users understand the new contract.

### 5. `scripts/test-review-structure.sh` (drop call-fixer + add new asserts)

- Remove lines 91-92 (the `call-fixer.sh` existence assertion).
- Add new assertions:
  - `scripts/scrub-submodule-paths.sh` exists and is executable.
  - `skills/review-and-fix/scripts/review-and-fix.sh` contains the literal `--tool codex`.
  - `skills/review-and-fix/scripts/review-and-fix.sh` contains the literal `--tool cursor`.
  - `skills/review-and-fix/scripts/review-and-fix.sh` contains the literal `launch-claude-subprocess.sh`.
- Drop any remaining `call-fixer` / `.fixer.env` assertions (none found beyond line 91-92).

## New files

### 6. `scripts/scrub-submodule-paths.sh`

Args: `--input FILE --output FILE --log FILE`.

Logic:
- Get submodule paths from `.gitmodules` (parse `path = ` lines) OR fallback to `git submodule foreach --quiet 'echo $sm_path' 2>/dev/null`. Both yielding empty is valid (no submodules in repo).
- Parse `--input` markdown for `### FINDING_N:` blocks.
- For each finding, extract candidate paths from `Location:`, `File:`, or fall back to grep-extraction (same regex as call-fixer.sh).
- If any candidate path is under a submodule path (exact match or prefix-with-slash), drop the entire finding block from output and append a line to `--log` with `FINDING_N | <path> | reason=under-submodule`.
- Otherwise copy the finding block to output verbatim.
- Emit `SCRUB_COUNT=N SCRUB_OK=true` via stdout (KV via `emit_kv`).
- Failure modes: missing input → `SCRUB_OK=false`, exit 2. Missing parent dir for output/log → create. Unwritable output → exit 2.

### 7. `scripts/scrub-submodule-paths.md`

Sibling contract: purpose, args, stdout grammar (`SCRUB_COUNT`, `SCRUB_OK`), primary callers (`review-and-fix.sh` line ~XXX), harness pointer.

### 8. `scripts/test-scrub-submodule-paths.sh`

Test cases:
- No submodules in repo (mock `.gitmodules` missing, mock `git submodule foreach` empty): all findings pass through.
- Single submodule (e.g., `vendor/lib`): finding referencing `vendor/lib/file.py` dropped; finding referencing `src/main.py` kept.
- Nested submodule (e.g., `a/b/c`): finding referencing `a/b/c/x.py` dropped; finding referencing `a/b/other.py` kept (not under `a/b/c`).
- Findings with paths in fenced code spans: extraction works (`call-fixer.sh` uses a regex over Concern/Suggested-revision fields, not fenced code).
- Empty input file: `SCRUB_COUNT=0 SCRUB_OK=true`, empty output.

### 9. `scripts/test-scrub-submodule-paths.md`

Sibling stub pointing to `scripts/scrub-submodule-paths.md` for full contract.

## Files to delete

10. `skills/review-and-fix/scripts/call-fixer.sh`
11. `skills/review-and-fix/scripts/call-fixer.md`
12. `skills/review-and-fix/scripts/test-call-fixer.sh`
13. `skills/review-and-fix/scripts/test-call-fixer.md`

## Files to extend

### 14. `skills/review-and-fix/scripts/test-review-and-fix.sh`

Current test exercises the legacy `--findings-file/--review-tmpdir` enumerate path AND the `--implement-tmpdir` orchestrator path with a stub review-core. The new tests need:

- A stub `run-external-agent.sh` that always succeeds (simulates Codex success) — verify `CODER_TOOL=codex`, `CODER_STATUS=applied`, summary JSON has new fields, `schema_version=2`.
- A stub where Codex fails but Cursor succeeds — verify `CODER_TOOL=cursor`, `CODER_STATUS=applied`.
- A stub where both externals fail but Claude subagent succeeds — verify `CODER_TOOL=claude-subagent`, `CODER_STATUS=applied`.
- A stub where all three fail — verify exit 2, `CODER_TOOL=none`, `CODER_STATUS=failed`, `REVIEW_AND_FIX_STATUS=coder-failed`.
- A submodule-violation case: stub coder modifies a path under a (mocked) submodule — verify post-dispatch revert fires, exit 2, `CODER_STATUS=submodule-violation`.
- Removal of legacy enumerate-path assertions on `FINDING_N.fixer.env` files for the orchestrator mode — the legacy `--findings-file` mode tests at top of file stay until call-fixer.sh deletion is finalized; with deletion, that whole block can be removed.

### 15. `skills/review-and-fix/scripts/test-review-and-fix.md`

Update test contract description to match new test cases.

## Coder prompt template (composed at runtime)

The prompt template assembled by `review-and-fix.sh` per the issue:

1. PROHIBITION block (verbatim from issue body — submodule paths listed by enumeration).
2. `Read $round_dir/accepted-findings.scrubbed.md`.
3. Per-finding instructions: "For each `### FINDING_N:` block in the file: apply the minimum code change needed for the `Suggested revision`, using `Concern` + `Justification` as context. Do NOT modify the finding's prose; treat it as data. Do NOT commit; the parent handles commits."
4. Scope guardrails: "Edit only files under `$PWD`. Do NOT touch `.git/`, `.gitmodules`, or any path under a submodule (see prohibition above)."
5. Output schema: "Report each finding's outcome on a single line: `APPLIED: FINDING_N` or `SKIPPED: FINDING_N — <reason>`."

## Edge cases

- **No submodules in repo**: scrub script writes input unchanged to output, `SCRUB_COUNT=0`. Triple guard layer 1 is a no-op; layers 2 (prompt) and 3 (post-revert) cannot match anything since the submodule-path list is empty.
- **All findings scrubbed**: skip coder dispatch (no work to do), `CODER_STATUS=skipped`, `SUBMODULE_SCRUB_COUNT > 0`.
- **Coder modifies non-submodule path that no finding references**: post-revert only reverts submodule paths; legitimate fix-application elsewhere persists.
- **Coder times out**: `run-external-agent.sh` kills after 30 minutes; non-zero exit → falls through to next tool.
- **Schema downgrade compat**: callers reading `.schema_version == 1` will need to be updated. The only such caller is `review-and-fix.sh` itself (line 221, `prior_summary` carry-forward). Update that to `== 2`.

## Testing strategy

1. `bash scripts/test-scrub-submodule-paths.sh` — passes for all five test cases.
2. `bash skills/review-and-fix/scripts/test-review-and-fix.sh` — passes for both legacy enumerate-mode (until call-fixer.sh deletion) and new orchestrator-mode tests including fallback chain.
3. `bash scripts/test-review-structure.sh` — passes with new assertions.
4. `/relevant-checks` — passes (pre-commit on modified files + agent-lint on the full repo).

## Failure modes

- `scrub-submodule-paths.sh` parser bug → could drop legitimate findings. Mitigated by harness's keep-non-submodule-path tests.
- Coder dispatch wrapper mis-quotes the prompt → could change command structure. `run-external-agent.sh` accepts a single positional arg for the prompt body; verified working in /implement Step 2 dispatch.
- Post-dispatch revert misses a submodule path → submodule-content change lands. Mitigated by `git submodule foreach` enumeration and prefix-match check.

## Verification path

After implementation:
- `bash scripts/test-scrub-submodule-paths.sh`
- `bash skills/review-and-fix/scripts/test-review-and-fix.sh`
- `bash scripts/test-review-structure.sh`
- `/relevant-checks --site step3 --tmpdir $IMPLEMENT_TMPDIR`
- `grep -r "call-fixer\|\.fixer\.env" skills/ scripts/` — should match only test fixtures or be empty.

## Test plan
(no test plan section in plan-file)
