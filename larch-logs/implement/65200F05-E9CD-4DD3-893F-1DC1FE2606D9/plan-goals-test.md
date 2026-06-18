## Goal
Implement issue #4671: [IMPLEMENTING] [BUG] /implement Step 2 silent plan-file drops; Step 5 panel-failed recurred (#4612).

## Implementation Plan
## Plan

## Approach

Implement both scoped fixes in one PR.

- **Failure 1:** Keep collector status authoritative in `check-reviewer-failure-threshold.sh`.
  - Add a source argument to `count_static_status_once`, for example `collector` vs `raw-output`.
  - Preserve the existing rule that a collector non-success cannot be upgraded by a non-empty raw output file.
  - Change only the raw-output success to failure downgrade path:
    - If the counted status is `OK` or `cap_hit` and the raw-output pass would report `ERROR`, do not change `SUCCEEDED_SLOTS`, `FAILED_SLOTS`, or stored status.
    - Record a loud diagnostic in the threshold output naming the normalized reviewer output base.
  - Keep genuine failures intact:
    - Collector non-`OK` and non-`cap_hit` statuses still count as failures.
    - `NOT_SUBSTANTIVE` still increments `NOT_SUBSTANTIVE_SLOTS`.
    - Dropped slots still count as failures.
    - Never-launched slots still count as failures.

- **Failure 2:** Add a warn-only plan-file coverage check in the external `status=complete` dispatcher path.
  - Run it after manifest validation and before `git add -A && git commit`.
  - Use the actual working-tree delta as the touched-path source:
    - tracked paths from `git diff --name-only HEAD`
    - untracked paths from `git ls-files --others --exclude-standard`
  - **Do not use `_git_stdout` for touched-path collection.** `_git_stdout` returns `""` on any non-zero exit with no failure signal; routing coverage through it would treat every explicit plan path as uncovered and emit false `WARN_PLAN_FILES_UNTOUCHED` warnings.
  - Parse plan scope with the shared plan grammar, but **never treat the design-SKILL fallback as plan contract**.
  - Run the gate **only when at least one explicit `### NEW:` / `### UPDATED:` / `### REWRITTEN:` path was parsed** from the plan text.
  - When zero explicit scope paths parse (missing section, prose-only Files section, scope-less `## Plan` stub, etc.), skip coverage entirely: no uncovered paths, no warning KVs, no execution-issues entry.
  - When explicit scope paths exist, compare that set against actual touched paths, not manifest self-report.
  - If any explicit plan-listed files are untouched:
    - Append a `Warnings` entry to `$IMPLEMENT_TMPDIR/execution-issues.md`.
    - Emit trailing advisory KVs on the `STATUS=complete` envelope, for example `WARN_PLAN_FILES_UNTOUCHED=true` and `WARN_PLAN_FILES_UNTOUCHED_COUNT=<N>`.
    - Still commit.
  - If either git probe fails:
    - Append a `Warnings` entry naming the failing command.
    - Skip plan-file coverage KVs entirely.
    - **Also skip** the existing undeclared-manifest path diagnostic at the same site (refactor that block to reuse `touched` when non-`None`; when `touched is None`, do not emit false undeclared-path warnings from empty `_git_stdout`-style behavior).
    - Still commit.
  - If plan-file read fails during coverage (missing after earlier validation, permission error, I/O error, etc.):
    - Wrap the read in `try`/`except` inside `_plan_coverage_uncovered_paths` (or a small helper it calls).
    - Use `read_text(encoding="utf-8", errors="replace")` so decode issues do not escape as `UnicodeDecodeError`.
    - On `OSError` (and any other read failure the helper chooses to catch at that boundary): append a `Warnings` entry naming `st.plan_file` and the exception; return the same failure sentinel as git-probe failure (`None`); skip `WARN_PLAN_FILES_UNTOUCHED` KVs; still commit.
    - Do not let an uncaught read exception abort dispatch after manifest validation.

