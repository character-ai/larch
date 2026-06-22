## Goal
Implement issue #4997: [IMPLEMENTING] Add linter enforcing no 2 consecutive Bash() tool calls in skill .md files.

## Implementation Plan
## Plan

## Approach

Implement a small Python linter for source-adjacent `bash` fences in orchestrator-facing skill Markdown.

Use the approved static model:

- Scan only:
  - `skills/*/SKILL.md`
  - `.claude/skills/*/SKILL.md`
  - `skills/*/references/*.md`
- Treat only fenced blocks whose info string starts with `bash` as Bash tool-call candidates.
- Do not treat `sh`, `shell`, `text`, or untyped fences as Bash tool calls.
- Parse Markdown fences with a length-aware fence parser, not regex-only scanning.
- Accept leading whitespace on fence openers and closers (CommonMark 0–3 space indent), matching `python/lint_literal_counts.py` `CODE_FENCE_REGEX` and `scripts/lint-bare-grep-probe.sh`.
- Flag two Bash tool-call fences when the text between them is only:
  - blank lines,
  - HTML comments,
  - or short breadcrumb prose.
- Treat substantive Markdown between fences as an intervening non-Bash step.

Use a conservative helper for breadcrumb prose:

- Strip blank lines and HTML comments.
- Consider the gap adjacent only when the remaining text is short, for example 1 to 2 prose lines and below a small character cap.
- Do not count headings, list items, tables, horizontal rules, or long paragraphs as breadcrumbs.

Add explicit carve-outs:

- WRONG/CORRECT example pairs.
- Foreground recovery probes for `.completed/step-3-terminal`, `.completed/step-5c-terminal`, and `.completed/step-final-summary`.
- Pause/resume boundary pairs that invoke the `/design` launcher wrapper and are intentionally separate.
- Immediate-background / `<task-notification>` boundary pairs that need distinct Bash tool calls.

Add inline suppression with two placement forms:

- **Trailing pragma (preferred for single-line launcher fences):** same-line `# lint-consecutive-bash: ok <reason>` at the end of the Bash fence body line, matching `lint-bare-grep-probe` pragma style. Required for `skills/implement/SKILL.md` new-shape fences because `scripts/test-implement-fence-shape.sh` rejects fences whose sole nonblank line starts with `#` (standalone suppression comment lines fail CI even when consecutive-bash lint would pass).
- **Body comment (multi-line fences):** `# lint-consecutive-bash: ok <reason>` on its own line inside either Bash fence when the fence has multiple nonblank body lines.

Teach the linter to recognize both forms. Require a non-empty reason in either case. Keep error messages actionable and include both fence line numbers.

**First-run green-lint contract (merge gate).** Wire the linter into `make lint` and pre-commit only after the scoped tree is clean. After implementation wiring, run `python3 python/cli.py lint consecutive-bash` once on the full repo. For every reported violation in any in-scope path (`skills/*/SKILL.md`, `.claude/skills/*/SKILL.md`, `skills/*/references/*.md`), resolve it in this PR before merge:

- **Legitimate boundary** (pause/resume, recovery probe, immediate-background wait, WRONG/CORRECT example, or other carve-out gap): add a justified suppression using the appropriate placement form above.
- **Genuine orchestration smell** (logic that should eventually move behind `cli.py`): add a justified inline suppression in this PR with a specific non-empty reason describing the deferred refactor. Do not refactor orchestrator logic here. Filing follow-up GitHub issues is optional operator choice outside this PR; suppressions do not require issue-number citations.

`make lint`, `pre-commit run lint-consecutive-bash --all-files`, and `python3 python/cli.py lint consecutive-bash` must all exit 0 before merge.

**File enumeration.** `lint_common.git_ls_files_z` accepts only one pathspec. Do not assume one call covers three disjoint globs. Mirror `python/lint_codex_exec_auth.py` `_git_files`: one `git ls-files --cached --others --exclude-standard -z --` invocation with multiple pathspec args:

- `skills/*/SKILL.md`
- `skills/*/references/*.md`
- `.claude/skills/*/SKILL.md`

Merge, dedupe, sort deterministically, then apply scope filters (`is_file`, skip symlinks). For non-git fixture roots, fall back to deterministic `Path.glob` over the same three patterns and merge/dedupe/sort the same way.

## Files to modify/create

### NEW: python/lint_consecutive_bash.py

Create the linter.

Implementation shape:

- Define the three scoped glob patterns.
- Reuse `lint_common.run_file_lint`.
- Add `_git_files(root, patterns: list[str])` (or equivalent) that passes all scoped pathspecs in one `git ls-files` call, matching `lint_codex_exec_auth._git_files`.
- Fall back to deterministic per-pattern `Path.glob` for fixture roots outside git; merge, dedupe, sort.
- Parse fences with a length-aware parser accepting leading whitespace on openers and closers (match `lint_literal_counts.CODE_FENCE_REGEX` indent + marker-length close rule).
- Parse fences into small records:
  - `start_line`
  - `end_line`
  - `info`
  - `body`
  - `body_lines` (physical lines with line numbers)
  - `preceding_context` if needed for example detection
