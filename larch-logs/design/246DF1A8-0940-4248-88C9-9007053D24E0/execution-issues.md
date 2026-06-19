### External Reviewer Issues

- **Step review Step 2 — cursor-review failed (exit 1 — unknown — auth-retries=1, transient-retries=1)**:
  ```
===== diag =====
[31m✗ Failed to reach the Cursor API. If you are behind a corporate proxy, set the HTTPS_PROXY environment variable.[0m
Failed with exit code 1. Output size: 0 bytes.
===== launch-stderr =====
❌ cursor agent: FAILED (exit code 1, output 0 bytes)

===== additional failure diagnostics =====
===== diag =====
[31m✗ Failed to reach the Cursor API. If you are behind a corporate proxy, set the HTTPS_PROXY environment variable.[0m
Failed with exit code 1. Output size: 0 bytes.
===== launch-stderr =====
❌ cursor agent: FAILED (exit code 1, output 0 bytes)
  ```

- **Step review Step 2 — cursor-review failed (exit 1 — unknown — auth-retries=1, transient-retries=1)**:
  ```
===== diag =====
[31m✗ Failed to reach the Cursor API. If you are behind a corporate proxy, set the HTTPS_PROXY environment variable.[0m
Failed with exit code 1. Output size: 0 bytes.
===== launch-stderr =====
❌ cursor agent: FAILED (exit code 1, output 0 bytes)

===== additional failure diagnostics =====
===== diag =====
[31m✗ Failed to reach the Cursor API. If you are behind a corporate proxy, set the HTTPS_PROXY environment variable.[0m
Failed with exit code 1. Output size: 0 bytes.
===== launch-stderr =====
❌ cursor agent: FAILED (exit code 1, output 0 bytes)
  ```

- **Step review Step 2 — cursor-review failed (exit 1 — unknown — auth-retries=1, transient-retries=1)**:
  ```
===== diag =====
[31m✗ Failed to reach the Cursor API. If you are behind a corporate proxy, set the HTTPS_PROXY environment variable.[0m
Failed with exit code 1. Output size: 0 bytes.
===== launch-stderr =====
❌ cursor agent: FAILED (exit code 1, output 0 bytes)

===== additional failure diagnostics =====
===== diag =====
[31m✗ Failed to reach the Cursor API. If you are behind a corporate proxy, set the HTTPS_PROXY environment variable.[0m
Failed with exit code 1. Output size: 0 bytes.
===== launch-stderr =====
❌ cursor agent: FAILED (exit code 1, output 0 bytes)
  ```

- **Step review Step 2 — cursor-review failed (exit 1 — unknown — auth-retries=1, transient-retries=1)**:
  ```
===== diag =====
[31m✗ Failed to reach the Cursor API. If you are behind a corporate proxy, set the HTTPS_PROXY environment variable.[0m
Failed with exit code 1. Output size: 0 bytes.
===== launch-stderr =====
❌ cursor agent: FAILED (exit code 1, output 0 bytes)

===== additional failure diagnostics =====
===== diag =====
[31m✗ Failed to reach the Cursor API. If you are behind a corporate proxy, set the HTTPS_PROXY environment variable.[0m
Failed with exit code 1. Output size: 0 bytes.
===== launch-stderr =====
❌ cursor agent: FAILED (exit code 1, output 0 bytes)
  ```

- **Step review Step 2 — cursor-review failed (exit 1 — unknown — auth-retries=1, transient-retries=1)**:
  ```
===== diag =====
Error: [unavailable]
Failed with exit code 1. Output size: 0 bytes.
===== launch-stderr =====
❌ cursor agent: FAILED (exit code 1, output 0 bytes)

===== additional failure diagnostics =====
===== diag =====
Error: [unavailable]
Failed with exit code 1. Output size: 0 bytes.
===== launch-stderr =====
❌ cursor agent: FAILED (exit code 1, output 0 bytes)
  ```

- **Step review Step 2 — cursor-review failed (exit 1 — unknown — auth-retries=1, transient-retries=1)**:
  ```
===== diag =====
Cannot use this model: composer-2.5. Available models: 
Failed with exit code 1. Output size: 0 bytes.
===== launch-stderr =====
❌ cursor agent: FAILED (exit code 1, output 0 bytes)

===== additional failure diagnostics =====
===== diag =====
Cannot use this model: composer-2.5. Available models: 
Failed with exit code 1. Output size: 0 bytes.
===== launch-stderr =====
❌ cursor agent: FAILED (exit code 1, output 0 bytes)
  ```

