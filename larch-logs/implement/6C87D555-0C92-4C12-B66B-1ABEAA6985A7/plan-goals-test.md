## Goal
Implement issue #3386: [IMPLEMENTING] lint-fix-loop Codex cascades on pre-existing failures when relevant-checks.sh runs against full branch diff\n\nlint-fix-loop Codex cascades on pre-existing failures when relevant-checks.sh runs against full branch diff.

## Implementation Plan
## Plan

### Summary

`scripts/lint-fix-loop.sh` `compose_prompt` tells the external coder to "Fix the repository so `scripts/relevant-checks.sh` passes" for every non-per-job site. The coder treats that as a global pass/fail goal and re-runs the full suite, which lints the entire branch diff and surfaces pre-existing failures in unrelated files — causing fix → unrelated failure → fix cascades until timeout (issue #3386, run FA70EBE2).

**Fix:** Make the non-per-job **authoritative goal log-scoped** (repair only failures shown in the redacted checks log). Derive an optional, **non-authoritative** local verification hint from the log when safe: affected file paths plus, only when the log’s failing phase is pre-commit, a display-only `pre-commit run --files …` suggestion with explicit caveats about whole-repo hooks. Do **not** present `pre-commit run --files` or `scripts/relevant-checks.sh` as the coder’s pass/fail condition. The parent loop keeps full-suite re-verification via `run-relevant-checks-captured.sh` after each `LINT_FIX_STATUS=applied`. `scripts/relevant-checks.sh` is unchanged.

## Files to modify/create

### UPDATED: `scripts/lint-fix-loop.sh`

- Add `checks_log_excerpt` — given `log_file`, compute the **same byte window** later embedded under **## Checks Log**: when `log_bytes <= 60000`, use the full file; when `log_bytes > 60000`, use `tail -c 60000` of the file (matching today's truncation banner). Emit that excerpt to stdout or a temp path. **All** log parsing and prompt embedding must consume this excerpt only — never scan the full file when the prompt shows only the tail.
- Add `affected_files_from_log` — read the **checks log excerpt** from `checks_log_excerpt` (not the raw full log when truncated); emit a newline-delimited, deduped list of in-scope paths:
  - Extract candidate tokens with conservative patterns: shellcheck `In <path> line N:`, leading `<path>:<line>` (markdownlint / generic), and whitespace-delimited tokens containing `/` or a known source extension.
  - **Path safety filter** (all must pass before inclusion): existing regular file under `REPO_ROOT` (`[ -f ]`); repo-relative (reject leading `/` and `..` segments); no control characters (mirror `target_cmd_display_from_file`); **reject backticks** `` ` `` and other prompt-container delimiters that could break inline Markdown; **reject leading `-`** so paths cannot be interpreted as `pre-commit` argv flags when echoed in a suggested command.
  - Dedupe (`awk 'NF && !seen[$0]++'`), cap count (e.g. 50). Emit nothing when no token qualifies.
- Add `infer_failure_phase_from_log` — scan the **same excerpt** from `checks_log_excerpt` (last matching phase wins) for `relevant-checks.sh` section banners:
  - `=== Running pre-commit on` → `pre-commit`
  - `=== Running agent-lint ===` → `agent-lint`
  - `=== Running direct relevant make target(s):` → `direct-make`
  - otherwise → `unknown`
  Used only to gate optional verification hints, not to change dispatch.
- In `compose_prompt`, change the **non-per-job** branch (`target_cmd_display` empty):
  - **Primary `fix_sentence` (always log-scoped):**
    - When `affected_files_from_log` is non-empty:  
      `Fix only the failures shown in the checks log for $site_label.`
    - When empty:  
      `Fix only the failures shown in the checks log for $site_label; no scoped file list could be derived from the log. The parent loop will re-run the appropriate verifier.`
    - Do **not** use `Fix the repository so \`scripts/relevant-checks.sh\` passes…` or `Fix the repository so the scoped check \`pre-commit run --files …\` passes…` as the authoritative goal (FINDING_1, FINDING_2, FINDING_6).
  - Leave the **per-job** branch (`target_cmd_display` non-empty) **unchanged**:  
    `Fix the repository so the local command \`$target_cmd_display\` passes for $site_label.`
  - After `fix_sentence`, before "Make the minimum necessary edits", add prompt sections:
    - **`## In-scope files`** — bullet list of affected paths, emitted **only** when the filtered list is non-empty. Render paths as plain list items (no backticks around paths) to avoid delimiter injection (FINDING_3).
    - **`## Optional local verification (non-authoritative)`** — emitted **only** when affected list is non-empty **and** `infer_failure_phase_from_log` is `pre-commit`. Content:
      - State this block is **not** the pass/fail goal; parent owns full verification.
      - Suggest display-only: `pre-commit run --files -- <quoted paths>` (literal `--` before filenames; shell-quote each path).
      - Warn that hooks with `pass_filenames: false` / `always_run` (gitleaks, literal-count, renderer-safety, etc.) still scan the repo and may fail unrelated to the listed files — do not chase those in a loop; fix only log-shown failures (FINDING_2).
    - **Anti-cascade guidance** — **branch by site** (FINDING_5):
      - **Non-per-job:** Forbid running `scripts/relevant-checks.sh` or full-branch `pre-commit` / `agent-lint` as the coder’s verification loop; fix only log / in-scope files; parent re-runs the appropriate verifier after return.
      - **Per-job:** One line only: forbid running `scripts/relevant-checks.sh` as a verification loop; parent re-runs the job command shown in `fix_sentence` (do not forbid `make lint-only` / per-job `agent-lint` named in `target_cmd_display`).
- In `compose_prompt`, compute `log_bytes` and the excerpt **once** via `checks_log_excerpt`; call `affected_files_from_log` / `infer_failure_phase_from_log` on that excerpt; embed the **identical** excerpt bytes under **## Checks Log** (preserve `[truncated to last 60000 bytes]` when `log_bytes > 60000`).
- Preserve unchanged: untrusted-log preamble, `emit_submodule_prohibition`, `FIXED:` / `UNFIXABLE:` contract, checks-log embedding/sanitizing, and all dispatch / revert / HEAD-guard / commit machinery below `compose_prompt`.

### UPDATED: `scripts/lint-fix-loop.md`

- Rewrite behavior item 4 to document:
  - Non-per-job authoritative log-scoped `fix_sentence` (no global `relevant-checks.sh` pass command; empty-parse variant without contradictory verifier ban).
  - `## In-scope files`, phase-gated optional pre-commit hint with `--` terminator and whole-repo-hook caveat.
  - Split anti-cascade text (non-per-job vs per-job).
  - Affected-file extraction filters (existing regular repo-relative file, control-char / backtick / leading-dash rejection, cap).
  - **Excerpt coupling:** when the checks log exceeds 60 000 bytes, parsers and **## Checks Log** both use the same `tail -c 60000` slice; in-scope paths and phase banners outside that window are intentionally excluded so the coder never chases failures absent from the embedded log.
  - `scripts/relevant-checks.sh` unchanged; parent still owns global re-verification.

### UPDATED: `scripts/test-lint-fix-loop.sh`

- **Preserve Cases 9–11:** existing dispatch-failure regressions (codex stderr-tail, cursor stderr-tail, cursor `.diag` fallback) stay as-is; add prompt-composition cases as **12–16** (do not renumber or overwrite Cases 9–11).
- **Case 12 — shellcheck `In <path> line N` (positive):** checks log with `In tracked.txt line 1:` for an existing fixture file; `--site step3`; assert prompt (a) contains log-scoped `fix_sentence` (`Fix only the failures shown in the checks log`), (b) contains `## In-scope files` listing `tracked.txt`, (c) contains non-per-job anti-cascade forbidding `scripts/relevant-checks.sh`, (d) does **not** contain `Fix the repository so` … `scripts/relevant-checks.sh` … `passes`, (e) when log includes `=== Running pre-commit on`, contains optional verification with `pre-commit run --files --` and `tracked.txt`.
- **Case 13 — leading `path:line`:** log line `tracked.txt:1: …` for existing `tracked.txt`; assert same scoped outcomes as Case 12 (in-scope list + no global relevant-checks goal).
- **Case 14 — empty affected list (fallback):** log with no qualifying existing file; assert log-scoped `fix_sentence` with “no scoped file list could be derived”, anti-cascade present, **no** `## In-scope files`, **no** `Fix the repository so` … `scripts/relevant-checks.sh` … `passes`.
- **Case 15 — unsafe path rejection:** fixture file whose name contains a backtick and/or a repo-relative name starting with `-`; assert neither appears in `## In-scope files` or optional command; prompt uses empty-list / log-scoped fallback for that path.
- **Case 16 — excerpt/parser coupling (truncated log):** build a checks log with `log_bytes > 60000` where a qualifying path and `=== Running pre-commit on` appear **only inside the last 60 000 bytes** (padding prefix before them); assert prompt **## Checks Log** shows `[truncated to last 60000 bytes]`, **## In-scope files** lists that path, and optional pre-commit block is present. Repeat with the same path placed **only** before the tail window (outside last 60 000 bytes); assert path is **absent** from **## In-scope files** and optional pre-commit block (log-scoped `fix_sentence` still present).
- **Case 6 (per-job):** keep existing `local command \`…\` passes` assertion; add assert full non-per-job anti-cascade wording is **absent** and per-job one-line `scripts/relevant-checks.sh` prohibition is **present**.
- Keep all existing cases (dispatch safety, HEAD guards, forbidden-path revert, Cases 6 and 9–11) green.

## Approach

- **Single excerpt source of truth** — `checks_log_excerpt` feeds embedding, `affected_files_from_log`, and `infer_failure_phase_from_log` so in-scope hints cannot reference paths or phase banners the coder does not see (FINDING_1).
- **Authoritative goal = log-scoped**; **verification hints = optional and phase-gated** — addresses phase mismatch (FINDING_1), whole-repo pre-commit hooks (FINDING_2), and empty-list contradiction (FINDING_6) without changing `relevant-checks.sh` or callers.
- Reuse per-job `target_cmd_display` shape unchanged; only non-per-job prompt composition changes.
- Path extraction is display-only (loop never executes suggested commands); defense-in-depth filters prevent Markdown injection and argv smuggling (FINDING_3, FINDING_4).
- Determinism comes from removing global pass/fail framing, not from reverting coder edits.

## Edge cases

- **agent-lint / direct-make failure with file paths in log:** in-scope list may still help; **no** optional `pre-commit run --files` block (phase ≠ `pre-commit`).
- **Repo-wide failure, no parseable files:** log-scoped empty-list `fix_sentence`; no in-scope section; no optional pre-commit block.
- **Many files:** cap list and optional command display.
- **Large checks log (>60 000 bytes):** parsers and embedded log share the tail slice only; failures mentioned only in the truncated prefix must not appear in **## In-scope files** or phase-gated hints.
- **Paths with spaces:** shell-quote in optional command; `[ -f ]` still resolves.
- **Malicious / odd filenames:** backtick or leading `-` paths dropped by filter; harness Case 15 locks behavior.
- **Per-job site:** `fix_sentence` unchanged; minimal anti-cascade only.

## Failure modes

- **Parser over-matches:** regular-file + delimiter filters + cap; signal: spurious in-scope entry. Mitigation: conservative patterns.
- **Parser/embed window drift (pre-fix):** if parsers read the full log while the prompt embeds only the tail, in-scope hints can reference unseen paths. Mitigation: `checks_log_excerpt` shared by embed and parsers (FINDING_1); Case 16 locks behavior.
- **Parser under-matches:** log-scoped goal still works; no optional pre-commit hint; parent re-verifies.
- **Coder ignores guidance and runs full suite:** unchanged parent dispatch cap + stall detection; bounded goal reduces cascade likelihood.
- **Optional pre-commit hint still hits whole-repo hooks:** explicit warning in prompt; coder instructed not to loop on unrelated hook failures.

## Testing strategy

- Extend `scripts/test-lint-fix-loop.sh` with Cases 12–16 (prompt composition, including truncated-log excerpt coupling); extend Case 6 assertions as above. Leave existing Cases 9–11 (dispatch stderr/diag regressions) unchanged.
- Run `bash scripts/test-lint-fix-loop.sh`, `bash scripts/test-prompt-template-invariants.sh` (compose_prompt invariants unchanged), `bash scripts/test-implement-structure.sh`.
- Run `bash scripts/relevant-checks.sh` (or `make lint`) on touched files.
- Review `SECURITY.md`: add a line only if backtick/leading-dash rejection beyond existing redacted-log trust model needs explicit documentation.


## Acceptance

- `scripts/lint-fix-loop.sh` non-per-job `compose_prompt` branch (`target_cmd_display` empty) sets a log-scoped `fix_sentence` (repair only failures shown in the checks log) and never frames `scripts/relevant-checks.sh` or `pre-commit run --files …` as the coder's pass/fail goal.
- `checks_log_excerpt`, `affected_files_from_log`, and `infer_failure_phase_from_log` exist and all consume the same byte window embedded under `## Checks Log` (shared `tail -c 60000` slice when the log exceeds 60000 bytes).
- `affected_files_from_log` emits only existing regular repo-relative files, rejecting absolute / `..` paths, control characters, backticks, and leading-dash names; deduped and capped.
- The prompt emits `## In-scope files` (plain bullets, no backticks) only when the filtered list is non-empty, and the `## Optional local verification (non-authoritative)` block (literal `--` before filenames, whole-repo-hook caveat) only when the list is non-empty AND the inferred phase is `pre-commit`.
- Anti-cascade guidance is branched by site: full prohibition for non-per-job; a one-line `scripts/relevant-checks.sh` prohibition for per-job. The per-job `fix_sentence` is unchanged.
- `scripts/relevant-checks.sh` is unchanged; the untrusted-log preamble, `emit_submodule_prohibition`, the `FIXED:` / `UNFIXABLE:` contract, and all dispatch / revert / HEAD-guard / commit machinery below `compose_prompt` are preserved.
- `scripts/lint-fix-loop.md` documents the log-scoped goal, in-scope list, phase-gated hint, split anti-cascade, extraction filters, and excerpt coupling.
- `scripts/test-lint-fix-loop.sh` adds Cases 12–16 and extends Case 6 while preserving Cases 9–11; `bash scripts/test-lint-fix-loop.sh` passes.
- `bash scripts/test-prompt-template-invariants.sh` (compose_prompt invariants `FIXED:`, `UNFIXABLE:`, `Acceptable final-line shapes`, `## PROHIBITION: Submodules`) and `bash scripts/test-implement-structure.sh` pass.
- `bash scripts/relevant-checks.sh` (or `make lint`) passes on the touched files.
diff_lines: 278

## Test plan
(no test plan section in plan-file)
