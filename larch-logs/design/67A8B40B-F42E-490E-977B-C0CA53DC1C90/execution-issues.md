### External Reviewer Issues

- **Step review Step 2 — codex-review failed (exit 7 — health-probe — auth-retries=1, transient-retries=5)**:
  ```
===== diag =====
health-probe fast-fail: codex unhealthy before launch
probe output: CODEX_BINARY_FOUND=true
CURSOR_BINARY_FOUND=true
CODEX_PRESENT=false
CURSOR_PRESENT=false
CODEX_AVAILABLE=false
CURSOR_AVAILABLE=false
CODEX_PROBE_TIMED_OUT=false
CURSOR_PROBE_TIMED_OUT=false; probe stderr:
  ```

- **Step review Step 2 — codex-review failed (exit 7 — health-probe — auth-retries=1, transient-retries=5)**:
  ```
===== diag =====
health-probe fast-fail: codex unhealthy before launch
probe output: CODEX_BINARY_FOUND=true
CURSOR_BINARY_FOUND=true
CODEX_PRESENT=false
CURSOR_PRESENT=false
CODEX_AVAILABLE=false
CURSOR_AVAILABLE=false
CODEX_PROBE_TIMED_OUT=false
CURSOR_PROBE_TIMED_OUT=false; probe stderr: 
===== launch-stderr =====
health-probe fast-fail: codex unhealthy before launch
health-probe fast-fail: codex unhealthy before launch
health-probe fast-fail: codex unhealthy before launch
health-probe fast-fail: codex unhealthy before launch
health-probe fast-fail: codex unhealthy before launch
  ```

- **Step review Step 2 — codex-review failed (exit 7 — health-probe — auth-retries=1, transient-retries=5)**:
  ```
===== diag =====
health-probe fast-fail: codex unhealthy before launch
probe output: CODEX_BINARY_FOUND=true
CURSOR_BINARY_FOUND=true
CODEX_PRESENT=false
CURSOR_PRESENT=false
CODEX_AVAILABLE=false
CURSOR_AVAILABLE=false
CODEX_PROBE_TIMED_OUT=false
CURSOR_PROBE_TIMED_OUT=false; probe stderr:
  ```

- **Step review Step 2 — codex-review failed (exit 7 — health-probe — auth-retries=1, transient-retries=5)**:
  ```
===== diag =====
health-probe fast-fail: codex unhealthy before launch
probe output: CODEX_BINARY_FOUND=true
CURSOR_BINARY_FOUND=true
CODEX_PRESENT=false
CURSOR_PRESENT=false
CODEX_AVAILABLE=false
CURSOR_AVAILABLE=false
CODEX_PROBE_TIMED_OUT=false
CURSOR_PROBE_TIMED_OUT=false; probe stderr: 
===== launch-stderr =====
health-probe fast-fail: codex unhealthy before launch
health-probe fast-fail: codex unhealthy before launch
health-probe fast-fail: codex unhealthy before launch
health-probe fast-fail: codex unhealthy before launch
health-probe fast-fail: codex unhealthy before launch
  ```

- **Step design Step 3 — collect-agent-results.sh cursor NOT_SUBSTANTIVE failed (exit 0)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/cursor-plan-innovation-output.txt|TOOL=cursor|STATUS=NOT_SUBSTANTIVE|EXIT_CODE=0|FAILURE_REASON=structured records not found after repair

## Reviewer output (<TMPDIR>/cursor-plan-innovation-output.txt)