- **Step design Step 3 — collect-results codex NOT_SUBSTANTIVE failed (exit 0)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/plan-review/round-1/dyn-cursor-plan-parity-auditor-phase2.txt|TOOL=codex|STATUS=NOT_SUBSTANTIVE|EXIT_CODE=0|FAILURE_REASON=structured records not found after repair

## Reviewer output (<TMPDIR>/plan-review/round-1/dyn-cursor-plan-parity-auditor-phase2.txt)


- **Step design Step 3 — collect-results codex NOT_SUBSTANTIVE failed (exit 0)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/plan-review/round-1/dyn-codex-plan-parity-auditor.txt|TOOL=codex|STATUS=NOT_SUBSTANTIVE|EXIT_CODE=0|FAILURE_REASON=structured records not found after repair

## Reviewer output (<TMPDIR>/plan-review/round-1/dyn-codex-plan-parity-auditor.txt)

Found 5 in-scope issues.


- **Step design Step 3 — collect-results codex NOT_SUBSTANTIVE failed (exit 0)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/plan-review/round-1/dyn-cursor-plan-consumer-sweeper-phase2.txt|TOOL=codex|STATUS=NOT_SUBSTANTIVE|EXIT_CODE=0|FAILURE_REASON=structured records not found after repair

## Reviewer output (<TMPDIR>/plan-review/round-1/dyn-cursor-plan-consumer-sweeper-phase2.txt)

**Findings found.**

1. **Important: final stale-name sweep omits `python/agents.py`.**
   - **Plan:** `larch-logs/design/F2F3E671-BDC6-48CD-8951-6672718B72E5/plan.txt:566-567`
   - **Evidence:** `python/agents.py:270-296`
   - **Issue:** The plan’s final grep excludes `python/agents.py`, but that module still contains deleted helper names in docstrings: `lib-external-launcher-common.sh`.
   - **Fix:** Add `python/agents.py` to the final grep scope. Reword those docstrings to name the Python authority, not the deleted shell helper.

2. **Minor: docs plan reintroduces a deleted harness target name.**
   - **Plan:** `larch-logs/design/F2F3E671-BDC6-48CD-8951-6672718B72E5/plan.txt:340-345`
   - **Issue:** The planned `docs/linting.md` prose says to mention former `test-lib-external-launcher-common`. That keeps a deleted helper target in consumer docs.
   - **Fix:** Say `python/test_agents.py` owns external-launcher classify/startup-lock coverage. Do not name the retired target.

3. **Minor: `agent-lint.toml` still has a stale deleted target comment.**
   - **File:** `agent-lint.toml:595-599`
   - **Issue:** The allowlist comment still says `test-lib-cursor-auth target`, but that target is deleted. `make lint-retired-scripts` passes because it does not catch this bare target form.
   - **Fix:** Remove the stale sentence or retarget it to the surviving Python/Makefile coverage.

4. **Minor: manifest append step is stale against the current tree.**
   - **Plan:** `larch-logs/design/F2F3E671-BDC6-48CD-8951-6672718B72E5/plan.txt:303-308`
   - **Current manifest:** `python/migrated-scripts.tsv:1102-1129`
   - **Issue:** The plan says to append the deleted paths with `#4639`, but those exact paths are already present with `#3692`.
   - **Fix:** Change the plan to verify existing rows, not append duplicates.

**`lib-phantom-probe.sh` verification.**

- **Kept:** `scripts/lib-phantom-probe.sh:1-12`
- **Sourced by wrappers:** `scripts/rebase-checkpoint-probe.sh:6-10`, `scripts/phantom-probe-with-warn.sh:6-10`
- **Sourced by survivor implement script:** `skills/implement/scripts/step-2-post-dispatch.sh:24-30`
- **Documented as shared runtime surface:** `skills/implement/references/phantom-probe.md:9-14`
- **Allowlisted correctly:** `agent-lint.toml:487-493`
- **Not retired:** no `lib-phantom-probe` entry in `python/migrated-scripts.tsv`.

**Checks run.**

- `make lint-retired-scripts` passed: `LINT_STATUS=ok`, `RETIRED_REFS=0`.
## Reviewer stderr (<TMPDIR>/plan-review/round-1/dyn-cursor-plan-consumer-sweeper-phase2.txt.diag)