- **API fix (blocking reviewer finding):** Do not use `extract_scope_paths(plan_text, default=None)` for the coverage gate. In Python, an omitted `default` and an explicit `default=None` are the same binding, so that shape cannot distinguish "CLI fallback" from "return empty when no explicit headings." Use a tri-state keyword instead: add `*, use_fallback: bool = True` to `extract_scope_paths`. When `use_fallback=False`, return `seen` as-is (including `[]`). Keep all existing no-kwarg callers (`plan_scope_paths_main`, `dirty_tree.py`) on the default `use_fallback=True` path so `skills/design/SKILL.md` fallback behavior is unchanged.

## Files to modify/create

### UPDATED: `python/legacy_review_shell/check-reviewer-failure-threshold.sh`

- Extend `count_static_status_once` to accept a source label.
- Pass `collector` for records parsed from `COLLECTOR_RESULTS_FILE`.
- Pass `raw-output` for records derived from `--reviewer-output-files`.
- In the `old_status` success plus new raw-output non-success branch:
  - Do not demote.
  - Append the normalized reviewer base to a diagnostic accumulator.
- Emit stable diagnostic KVs at the end, such as:
  - `RAW_OUTPUT_DOWNGRADE_SUPPRESSED_SLOTS=<N>`
  - `RAW_OUTPUT_DOWNGRADE_SUPPRESSED_REVIEWERS=<comma-or-space-safe-list>`
- Keep the existing counters unchanged for suppressed raw-output demotions.

### UPDATED: `python/test_review_pipeline.py`

Add coverage for the recurrence:

- Collector says `STATUS=OK`.
- Raw output file is empty or contains `NOT_SUBSTANTIVE`, so the raw-output pass would currently mark it `ERROR`.
- Assert:
  - `SUCCEEDED_SLOTS=1`
  - `FAILED_SLOTS=0`
  - `THRESHOLD_OK=true`
  - the new suppressed-downgrade diagnostic names the reviewer.
- Keep the existing `NOT_SUBSTANTIVE` preservation test unchanged, or adjust only for the new source argument behavior.

### UPDATED: `python/issue_wire.py`

- Add a module-level design-SKILL fallback constant, for example `_SCOPE_PATH_FALLBACK = ["skills/design/SKILL.md"]`.
- Change `extract_scope_paths` signature to `extract_scope_paths(plan_text: str, *, use_fallback: bool = True) -> list[str]`.
- Keep the existing heading parser and `seen` accumulation unchanged.
- Replace `return seen or ["skills/design/SKILL.md"]` with:
  - `return seen` when `seen` is non-empty.
  - `return list(_SCOPE_PATH_FALLBACK)` when `seen` is empty and `use_fallback=True`.
  - `return []` when `seen` is empty and `use_fallback=False`.
- Leave `plan_scope_paths_main` calling `extract_scope_paths(...)` with no keyword override so CLI `plan scope-paths` behavior is unchanged.

### UPDATED: `python/test_issue_wire.py`

- Add a direct-parser case: `extract_scope_paths("## Files to modify/create\n\n## Acceptance\n", use_fallback=False) == []`.
- Keep the existing empty-section CLI test that still emits `skills/design/SKILL.md` via the default CLI path (`plan_scope_paths_main` with no `use_fallback` override).
- Optionally add one assertion that `extract_scope_paths(...)` with default kwargs still returns `["skills/design/SKILL.md"]` for the same empty-section fixture, documenting the CLI vs explicit-scope split.

### UPDATED: `python/implement_dispatch.py`

- Import `issue_wire`.
- Add a helper, for example `_working_tree_touched_paths(repo_root: Path) -> set[str] | None`, that:
  - invokes `_git(repo_root, "diff", "--name-only", "HEAD")` and `_git(repo_root, "ls-files", "--others", "--exclude-standard")` directly (or `subprocess.run` with the same argv)
  - checks `returncode` for **each** command independently
  - on success, returns the union of non-empty line sets from both stdout captures
  - on **any** non-zero exit, returns `None` (failure sentinel); do **not** call `_git_stdout` and do **not** treat empty stdout as an empty touched set