schema_version	scope	severity	focus_area	location	what	scenario_or_breakage	suggested_fix
1	in_scope	important	completeness	python/upgrade_larch.py:TEST_FILE_CLEANUP_PATTERNS	Harness fixture trees under scripts/ and skills/*/scripts/fixtures/ are not in any cleanup pattern	The issue requires auditing and excluding dev test infrastructure; cone mode still ships scripts/ and skills/, so paths like scripts/fixtures/parse-codex-usage/*.jsonl and skills/design/scripts/fixtures/** remain in the cache after /upgrade-larch	Add recursive fixture globs to cleanup (e.g. scripts/fixtures/** and skills/*/scripts/fixtures/**) or a single confined **/fixtures/** glob; extend unit-test fixtures to assert those files are removed
2	out_of_scope	latent	architecture	.pre-commit-config.yaml:1	[OUT_OF_SCOPE] Root dev CI config ships via cone root files but is absent from cleanup patterns and audit notes	Cone mode always keeps top-level tracked files; .pre-commit-config.yaml is dead weight for clients but not test harness per se	If desired in a follow-up, add .pre-commit-config.yaml and .markdownlint.json to cleanup patterns or document them as accepted cone-root dev residue
3	out_of_scope	nit	code-quality	scripts/lib-sparse-dirs.md:3	[OUT_OF_SCOPE] lib-sparse-dirs.md is not listed in edit-in-sync surfaces while the allowlist comment contract changes	Drift between the sourced allowlist script and its contract doc may confuse maintainers	Add scripts/lib-sparse-dirs.md to the edit-in-sync list in skills/upgrade-larch/SKILL.md and docs/installation-and-setup.md


- **Step review Step 2 — codex-review failed (exit 7 — health-probe — auth-retries=1, transient-retries=5)**:
  ```
===== diag =====
health-probe fast-fail: codex unhealthy before launch
probe output: CODEX_BINARY_FOUND=true
CURSOR_BINARY_FOUND=true
CODEX_PRESENT=false
CURSOR_PRESENT=false
CODEX_AVAILABLE=false
CURSOR_AVAILABLE=false
CODEX_PROBE_TIMED_OUT=false
CURSOR_PROBE_TIMED_OUT=false; probe stderr: 
===== launch-stderr =====
health-probe fast-fail: codex unhealthy before launch
health-probe fast-fail: codex unhealthy before launch
health-probe fast-fail: codex unhealthy before launch
health-probe fast-fail: codex unhealthy before launch
health-probe fast-fail: codex unhealthy before launch
  ```

- **Step design Step 3 — collect-agent-results.sh cursor NOT_SUBSTANTIVE failed (exit 0)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/cursor-plan-innovation-output.txt|TOOL=cursor|STATUS=NOT_SUBSTANTIVE|EXIT_CODE=0|FAILURE_REASON=structured records not found after repair

## Reviewer output (<TMPDIR>/cursor-plan-innovation-output.txt)

schema_version	scope	severity	focus_area	location	what	scenario_or_breakage	suggested_fix
1	in_scope	important	completeness	python/upgrade_larch.py:55-59	[SCOPE-REDUCTION] `tests/` is removed from `LARCH_SPARSE_DIRS` but not from `DEV_TOP_LEVEL_CLEANUP_DIRS`	Older cache installs that still contain a top-level `tests/` directory keep that dead weight after `/upgrade-larch`; the issue goal to keep test infrastructure out of the installed cache is only partially met	Add `"tests"` to `DEV_TOP_LEVEL_CLEANUP_DIRS` and remove it with the same confined direct-child `shutil.rmtree()` path used for `.claude/`, `.github/`, and `.gemini/`
2	in_scope	important	completeness	python/upgrade_larch.py:61-76	[SCOPE-REDUCTION] Cone-mode root dev/CI files are not in cleanup patterns	Git sparse cone mode still ships root files; `agent-lint.toml`, `.pre-commit-config.yaml`, `.agnix.toml`, `.gitleaks.toml`, `.markdownlint.json`, and `.markdownlintignore` remain in the installed cache even after cleanup, despite the issue asking to audit other client-dead-weight files	Add explicit root-level entries to the cleanup pattern tuple (or a small sibling tuple) for those files; keep the existing confinement checks before `unlink()`
3	out_of_scope	nit	code-quality	python/upgrade_larch.py:78-81	`skills/test-issue/` cleanup removes only two files, not the directory	An empty `skills/test-issue/` directory may remain after cleanup	No functional breakage; optionally `rmtree` the whole skill directory as a confined direct-child path if it is ever promoted from file patterns to directory cleanup
4	out_of_scope	latent	architecture	skills/research/references/eval-set.md:1-5	Dev-only `/research` eval catalog and baseline ship under retained `skills/` and are not cleaned	Consumers keep eval-harness markdown/json that only `python/cli.py eval research` uses; dead weight but not test harness in the narrow sense	If the audit should cover all maintainer-only harness artifacts, add explicit cleanup for `skills/research/references/eval-set.md` and `eval-baseline.json`; otherwise file a follow-up issue


- **Step review Step 2 — codex-review failed (exit 7 — health-probe — auth-retries=1, transient-retries=5)**:
  ```
===== diag =====
health-probe fast-fail: codex unhealthy before launch
probe output: CODEX_BINARY_FOUND=true
CURSOR_BINARY_FOUND=true
CODEX_PRESENT=false
CURSOR_PRESENT=false
CODEX_AVAILABLE=false
CURSOR_AVAILABLE=false
CODEX_PROBE_TIMED_OUT=false
CURSOR_PROBE_TIMED_OUT=false; probe stderr:
  ```
### 1. [completeness] `tests/` dropped from sparse cone but not from cache cleanup
**Location:** `python/upgrade_larch.py` (`DEV_TOP_LEVEL_CLEANUP_DIRS`)

The plan and approved outline both remove `tests` from `LARCH_SPARSE_DIRS`, and the docs call that out. Cleanup only targets `.claude/`, `.github/`, and `.gemini/`. Legacy caches that already have a top-level `tests/` tree will keep it after `/upgrade-larch`. That leaves a hole in the stated goal.

**Suggested revision:** Add `"tests"` to `DEV_TOP_LEVEL_CLEANUP_DIRS` and delete it with the same confined direct-child directory checks.

### 2. [completeness] Root dev/CI files still ship via cone mode
**Location:** `python/upgrade_larch.py` (`TEST_FILE_CLEANUP_PATTERNS`)

Sparse checkout cannot drop root files. The plan cleans `Makefile` and `parallel-tests.py`, but not other large dev-only root artifacts: `agent-lint.toml`, `.pre-commit-config.yaml`, `.agnix.toml`, `.gitleaks.toml`, `.markdownlint.json`, `.markdownlintignore`. The issue also asks to audit other client-dead-weight files. Cone installs will still carry these after cleanup.

**Suggested revision:** Add those root paths to the cleanup pattern list. No new machinery is required.

### 3. [OUT_OF_SCOPE] [code-quality] Partial removal of `skills/test-issue/`
**Location:** `python/upgrade_larch.py` (`DEV_ONLY_SKILL_CLEANUP_PATTERNS`)

Only `SKILL.md` and `scripts/test-issue.sh` are removed. Today that is the whole skill, so behavior is fine. An empty directory may remain.

### 4. [OUT_OF_SCOPE] [architecture] Research eval reference files not in scope
**Location:** `skills/research/references/eval-set.md`, `skills/research/references/eval-baseline.json`

These are maintainer eval artifacts, not Python/bash test harnesses. They are outside the plan’s pattern set. Worth a follow-up if the audit should go broader.

**Note on minimum-change:** The plan correctly keeps `python/research_eval.py` and `python/legacy_review_shell/` out of cleanup. Both are runtime dependencies (`collect-agent-results.sh` and `review_pipeline.py`). The confinement helpers before `rmtree()` are proportionate, not scope creep.
## Reviewer stderr (<TMPDIR>/cursor-plan-innovation-output.txt.diag)

(empty: <TMPDIR>/cursor-plan-innovation-output.txt.diag)

## Failed-agent stderr tail (<TMPDIR>/cursor-plan-innovation-output.txt.stderr-tail)

(file missing: <TMPDIR>/cursor-plan-innovation-output.txt.stderr-tail)

## Launcher stderr (<TMPDIR>/cursor-plan-innovation-output.txt.launch-stderr)

⏳ cursor agent: still running (1m elapsed)
⏳ cursor agent: still running (2m elapsed)
⏳ cursor agent: still running (3m elapsed)
✓ cursor agent: completed (exit code 0, output 4701 bytes)
  ```
### Finding 1 (completeness)
**Location:** `python/upgrade_larch.py` (`TEST_FILE_CLEANUP_PATTERNS` and related constants)

The plan’s pattern set covers `python/test_*.py`, `scripts/test-*`, and skill harness scripts, but not harness **fixture** trees. The repo has substantial fixture content under `scripts/fixtures/` and `skills/*/scripts/fixtures/` (for example `scripts/fixtures/parse-codex-usage/` and `skills/design/scripts/fixtures/parse-plan-commands/`). Those paths stay in the installed cache after cleanup because they are not matched by any proposed glob. That leaves a hole in the issue’s explicit “audit for other files of this nature” requirement.

**Suggested revision:** Add confined recursive globs for fixture trees (minimal form: `scripts/fixtures/**` plus `skills/*/scripts/fixtures/**`, or one `**/fixtures/**` under `version_root`). Extend `test_upgrade_larch.py` fixtures to place sample fixture files and assert they are removed.

### Finding 2 [OUT_OF_SCOPE] (architecture)
**Location:** `.pre-commit-config.yaml`

Cone sparse checkout still ships root tracked files. `.pre-commit-config.yaml` (and `.markdownlint.json`) are dev-only CI/lint config, not covered by the plan’s cleanup list or audit notes. Low risk for runtime, but the audit is incomplete for “other files of this nature.” Track as a follow-up only if you want zero dev residue at the repo root.

### Finding 3 [OUT_OF_SCOPE] (code-quality)
**Location:** `scripts/lib-sparse-dirs.md`

The plan updates `scripts/lib-sparse-dirs.sh` comments and multiple edit-in-sync docs, but not `scripts/lib-sparse-dirs.md`, which documents the allowlist contract. Minor maintainer-doc drift; add to the edit-in-sync surface list if you touch nearby install docs anyway.
## Reviewer stderr (<TMPDIR>/cursor-plan-innovation-output.txt.diag)

(empty: <TMPDIR>/cursor-plan-innovation-output.txt.diag)

## Failed-agent stderr tail (<TMPDIR>/cursor-plan-innovation-output.txt.stderr-tail)

(file missing: <TMPDIR>/cursor-plan-innovation-output.txt.stderr-tail)

## Launcher stderr (<TMPDIR>/cursor-plan-innovation-output.txt.launch-stderr)

⏳ cursor agent: still running (1m elapsed)
⏳ cursor agent: still running (2m elapsed)
✓ cursor agent: completed (exit code 0, output 3768 bytes)
  ```
### Warnings

- **Step design Step 3.5 / Gate B — validate-plan-commands(auto-fixed:cursor) failed (exit 0)**:
  ```
DEFECT script=scripts/test-sessionstart-health.sh kind=non-canonical-path
DEFECT script=scripts/relevant-checks.sh kind=non-canonical-path
VALIDATE_STATUS=defects-found	DEFECT_COUNT=2	SKIPPED_COUNT=0	UNSAFE_TOKEN_COUNT=0
  ```