- Classify candidate tool-call fences when the normalized info string starts with `bash`.
- Skip example fences when:
  - the info string marks the block as an example, or
  - nearby text or first body comment marks `WRONG` / `CORRECT`.
- Check adjacent candidate pairs.
- Report only when the gap is blank/comment/short breadcrumb and no carve-out or suppression applies.
- Recognize suppressions via:
  - trailing pragma regex on any nonblank body line: `\s# lint-consecutive-bash: ok\s+(\S.*)$` (non-empty capture group required), or
  - standalone body-line comment: `^\s*# lint-consecutive-bash: ok\s+(\S.*)$` on a line that is the sole nonblank body line only when the fence has multiple body lines (never as the only line in a single-line implement launcher fence).
- Emit messages like:
  - `lint-consecutive-bash: path:line: consecutive bash tool-call fences at lines X and Y; combine into one cli.py-backed call or add trailing # lint-consecutive-bash: ok <reason> on single-line launcher fences (or body comment in multi-line fences) for an intentional boundary`

### NEW: python/test_lint_consecutive_bash.py

Add pytest coverage.

Cover:

- Clean single Bash fence.
- Two adjacent Bash fences with only blanks.
- Two adjacent Bash fences with HTML comments only.
- Two adjacent Bash fences with short breadcrumb prose.
- Substantive heading or long prose between fences passes.
- `sh`, `shell`, `text`, and untyped fences do not count.
- WRONG/CORRECT example pair passes.
- Pause/resume launcher boundary passes.
- Foreground recovery probe passes.
- `<task-notification>` / immediate-background boundary passes.
- Indented ` ```bash` opener pair (0–3 leading spaces) is detected and flagged or suppressed correctly.
- Trailing pragma on a single-line launcher fence passes (implement fence-shape compatible).
- Standalone `# lint-consecutive-bash: ok` as sole body line in a single-line fence does not count as valid suppression (documents implement fence-shape constraint).
- Multi-line fence body-comment suppression passes only with a reason.
- Suppression without a reason fails for both placement forms.
- Multiple files report deterministic messages.
- Non-UTF-8 input returns exit 2 through `LintError`.
- Fixture roots outside git enumerate all three scoped patterns (disjoint globs merged deterministically).
- Out-of-scope Markdown files are ignored.
- Git enumeration uses multiple pathspecs in one invocation so `.claude/skills/*` and `skills/*/references/*` are included, not only top-level `skills/*/SKILL.md`.

### UPDATED: python/cli.py

Add the dispatch entry:

- `("lint", "consecutive-bash"): ("lint_consecutive_bash", "main")`

Keep it near the other lint entries.

### UPDATED: .pre-commit-config.yaml

Add a local hook.

Suggested shape:

- `id: lint-consecutive-bash`
- `entry: python3 python/cli.py lint consecutive-bash`
- `language: system`
- `pass_filenames: false`
- `always_run: true`
- `files:` matching the scoped surfaces:
  - `skills/<skill>/SKILL.md`
  - `.claude/skills/<skill>/SKILL.md`
  - `skills/<skill>/references/*.md`

### UPDATED: Makefile

Wire the linter into local lint and harness coverage.

Add:

- `.PHONY` entry for `lint-consecutive-bash`
- `.PHONY` entry for `test-lint-consecutive-bash`
- `lint-consecutive-bash:` target that runs `python3 python/cli.py lint consecutive-bash`
- `test-lint-consecutive-bash:` target that runs `python3 -m pytest python/test_lint_consecutive_bash.py -q` through `python/cli.py timing harness-mark`
- Add `lint-consecutive-bash` to the direct `lint:` prerequisite list.
- Add `test-lint-consecutive-bash` to one existing `test-harnesses-N` shard.

Do not rebalance shards unless the harness is unexpectedly slow.

### UPDATED: docs/linting.md

Document the new lint row.

Include:

- Scope.
- Static source-adjacent definition.
- Indented fence openers (0–3 leading spaces).
- Carve-outs.
- Suppression grammar:
  - trailing `# lint-consecutive-bash: ok <reason>` on the Bash command line (required for single-line `skills/implement/SKILL.md` launcher fences per `test-implement-fence-shape.sh`);
  - body-line comment form for multi-line fences.
- First-run contract: every in-scope violation must pass or carry a justified suppression before merge; follow-up issue filing is optional operator choice, not a merge gate.
- How it runs:
  - `make lint-consecutive-bash`
  - pre-commit hook
  - `make lint`
  - pytest harness.

Add a make-target row for `make test-lint-consecutive-bash`.

### UPDATED: skills/*/SKILL.md, .claude/skills/*/SKILL.md, skills/*/references/*.md (first-run remediation)