- Add a helper, for example `_explicit_plan_scope_paths(plan_text: str) -> list[str]`, that calls `issue_wire.extract_scope_paths(plan_text, use_fallback=False)` and returns the list as-is (empty when no `### NEW|UPDATED|REWRITTEN:` headings parsed). This helper operates on already-read text only; it does not perform I/O.
- Add a helper, for example `_plan_coverage_uncovered_paths(st, touched: set[str] | None) -> list[str] | None`, that:
  - returns `None` immediately when `touched is None` (git probe failed upstream; caller must not emit coverage KVs)
  - reads `st.plan_file` inside `try`/`except OSError`:
    - use `Path(st.plan_file).read_text(encoding="utf-8", errors="replace")`
    - on `OSError`, call `_append_warning(st, ...)` with the plan path and exception message, then return `None` (coverage skipped; no KVs)
  - obtains explicit scope paths via `_explicit_plan_scope_paths(plan_text)`
  - returns `[]` immediately when that set is empty (no declared file scope)
  - otherwise returns sorted explicit plan paths absent from `touched`
- In the external `status == "complete"` path, before `git add -A`:
  - compute `touched = _working_tree_touched_paths(repo_root)` once
  - when `touched is None`: append a `Warnings` entry to `execution-issues.md` naming the failed git probe(s); skip plan-file coverage KVs; **also skip** the existing undeclared-manifest path diagnostic that currently uses `_git_stdout` at lines 1003–1008 (refactor that block to reuse `touched` when non-`None`, so a git failure does not emit a false undeclared-path warning either)
  - when `touched is not None`: reuse `touched` for the existing undeclared-manifest warning (compare against manifest `files_touched` / `tests_added_or_modified`; append warning only when undeclared working-tree paths exist)
  - compute `uncovered = _plan_coverage_uncovered_paths(st, touched)`:
    - when `uncovered is None` (git failure already handled, or plan read failure handled inside the helper): skip `WARN_PLAN_FILES_UNTOUCHED` KVs; still commit
    - when `uncovered` is a non-empty list: append a warning to `execution-issues.md` listing the paths
  - keep the commit flow unchanged in all branches
- Store the uncovered count in a local variable and emit `WARN_PLAN_FILES_UNTOUCHED=true` / `WARN_PLAN_FILES_UNTOUCHED_COUNT=<N>` advisory KVs only on `STATUS=complete` when `uncovered` is a non-empty list (never when `uncovered is None`).

### UPDATED: `python/test_implement_dispatch.py`

Add tests for the warn-only gate using **canonical plan grammar**:

- **Untouched plan file warning:**
  - Write a plan with:
    ```
    ## Files to modify/create
    ### UPDATED: `README.md`
    ### UPDATED: `docs/expected.md`
    ```
  - Fake the external launcher so it edits only `README.md` and writes a valid complete manifest.
  - Assert:
    - dispatcher returns 0
    - `STATUS=complete`
    - commit is created
    - stdout includes `WARN_PLAN_FILES_UNTOUCHED=true`
    - stdout includes `WARN_PLAN_FILES_UNTOUCHED_COUNT=1`
    - `execution-issues.md` lists `docs/expected.md`
- **No warning when all plan files touched:**
  - Plan uses `### UPDATED: `README.md`` for the edited file.
  - Assert no `WARN_PLAN_FILES_UNTOUCHED` KV and no matching warning entry.
- **No warning when plan has no explicit scope paths:**
  - Reuse a scope-less fixture such as `## Plan\n` only, or a `## Files to modify/create` section with prose but no `### NEW|UPDATED|REWRITTEN:` headings.
  - Assert dispatcher still returns `STATUS=complete`, commit succeeds, and there is no `WARN_PLAN_FILES_UNTOUCHED` KV and no spurious `skills/design/SKILL.md` warning.