(file missing: <TMPDIR>/plan-review/round-1/dyn-cursor-plan-consumer-sweeper-phase2.txt.diag)

## Failed-agent stderr tail (<TMPDIR>/plan-review/round-1/dyn-cursor-plan-consumer-sweeper-phase2.txt.stderr-tail)

(file missing: <TMPDIR>/plan-review/round-1/dyn-cursor-plan-consumer-sweeper-phase2.txt.stderr-tail)

## Launcher stderr (<TMPDIR>/plan-review/round-1/dyn-cursor-plan-consumer-sweeper-phase2.txt.launch-stderr)

⏳ codex agent: still running (1m elapsed)
⏳ codex agent: still running (2m elapsed)
⏳ codex agent: still running (3m elapsed)
⏳ codex agent: still running (4m elapsed)
⏳ codex agent: still running (5m elapsed)
✓ codex agent: completed (exit code 0, output 2459 bytes)
  ```

- **Step design Step 3 — collect-results codex NOT_SUBSTANTIVE failed (exit 0)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/plan-review/round-1/dyn-codex-plan-consumer-sweeper.txt|TOOL=codex|STATUS=NOT_SUBSTANTIVE|EXIT_CODE=0|FAILURE_REASON=structured records not found after repair

## Reviewer output (<TMPDIR>/plan-review/round-1/dyn-codex-plan-consumer-sweeper.txt)


- **Step design Step 3 — collect-results codex NOT_SUBSTANTIVE failed (exit 0)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/plan-review/round-1/dyn-cursor-plan-coverage-guardian-phase2.txt|TOOL=codex|STATUS=NOT_SUBSTANTIVE|EXIT_CODE=0|FAILURE_REASON=structured records not found after repair

## Reviewer output (<TMPDIR>/plan-review/round-1/dyn-cursor-plan-coverage-guardian-phase2.txt)

**Coverage gaps found:** 6 harness behaviors lack equivalent pytest coverage.

**Findings**

- **[P1] Git commit pathspec scoping is not equivalently tested.**
  - **Deleted behavior:** `scripts/test-git-commit-only.sh:27-56` proves `--only --pathspec-from-file --pathspec-file-nul` commits only recovery paths, handles spaces, and leaves unrelated staged content staged.
  - **Replacement gap:** `python/test_implement_dispatch.py:763-787` only checks argv forwarding. `python/test_git.py:184-202` only checks a generic commit argv.
  - **Risk:** A regression could sweep unrelated staged changes into recovery commits.

- **[P2] Push retry stderr dedupe is only partially tested.**
  - **Deleted behavior:** `scripts/test-git-push.sh:59-72` checks final exit-code passthrough. `scripts/test-git-push.sh:74-114` checks repeated stderr emits once plus `(repeated 3 times)`.
  - **Replacement gap:** `python/test_push.py:178-185` checks only the repeat annotation. It does not assert the stderr block appears exactly once. `python/test_push.py:109-122` checks sleeps and attempts, not stderr or non-1 exit passthrough.
  - **Risk:** The CLI could drop or duplicate the real push diagnostic.

- **[P1] Clean-tree fail-open versus fail-closed coverage is incomplete.**
  - **Deleted behavior:** `scripts/test-check-clean-tree.sh:88-128` covers clean, dirty default, dirty fail-closed, default probe failure fail-open, fail-closed probe failure, tab sanitization, stderr diagnostic, and bad args.
  - **Replacement gap:** `python/test_git.py:701-707` covers only `--fail-closed` probe failure.
  - **Risk:** Default fail-open behavior or dirty-tree reporting could regress silently. Implementation surface is `python/git.py:888-906` and CLI emission is `python/git.py:1215-1227`.

- **[P1] Main-sync reset safety is not equivalently covered.**
  - **Deleted behavior:** `scripts/test-check-main-sync.sh:106-195` covers flush-only auto-reset, non-log block, mixed commits block, missing `origin/main` probe-error, and dirty-tree reset refusal.
  - **Replacement gap:** I found no pytest for `git.check_main_sync` or `git.check_main_sync_main`. Existing admission tests stub the script result, for example `python/test_admission.py:32-57`.
  - **Risk:** A destructive reset could become too permissive. The safety logic lives at `python/git.py:962-1006`.

- **[P2] Phantom status mapping loses several end-to-end cases.**
  - **Deleted behavior:** `scripts/test-check-phantom-dirty.sh:61-138` covers `clean`, `phantom`, missing baseline `unknown`, `tracked-only`, empty baseline, spaced path preservation, failed capture, and bad step tokens.
  - **Replacement gap:** `python/test_phantom.py:12-43` covers only phantom copy shape. `python/test_phantom.py:46-65` covers detector failure. `python/test_git.py:710-738` covers clean CLI and parse error. It does not cover `tracked-only`, bad-step CLI, missing-baseline propagation, or spaced path preservation through `check_phantom_dirty`.
  - **Risk:** The status contract in `python/phantom.py:83-127` can drift.

- **[P2] Check-remote-branch trichotomy has no direct pytest.**
  - **Expected behavior:** `scripts/check-remote-branch.sh:9-21` requires distinct `present`, `absent`, and `error` states.
  - **Replacement gap:** `python/git.py:1015-1042` implements the trichotomy and `python/git.py:1272-1287` emits it, but grep found no direct pytest for `remote_branch_state` or `check_remote_branch_main`.
  - **Risk:** Transport failures could be mistaken for absent branches, recreating the stale-remote failure mode.
## Reviewer stderr (<TMPDIR>/plan-review/round-1/dyn-cursor-plan-coverage-guardian-phase2.txt.diag)

(file missing: <TMPDIR>/plan-review/round-1/dyn-cursor-plan-coverage-guardian-phase2.txt.diag)

## Failed-agent stderr tail (<TMPDIR>/plan-review/round-1/dyn-cursor-plan-coverage-guardian-phase2.txt.stderr-tail)

(file missing: <TMPDIR>/plan-review/round-1/dyn-cursor-plan-coverage-guardian-phase2.txt.stderr-tail)

## Launcher stderr (<TMPDIR>/plan-review/round-1/dyn-cursor-plan-coverage-guardian-phase2.txt.launch-stderr)

⏳ codex agent: still running (1m elapsed)
⏳ codex agent: still running (2m elapsed)
⏳ codex agent: still running (3m elapsed)
⏳ codex agent: still running (4m elapsed)
✓ codex agent: completed (exit code 0, output 3564 bytes)
  ```