**Firm step, not optional.** After wiring, run `python3 python/cli.py lint consecutive-bash` on the full repo. Touch every scoped file that still reports a violation. For each hit, add a minimal justified suppression using the correct placement form (trailing pragma on single-line launcher fences; body comment only in multi-line fences). Expected touch surfaces from the first scan include, but are not limited to:

- `skills/design/SKILL.md`
- `skills/implement/SKILL.md` (use trailing pragmas on single-line launcher fences)
- `skills/research/SKILL.md`
- `.claude/skills/agnix-fix/SKILL.md`
- `.claude/skills/audit-runs/SKILL.md`
- `.claude/skills/combine-issues/SKILL.md`
- `.claude/skills/release/SKILL.md`
- relevant `skills/*/references/*.md` files

Do not refactor orchestration in this PR. Re-run `python3 python/cli.py lint consecutive-bash`, `make lint-consecutive-bash`, and `make lint` to confirm exit 0 before merge.

### MAY_UPDATE: python/README.md

Update only if the local lint surface list is expected to stay complete.

If updated, add `lint_consecutive_bash.py` to the local lint surfaces exposed through `python/cli.py lint`.

### MAY_UPDATE: skills/design/SKILL.md

Only if the first full lint run finds additional adjacent Bash boundaries in this file beyond those covered by the firm remediation step above.

### MAY_UPDATE: skills/implement/SKILL.md

Only if the first full lint run finds additional adjacent Bash boundaries beyond those covered by the firm remediation step above. Prefer trailing pragmas on single-line launcher fences.

### MAY_UPDATE: skills/research/SKILL.md


### MAY_UPDATE: .claude/skills/release/SKILL.md


### MAY_UPDATE: .claude/skills/combine-issues/SKILL.md


## Edge cases

- Handle CRLF and UTF-8 BOM.
- Require closing fences to use at least the opener fence length; match opener indent on close.
- Accept indented ` ```bash` openers (0–3 leading spaces) per `lint_literal_counts` / CommonMark.
- Ignore nested backticks inside non-Bash outer fences.
- Preserve line numbers from original source.
- Skip symlink files.
- Keep non-git fixture enumeration deterministic across three disjoint globs.
- Avoid broad carve-outs that hide real adjacent Bash smells.
- Treat `bash` info strings with trailing attributes as Bash fences.
- Treat `bash` example markers as examples only when explicit.
- Do not leave any scoped violation unresolved at merge; suppressions are the mechanism for deferred smells.
- Single-line implement launcher fences must use trailing pragmas, not standalone comment-only body lines, to stay compatible with `test-implement-fence-shape.sh`.

## Failure modes

- Overbroad carve-outs may hide real smells.
  - Keep carve-outs narrow and covered by tests.
- Too-strict breadcrumb detection may flag intentional step boundaries.
  - Use reasoned suppressions for rare legitimate pairs.
- Too-loose breadcrumb detection may miss adjacent prompts.
  - Test the blank/comment/short-prose cases directly.
- Single-pathspec `git_ls_files_z` may silently skip `.claude/skills/*` or `skills/*/references/*`.
  - Use multi-pathspec enumeration with deterministic merge; cover in pytest.
- Column-0-only fence parsing may miss indented bash blocks in scoped files.
  - Match `lint_literal_counts` indent-aware parser; cover indented pairs in pytest.
- Standalone suppression comments in single-line implement fences may pass consecutive-bash lint but fail fence-shape CI.
  - Document and test trailing-pragma placement; use trailing pragmas in implement remediation.
- Wiring `make lint` before first-run remediation ships a red tree.
  - Run full scan, add suppressions to every failing scoped file, verify green `make lint` before merge.

## Testing strategy

Run focused checks:

- `python3 -m pytest python/test_lint_consecutive_bash.py -q`
- `python3 python/cli.py lint consecutive-bash`
- `pre-commit run lint-consecutive-bash --all-files`
- `make test-lint-consecutive-bash`

Run required repo checks:

- `make lint`
- Because Python files change:
  - `make py-lint`
  - `make py-test`

## Acceptance

- `python3 python/cli.py lint consecutive-bash`, `make lint`, and `pre-commit run lint-consecutive-bash --all-files` all exit 0 on the repository.
- `make lint-consecutive-bash` is a prerequisite of the `lint:` target, and a pre-commit hook runs the linter on the scoped skill `.md` surfaces.
- Carve-outs (WRONG/CORRECT example pairs) and both suppression placement forms are covered by `python/test_lint_consecutive_bash.py`, wired via `make test-lint-consecutive-bash` into a `test-harnesses-N` shard.
- Every in-scope skill `.md` file (`skills/*/SKILL.md`, `.claude/skills/*/SKILL.md`, `skills/*/references/*.md`) passes or carries a justified `# lint-consecutive-bash: ok <reason>` suppression before merge.
- `make py-lint` and `make py-test` pass.
- `docs/linting.md` documents the lint row: scope, source-adjacent definition, carve-outs, and suppression grammar.

diff_lines: 640

## Test plan
(no test plan section in plan-file)