- **No false coverage warning when git probe fails (regression guard for undeclared-manifest suppression):**
  - Mirror `test_step2_dispatch_undeclared_path_warning`: fake launcher writes both a declared manifest path (`README.md`) and an undeclared working-tree file (`undeclared.txt`) not listed in `files_touched` / `tests_added_or_modified`.
  - Use a plan with explicit scope paths (for example `### UPDATED: `README.md`` and `### UPDATED: `docs/expected.md``) where the implementer touches only `README.md` (would otherwise trigger plan-coverage warning when git probes succeed).
  - Monkeypatch `_git` (or the subprocess layer used by `_working_tree_touched_paths`) so `git diff --name-only HEAD` returns non-zero.
  - Assert:
    - dispatcher still returns `STATUS=complete` and commit succeeds
    - stdout has **no** `WARN_PLAN_FILES_UNTOUCHED` KV
    - `execution-issues.md` contains a `Warnings` entry about the git probe failure
    - `execution-issues.md` does **not** list plan paths such as `docs/expected.md` as uncovered
    - `execution-issues.md` does **not** contain `not declared in manifest files_touched/tests_added_or_modified`
    - `execution-issues.md` does **not** list working-tree paths such as `undeclared.txt` as undeclared (prevents shipping a regression where failed `_git_stdout`-style collection still emits the false undeclared-manifest diagnostic)
- **No coverage KV when plan read fails during coverage:**
  - Use a plan fixture with explicit scope paths and an implementer that touches only a subset (would otherwise warn).
  - Monkeypatch `Path.read_text` on `st.plan_file` (or the plan path object used by `_plan_coverage_uncovered_paths`) to raise `OSError`.
  - Assert:
    - dispatcher still returns `STATUS=complete` and commit succeeds
    - stdout has **no** `WARN_PLAN_FILES_UNTOUCHED` KV
    - `execution-issues.md` contains a `Warnings` entry about plan-file read failure
    - `execution-issues.md` does **not** list plan paths as uncovered
- Do not add coverage for `claude_fallback`; it is out of scope.

### UPDATED: `skills/implement/references/step2-dispatch.md`

Update the Step 2 dispatcher contract:

- Add the new optional advisory KVs to the stdout grammar.
- Document that the coverage gate is warn-only.
- State that it compares **explicit** plan-listed files from `### NEW:` / `### UPDATED:` / `### REWRITTEN:` headings against actual working-tree touched paths before the dispatcher commit.
- Document the skip rule: when zero explicit scope paths parse, the gate does not run and must not treat the `extract_scope_paths` design-SKILL fallback as scope (coverage uses `use_fallback=False`; CLI `plan scope-paths` keeps the fallback).
- Document the git-probe failure rule: touched-path collection uses explicit return-code checks (not `_git_stdout`); on probe failure the dispatcher appends a `Warnings` execution-issues entry, skips `WARN_PLAN_FILES_UNTOUCHED` KVs, **skips the undeclared-manifest touched-path diagnostic**, and still commits.
- Document the plan-read failure rule: if `st.plan_file` cannot be read during coverage, the dispatcher appends a `Warnings` execution-issues entry, skips `WARN_PLAN_FILES_UNTOUCHED` KVs, and still commits (same non-gating posture as git-probe failure).
- Replace the stale sentence that says there is no longer a committed-diff cross-check with the new narrower truth:
  - no fail-closed manifest path equality gate
  - yes warn-only explicit plan-file coverage diagnostic when the plan declares file scope
  - yes existing warn-only undeclared-manifest diagnostic when git probes succeed and working-tree paths are absent from manifest declarations

### UPDATED: `skills/implement/SKILL.md`

Update Step 2 parser prose:

- Mention the new optional `WARN_PLAN_FILES_UNTOUCHED=true` and count KV.
- State that it is advisory, applies only when the plan declares explicit file-scope headings, and never gates §2.1.5.
- Note that git probe failure suppresses coverage KVs (warn-only execution-issues entry instead) and also suppresses the undeclared-manifest touched-path diagnostic at the same site.
- Note that plan-file read failure during coverage suppresses coverage KVs the same way.
- Keep the envelope authority invariant unchanged.

## Edge cases