- **Step design Step 3 — collect-results codex NOT_SUBSTANTIVE failed (exit 0)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/plan-review/round-1/dyn-codex-plan-coverage-guardian.txt|TOOL=codex|STATUS=NOT_SUBSTANTIVE|EXIT_CODE=0|FAILURE_REASON=structured records not found after repair

## Reviewer output (<TMPDIR>/plan-review/round-1/dyn-codex-plan-coverage-guardian.txt)

Found **6 coverage gaps** that would lose bash-harness behavior if those harnesses are deleted.

## Findings

### FINDING-1: **git commit pathspec scoping is only argv-tested**
- **Deleted behavior:** `scripts/test-git-commit-only.sh:27-55` runs the real helper, commits NUL pathspecs with spaces, excludes unrelated staged `staged.txt`, and verifies that `staged.txt` remains staged.
- **Replacement pytest:** `python/test_implement_dispatch.py:763-790` only stubs `_run` and checks argv shape.
- **Gap:** No pytest verifies the actual commit contents or preserved pre-staged unrelated changes.
- **Risk:** A regression in `scripts/git-commit.sh` or `python/git.py:1057-1096` could commit too much and still pass.

### FINDING-2: **push retry stderr dedupe is partial**
- **Deleted behavior:** `scripts/test-git-push.sh:28-72` asserts final exit code `7`, 3 attempts, and `BRANCH=feature`; `scripts/test-git-push.sh:74-114` asserts repeated stderr appears exactly once plus `(repeated 3 times)`.
- **Replacement pytest:** `python/test_push.py:178-185` checks `(repeated 3 times)` but not single occurrence of the stderr block; it also uses rc `1`, not a distinct final rc like `7`.
- **Gap:** Exit-code propagation and exact stderr de-duplication are not equivalent.
- **Risk:** Duplicate stderr or wrong final exit status could pass.