- **Plan with no explicit file-scope headings:** `_explicit_plan_scope_paths` uses `use_fallback=False`; coverage skips; no spurious warnings for `skills/design/SKILL.md`.
- **Plan-listed file legitimately unchanged:** when the file is explicitly listed under `### NEW|UPDATED|REWRITTEN:`, warn only; review remains the backstop.
- **Manifest lies about touched paths:** coverage uses git state, not manifest state.
- **Untracked files:** include them in touched paths when git probes succeed.
- **Deleted tracked files:** include them through `git diff --name-only HEAD` when the probe succeeds.
- **Raw-output file empty after collector `OK`:** suppress the demotion and emit the diagnostic.
- **Collector reports `ERROR` first:** still counts as a failed slot.
- **`default=None` trap:** never pass `default=None` to mean "no fallback"; use `use_fallback=False` explicitly.
- **Git probe failure:** `_working_tree_touched_paths` returns `None`; no `WARN_PLAN_FILES_UNTOUCHED` KVs; no false uncovered-path warnings; undeclared-manifest diagnostic at the same site is also skipped (even when undeclared working-tree files exist).
- **Plan read failure during coverage:** `_plan_coverage_uncovered_paths` returns `None` after appending a `Warnings` entry; no `WARN_PLAN_FILES_UNTOUCHED` KVs; dispatch still reaches `STATUS=complete` and commits.

## Failure modes

- If `st.plan_file` read fails during coverage checking, catch `OSError` at the coverage boundary, append a `Warnings` execution-issues entry naming the path and error, return `None` from `_plan_coverage_uncovered_paths`, skip `WARN_PLAN_FILES_UNTOUCHED` KVs, and still commit. Do not propagate the exception past manifest validation.
- If `git diff --name-only HEAD` or `git ls-files --others --exclude-standard` fails, append a `Warnings` execution-issues entry naming the failing command, return `None` from `_working_tree_touched_paths`, skip plan-file coverage KVs and the undeclared-manifest touched-path diagnostic, and still commit. Never infer an empty touched set from `_git_stdout`-style silent failure (which would falsely flag every explicit plan path as uncovered and every working-tree path as undeclared).
- If the suppressed downgrade reviewer list risks unsafe characters, emit normalized basenames only.
- If explicit scope parsing yields an empty set, treat that as "no declared file scope" and skip coverage rather than falling back to `skills/design/SKILL.md`.

## Testing strategy

Run focused tests first:

```bash
make test-check-reviewer-failure-threshold
make test-step2-dispatch
```

Then run required Python and repo checks:

```bash
make py-lint
make py-test
make lint
```

## Acceptance

- `check-reviewer-failure-threshold.sh` keeps collector status authoritative: when a slot's collector `STATUS` is `OK` (or `cap_hit`) and the raw `--reviewer-output-files` pass would report `ERROR`, the slot stays in `SUCCEEDED_SLOTS`, `THRESHOLD_OK` stays `true`, and a `RAW_OUTPUT_DOWNGRADE_SUPPRESSED_SLOTS` / `RAW_OUTPUT_DOWNGRADE_SUPPRESSED_REVIEWERS` diagnostic names the suppressed slot.
- Genuine reviewer failures still trip the threshold: collector statuses other than `OK`/`cap_hit`, `NOT_SUBSTANTIVE` (still counted in `NOT_SUBSTANTIVE_SLOTS`), dropped static slots, and never-launched slots all continue to count as failures.
- `extract_scope_paths(plan_text, use_fallback=False)` returns `[]` for a plan with no `### NEW:` / `### UPDATED:` / `### REWRITTEN:` headings; no-keyword callers (`plan_scope_paths_main` and CLI `plan scope-paths`) still return `["skills/design/SKILL.md"]`.
- On external `status=complete`, the Step 2 dispatcher emits `WARN_PLAN_FILES_UNTOUCHED=true` and `WARN_PLAN_FILES_UNTOUCHED_COUNT=<N>` plus an `execution-issues.md` `Warnings` entry listing the untouched explicit plan files, and still commits.
- The coverage gate skips with no KV and no warning when the plan declares no explicit scope paths. On git-probe failure or plan-file read failure it appends a `Warnings` entry, skips the coverage KVs, also skips the undeclared-manifest touched-path diagnostic at that site, and still commits.
- `make test-check-reviewer-failure-threshold`, `make test-step2-dispatch`, `make py-lint`, `make py-test`, and `make lint` all pass; new tests cover the suppressed downgrade, the warn-only coverage hit, the no-explicit-scope skip, the git-probe-failure suppression, and the plan-read-failure suppression.

diff_lines: 252

## Test plan
(no test plan section in plan-file)