### FINDING-3: **clean-tree fail-open behavior lacks pytest**
- **Deleted behavior:** `scripts/test-check-clean-tree.sh:88-123` covers clean, dirty, default probe failure fail-open, fail-closed probe failure, and tab sanitization.
- **Replacement pytest:** `python/test_git.py:701-708` only covers `--fail-closed` probe failure.
- **Gap:** No pytest covers default probe failure returning `CLEAN=true` and rc 0, clean/dirty output shape, or summary sanitization.
- **Risk:** `python/git.py:894-905` could flip fail-open/fail-closed behavior without a pytest failure.

### FINDING-4: **main-sync reset safety is incomplete**
- **Deleted behavior:** `scripts/test-check-main-sync.sh:140-154` covers mixed flush plus non-flush ahead commits; `scripts/test-check-main-sync.sh:183-195` covers dirty working tree refusing reset.
- **Replacement pytest:** `python/test_check_main_sync.py:91-107` covers clean flush reset success; `python/test_check_main_sync.py:45-58` covers one non-log blocked commit.
- **Gap:** No pytest covers mixed-ahead blocking or dirty-tree refusal before reset.
- **Risk:** The reset guard in `python/git.py:994-1006` could regress and reset a dirty tree.

### FINDING-5: **phantom status matrix is not equivalent**
- **Deleted behavior:** `scripts/test-check-phantom-dirty.sh:61-138` covers clean, phantom, missing-baseline unknown, tracked-only, empty-baseline phantom, path with spaces, failed capture, and bad step tokens.
- **Replacement pytest:** `python/test_phantom.py:12-43` covers only a monkeypatched phantom path/count case; `python/test_git.py:710-737` covers clean output and unknown-flag parse error; `python/test_dirty_tree.py:140-192` covers lower-level baseline behavior.
- **Gap:** No pytest covers the wrapper status mapping for tracked-only, missing-baseline unknown, empty-baseline phantom, bad-step variants, or failed capture.
- **Risk:** Branches in `python/phantom.py:101-126` can regress without an equivalent test.

### FINDING-6: **check-remote-branch trichotomy has no direct pytest**
- **Contract:** `scripts/check-remote-branch.md:12-22` defines `present`, `absent`, and `error`, always exit 0.
- **Implementation:** `python/git.py:1015-1042` maps `git ls-remote` rc values; `python/git.py:1272-1287` emits the CLI envelope.
- **Current tests:** `python/test_finalize.py:232-246` only exercises an indirect rc 2 absent path; `python/test_finalize_bash_parity.py:49-69` monkeypatches absent.
- **Gap:** No pytest directly covers present, absent, transport error, missing `--branch`, stderr flatten/redaction, or always-exit-0 CLI behavior.
- **Risk:** The load-bearing trichotomy can regress silently.
## Reviewer stderr (<TMPDIR>/plan-review/round-1/dyn-codex-plan-coverage-guardian.txt.diag)

(file missing: <TMPDIR>/plan-review/round-1/dyn-codex-plan-coverage-guardian.txt.diag)

## Failed-agent stderr tail (<TMPDIR>/plan-review/round-1/dyn-codex-plan-coverage-guardian.txt.stderr-tail)

(file missing: <TMPDIR>/plan-review/round-1/dyn-codex-plan-coverage-guardian.txt.stderr-tail)

## Launcher stderr (<TMPDIR>/plan-review/round-1/dyn-codex-plan-coverage-guardian.txt.launch-stderr)

⏳ codex agent: still running (1m elapsed)
⏳ codex agent: still running (2m elapsed)
⏳ codex agent: still running (3m elapsed)
⏳ codex agent: still running (4m elapsed)
✓ codex agent: completed (exit code 0, output 3989 bytes)
  ```
### In-Scope Findings

1. **Important** — `risk-integration` — `larch-logs/design/BEBB7037-AA88-4887-A2E9-4DD7EDFD52A2/plan.txt:189-202`, `larch-logs/design/BEBB7037-AA88-4887-A2E9-4DD7EDFD52A2/plan.txt:698-711`, `python/run_logs.py:2735-2746`  
   What: The plan requires preserving `append-execution-issue.sh` / `append-tool-failure.sh` as Python runtime `argv0`, `prog`, and `USAGE` strings, but later requires the retired-name sweep to leave retired helper references only in `python/migrated-scripts.tsv`.  
   Concrete breakage path: An implementer who preserves exact append-entry / append-failure output leaves deleted helper basenames in `python/run_logs.py`; an implementer who removes them satisfies the sweep but violates the plan’s stated parity contract.  
   Suggested fix: Add an explicit narrow exception for basename-only compatibility strings in `python/run_logs.py`, or change the plan to cut those messages over to `run-log append-entry` / `run-log append-failure`.

### Out-of-Scope Observations

1. **Nit** — `risk-integration` — `larch-logs/design/BEBB7037-AA88-4887-A2E9-4DD7EDFD52A2/plan.txt:357-370`, `larch-logs/design/BEBB7037-AA88-4887-A2E9-4DD7EDFD52A2/plan.txt:441-485`  
   What: `scripts/lib-phantom-probe.sh` is kept and repointed, not deleted. It appears under append-entry cutovers, and it is absent from the delete list.  
   Suggested fix: No change required.  
   Note why out of scope: This is a verification result, not a defect.
## Reviewer stderr (<TMPDIR>/plan-review/round-1/dyn-codex-plan-consumer-sweeper.txt.diag)

(file missing: <TMPDIR>/plan-review/round-1/dyn-codex-plan-consumer-sweeper.txt.diag)

## Failed-agent stderr tail (<TMPDIR>/plan-review/round-1/dyn-codex-plan-consumer-sweeper.txt.stderr-tail)

(file missing: <TMPDIR>/plan-review/round-1/dyn-codex-plan-consumer-sweeper.txt.stderr-tail)

## Launcher stderr (<TMPDIR>/plan-review/round-1/dyn-codex-plan-consumer-sweeper.txt.launch-stderr)

⏳ codex agent: still running (1m elapsed)
⏳ codex agent: still running (2m elapsed)
⏳ codex agent: still running (3m elapsed)
⏳ codex agent: still running (4m elapsed)
⏳ codex agent: still running (5m elapsed)
⏳ codex agent: still running (6m elapsed)
✓ codex agent: completed (exit code 0, output 1481 bytes)
  ```
### In-Scope Findings

1. **Blocking** — `risk-integration` — `python/bootstrap.py:735-736`, `python/review_and_fix.py:2294-2301`, `python/bootstrap.py:1435-1440`, `python/step_7a.py:290-299`, `skills/implement/scripts/step-8-ship.sh:63-65`, `scripts/rebase-checkpoint-probe.sh:70-75`  
   What: **Deleted helper paths still have live callers**. `snapshot-untracked.sh`, `rebase-checkpoint-probe.sh`, `phantom-probe-with-warn.sh`, and `rebase-push.sh` are still invoked by runtime paths.  
   Concrete failing scenario: after deletion, Step 0 bootstrap, review round 1, Step 7a, Step 8 ship, or checkpoint probe hits `ENOENT` before reaching the Python replacement.  
   Suggested fix: replace these call sites with the new `python3 python/cli.py ...` commands, or keep thin compatibility wrappers.

2. **Important** — `risk-integration` — `python/git.py:1230-1238`, `python/git.py:1272-1281`, `scripts/snapshot-untracked.sh:28-45`, `scripts/check-remote-branch.sh:36-52`  
   What: **Argparse breaks legacy fail-open argv errors** for `snapshot-untracked` and `check-remote-branch`. Unknown flags and missing values now emit `cli.py ...` argparse usage on stderr, then often emit the wrong legacy `ERROR` or message.  
   Concrete failing scenario: `check-remote-branch --bogus` should emit `ERROR=unknown flag: --bogus`, but the Python path emits `ERROR=--branch is required`; `snapshot-untracked --output` should say `--output requires a value`, but it says `--output is required`.  
   Suggested fix: hand-parse these wrappers like the shell did, preserving stdout keys, stderr prefixes, and exit 0 fail-open behavior.

3. **Important** — `risk-integration` — `python/git.py:682-694`, `python/push.py:218-238`, `scripts/git-force-push.sh:62-73`  
   What: **Force-push recovery loses stderr diagnostics** on dirty-tree and status-probe failures. The shell emits the `git-force-push.sh:` prefix plus dirty paths; the Python CLI only emits `PUSHED=false` and `STATUS=...`.  
   Concrete failing scenario: a dirty worktree before force-push exits 1 without listing the paths, so callers and operators lose the documented recovery detail.  
   Suggested fix: carry the status stderr and dirty porcelain through `ForcePushResult`, and print the same prefixed diagnostics in `push.force_main`.

4. **Important** — `correctness` — `python/phantom.py:92-100`, `python/phantom.py:135-162`, `python/phantom.py:173-201`, `scripts/lib-phantom-probe.sh:51-60`  
   What: **Phantom probe no-`IMPLEMENT_TMPDIR` behavior changed**. The shell emits `PHANTOM_REASON=IMPLEMENT_TMPDIR-unset` and returns without append attempts; Python reports `phantom-paths-dir-required` and adds `PHANTOM_APPEND_WARN_ERROR=IMPLEMENT_TMPDIR-unset`.  
   Concrete failing scenario: standalone `phantom-probe --step s1` without `IMPLEMENT_TMPDIR` produces a different reason and an extra append-failure key, which can trip contract parsers.  
   Suggested fix: add the shell’s early `IMPLEMENT_TMPDIR` guard before `check_phantom_dirty` and skip warning appends in that case.

5. **Important** — `risk-integration` — `python/push.py:295-303`, `scripts/lib-phantom-probe.sh:75-83`  
   What: **Checkpoint probe emits `PHANTOM_COUNT=0` for non-phantom statuses**. The shell only emits count and paths when those fields are present.  
   Concrete failing scenario: a clean post-rebase probe now has `PHANTOM_STATUS=clean` plus `PHANTOM_COUNT=0`, widening the KV contract and potentially confusing consumers that treat the count key as phantom-specific.  
   Suggested fix: mirror `phantom_probe_main`: emit `PHANTOM_COUNT` and `PHANTOM_PATHS_FILE` only when status is `phantom`.
## Reviewer stderr (<TMPDIR>/plan-review/round-1/dyn-codex-plan-parity-auditor.txt.diag)

(file missing: <TMPDIR>/plan-review/round-1/dyn-codex-plan-parity-auditor.txt.diag)

## Failed-agent stderr tail (<TMPDIR>/plan-review/round-1/dyn-codex-plan-parity-auditor.txt.stderr-tail)

(file missing: <TMPDIR>/plan-review/round-1/dyn-codex-plan-parity-auditor.txt.stderr-tail)

## Launcher stderr (<TMPDIR>/plan-review/round-1/dyn-codex-plan-parity-auditor.txt.launch-stderr)

⏳ codex agent: still running (1m elapsed)
⏳ codex agent: still running (2m elapsed)
⏳ codex agent: still running (3m elapsed)
⏳ codex agent: still running (4m elapsed)
⏳ codex agent: still running (5m elapsed)
⏳ codex agent: still running (6m elapsed)
⏳ codex agent: still running (7m elapsed)
✓ codex agent: completed (exit code 0, output 3690 bytes)
  ```
### In-Scope Findings

1. **Important** — `risk-integration` — `python/push.py:274-304`, `scripts/rebase-checkpoint-probe.sh:24-61,340-381`, `skills/implement/SKILL.md:533,717`  
   What: `push checkpoint-probe` is not argv or stdout compatible with `rebase-checkpoint-probe.sh`. It lacks `--forked-target`, omits the required `ROUTE=` key, and emits `PHANTOM_COUNT=0` even when the phantom status is clean.  
   Concrete failing scenario: a forked run reaches Step 4.r or 7.r with the current `--forked-target "${forked_target:-false}"` argv, the Python replacement exits 2 before rebase, and routing loses the `ROUTE=continue|conflict|bail` contract.  
   Suggested fix: add `--forked-target true|false`, preserve the upstream/main mapping, emit `ROUTE` on every rebase path, and only emit `PHANTOM_COUNT` when the phantom result is actually `phantom`.

2. **Important** — `correctness` — `python/push.py:284-294`, `python/rebase.py:594-603`, `scripts/rebase-checkpoint-probe.sh:255-338`  
   What: the Python checkpoint replacement calls `rebase.rebase_push()` once and returns conflicts directly. It drops the shell wrapper’s larch-log-only trivial-conflict pre-pass and empty-continue recovery loop.  
   Concrete failing scenario: a rebase conflict only touches `larch-logs/*`; the shell wrapper resolves it with `git checkout --ours` / `git rm`, continues the rebase, and then runs the phantom probe, but the Python replacement returns `REBASE_OUTCOME=conflict` and stalls the workflow.  
   Suggested fix: port the wrapper pre-pass before deleting the shell helper, or keep the shell helper until the Python surface has parity tests for larch-log-only, mixed, and empty-continue cases.

3. **Important** — `correctness` — `python/git.py:920-942`, `python/git.py:1230-1238`, `scripts/snapshot-untracked.sh:7-16,62-63`  
   What: `snapshot_untracked()` can raise during failure cleanup. The shell helper always exits 0 and best-effort removes `$OUTPUT` / `$TMP`, but Python calls `unlink()` outside a suppressing cleanup path.  
   Concrete failing scenario: `git ls-files` fails and `--output` points at a directory or otherwise unlink-protected path; Python raises `IsADirectoryError` / `OSError`, so the CLI exits nonzero instead of fail-opening.  
   Suggested fix: wrap both cleanup unlinks in `contextlib.suppress(OSError)` and keep returning 0 on every operational failure.

4. **Important** — `risk-integration` — `python/phantom.py:92-99,135-162,173-201`, `python/git.py:1359-1380`, `scripts/lib-phantom-probe.sh:51-54`  
   What: `phantom.probe_with_warn()` changes the unset-`IMPLEMENT_TMPDIR` fail-open path. The shell emits `PHANTOM_STATUS=unknown` and `PHANTOM_REASON=IMPLEMENT_TMPDIR-unset` and returns without appending, but Python reports a different reason and then attempts a warning append, producing `PHANTOM_APPEND_WARN_ERROR=IMPLEMENT_TMPDIR-unset`.  
   Concrete failing scenario: a standalone phantom probe runs without `IMPLEMENT_TMPDIR`; the replacement surfaces an append failure that the shell never emitted, which can mislead operators into debugging the warning appender instead of the missing environment.  
   Suggested fix: special-case missing `IMPLEMENT_TMPDIR` before `check_phantom_dirty()` append handling, emit the shell-compatible reason, and skip warning appends.

### Out-of-Scope Observations

(none)
## Reviewer stderr (<TMPDIR>/plan-review/round-1/dyn-cursor-plan-parity-auditor-phase2.txt.diag)

(file missing: <TMPDIR>/plan-review/round-1/dyn-cursor-plan-parity-auditor-phase2.txt.diag)

## Failed-agent stderr tail (<TMPDIR>/plan-review/round-1/dyn-cursor-plan-parity-auditor-phase2.txt.stderr-tail)

(file missing: <TMPDIR>/plan-review/round-1/dyn-cursor-plan-parity-auditor-phase2.txt.stderr-tail)

## Launcher stderr (<TMPDIR>/plan-review/round-1/dyn-cursor-plan-parity-auditor-phase2.txt.launch-stderr)

⏳ codex agent: still running (1m elapsed)
⏳ codex agent: still running (2m elapsed)
⏳ codex agent: still running (3m elapsed)
⏳ codex agent: still running (4m elapsed)
⏳ codex agent: still running (5m elapsed)
⏳ codex agent: still running (6m elapsed)
⏳ codex agent: still running (7m elapsed)
✓ codex agent: completed (exit code 0, output 3368 bytes)
  ```
### Warnings

- **Step design Step 3.5 / Gate B — validate-plan-commands failed (exit 0)**:
  ```
DEFECT script=scripts/test-rebase-checkpoint-probe.sh kind=missing-script
DEFECT script=scripts/test-merge-pr.sh kind=missing-script
DEFECT script=scripts/test-create-pr.sh kind=missing-script
DEFECT script=skills/implement/scripts/test-step-8-ship.sh kind=missing-script
DEFECT script=scripts/test-implement-fence-shape.sh kind=missing-script
VALIDATE_STATUS=defects-found	DEFECT_COUNT=5	SKIPPED_COUNT=0	UNSAFE_TOKEN_COUNT=0
  ```

- **Step design Step 5c — validate-plan-commands failed (exit 0)**:
  ```
DEFECT script=scripts/test-rebase-checkpoint-probe.sh kind=missing-script
DEFECT script=scripts/test-merge-pr.sh kind=missing-script
DEFECT script=scripts/test-create-pr.sh kind=missing-script
DEFECT script=skills/implement/scripts/test-step-8-ship.sh kind=missing-script
DEFECT script=scripts/test-implement-fence-shape.sh kind=missing-script
VALIDATE_STATUS=defects-found	DEFECT_COUNT=5	SKIPPED_COUNT=0	UNSAFE_TOKEN_COUNT=0
  ```
