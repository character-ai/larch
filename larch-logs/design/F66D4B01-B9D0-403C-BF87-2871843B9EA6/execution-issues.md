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

- **Step design Step 3 — collect-results cursor NOT_SUBSTANTIVE failed (exit 0)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/plan-review/round-2/cursor-plan-requirements-output.txt|TOOL=cursor|STATUS=NOT_SUBSTANTIVE|EXIT_CODE=0|FAILURE_REASON=structured records not found after repair

## Reviewer output (<TMPDIR>/plan-review/round-2/cursor-plan-requirements-output.txt)

Reading the plan and verifying it against the feature scope and codebase.
schema_version	scope	severity	focus_area	location	what	scenario_or_breakage	suggested_fix
1	in_scope	important	completeness	plan.txt:40-250	Terminal lib and harness deletions are described only in Approach and migrated-scripts.tsv append; Files lacks firm delete entries for scripts/lib-*.sh, sibling .md files, scripts/test-lib-{quiet,net,submodule-prohibition}.sh, and Makefile test-harnesses-* wiring is MAY_UPDATE only	Implementer can retire consumers but leave lib-*.sh and make test-lib-* targets in place; make lint still runs deleted harnesses and DoD "terminal libs retired" is not mechanically closed	Add firm ### REWRITTEN:/delete subsections for each terminal lib artifact plus ### UPDATED: Makefile rows removing test-lib-quiet, test-lib-net, test-lib-submodule-prohibition and rebalance shards; require docs/linting.md removal of stale test-lib-net and test-lib-submodule-prohibition entries
2	in_scope	important	correctness	plan.txt:165-174	deny-edit-write.sh, audit-edit-write.sh, and sleep-seconds.sh are listed as UPDATED but have no owned bullets; the lib-quiet removal steps sit only under extract-closes-issue-from-pr.sh	All three still source scripts/lib-quiet.sh today; an implementer following per-file headings can delete lib-quiet.sh while these hooks keep sourcing it	Add explicit per-file bullets for deny-edit-write.sh, audit-edit-write.sh, and sleep-seconds.sh to remove lib-quiet sourcing and preserve hook wire contracts
3	in_scope	important	correctness	.github/workflows/ci.yaml:645-656	Plan narrows only the shellcheck job to scripts/residual-bash-enumerate.sh; the separate bash32-check job still runs find scripts skills .claude -name '*.sh'	Pre-commit bash-syntax and lint-bash32 narrow to the residual manifest while CI still syntax-checks every tracked .sh under those trees; CI/local scope diverge and the plan's own failure-mode note for shellcheck applies equally here	Update the bash32-check job to consume scripts/residual-bash-enumerate.sh (same set as shellcheck and pre-commit) or document an intentional broader CI scope with a compensating gate
4	in_scope	important	correctness	plan.txt:42-51	scripts/residual-bash-paths.txt must list ~50 thin python/cli.py delegation wrappers but the plan defines no discovery or refresh contract for that set	An incomplete hand-maintained manifest drops shellcheck, bash-syntax, and lint-bash32 coverage on kept wrappers while CI claims residual-only scanning	Specify one inventory step (for example rg/git ls-files for thin delegation pattern) that seeds or validates residual-bash-paths.txt and require test-residual-bash-enumerate to fail when a kept wrapper is missing
5	in_scope	important	completeness	plan.txt:277-305	Issue scope requires deleting verified-zero-consumer orphan utilities; Testing strategy inventories terminal libs only and Files has no orphan deliverable beyond migrated-scripts.tsv rows	Post-G-track orphan scripts can remain in the tree while E3 is marked done without a recorded orphan sweep	Add a preflight orphan pass with recorded results in docs/python-migration.md and firm delete rows (or explicit no-orphans evidence) before terminal-lib deletion
6	in_scope	important	completeness	plan.txt:53-57;Makefile	Testing strategy calls make test-residual-bash-enumerate but the plan never adds a Makefile target or harness shard for scripts/test-residual-bash-enumerate.sh	The new manifest contract is not on the make lint path unless an operator runs the harness manually	Add ### UPDATED: Makefile with test-residual-bash-enumerate target and shard assignment alongside test-lint-bash32

**1. completeness** (`plan.txt:40-250`) — Terminal lib and harness deletions are only in Approach plus `migrated-scripts.tsv` append. Files has no firm delete entries for `scripts/lib-*.sh`, sibling `.md` files, `scripts/test-lib-{quiet,net,submodule-prohibition}.sh`, and Makefile harness removal is `MAY_UPDATE` only. Implementer can leave libs and `make test-lib-*` targets in place; `make lint` still runs deleted harnesses.

**2. correctness** (`plan.txt:165-174`) — `deny-edit-write.sh`, `audit-edit-write.sh`, and `sleep-seconds.sh` are listed as `UPDATED` without owned bullets. Lib-quiet removal steps sit only under `extract-closes-issue-from-pr.sh`. All three still `source` `lib-quiet.sh` today.

**3. correctness** (`.github/workflows/ci.yaml:645-656`) — Plan narrows the shellcheck job to the residual enumerator. The separate `bash32-check` job still runs `find scripts skills .claude -name '*.sh'`. Pre-commit narrows while CI syntax-checks the full tree.

**4. correctness** (`plan.txt:42-51`) — `residual-bash-paths.txt` must list thin `cli.py` wrappers but has no discovery or refresh contract. An incomplete manifest drops linter coverage on kept wrappers.

**5. completeness** (`plan.txt:277-305`) — Issue scope requires deleting verified-zero-consumer orphan utilities. Testing strategy inventories terminal libs only. No orphan deliverable beyond `migrated-scripts.tsv` rows.

**6. completeness** (`plan.txt:53-57`; `Makefile`) — Testing strategy calls `make test-residual-bash-enumerate` but the plan never adds a Makefile target or shard for `scripts/test-residual-bash-enumerate.sh`.

[OUT_OF_SCOPE] **risk-integration** (`python/test_retry.py:62-64`) — Deleting `lib-net.sh` makes bash parity tests skip when the file is absent. Python-native retry tests remain. Worth a follow-up issue, not an E3 blocker.

[OUT_OF_SCOPE] **architecture** (`plan.txt:19`) — Retiring `lib-submodule-prohibition.sh` extends the issue's seven-lib list, but runtime callers are already Python-inlined and only the harness sources the shell lib. Deletion is consistent with the harness-only rule; no in-scope change required beyond finding 1 cleanup.
## Reviewer stderr (<TMPDIR>/plan-review/round-2/cursor-plan-requirements-output.txt.diag)

(empty: <TMPDIR>/plan-review/round-2/cursor-plan-requirements-output.txt.diag)

## Failed-agent stderr tail (<TMPDIR>/plan-review/round-2/cursor-plan-requirements-output.txt.stderr-tail)

(file missing: <TMPDIR>/plan-review/round-2/cursor-plan-requirements-output.txt.stderr-tail)

## Launcher stderr (<TMPDIR>/plan-review/round-2/cursor-plan-requirements-output.txt.launch-stderr)

⏳ cursor agent: still running (1m elapsed)
⏳ cursor agent: still running (2m elapsed)
⏳ cursor agent: still running (3m elapsed)
✓ cursor agent: completed (exit code 0, output 6236 bytes)
  ```

- **Step design Step 3 — collect-results cursor NOT_SUBSTANTIVE failed (exit 0)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/plan-review/round-5/cursor-plan-requirements-output.txt|TOOL=cursor|STATUS=NOT_SUBSTANTIVE|EXIT_CODE=0|FAILURE_REASON=structured records not found after repair

## Reviewer output (<TMPDIR>/plan-review/round-5/cursor-plan-requirements-output.txt)

Reviewing the plan against the issue scope and verifying cited paths in the codebase.
schema_version	scope	severity	focus_area	location	what	scenario_or_breakage	suggested_fix
1	in_scope	important	completeness	plan.txt:13-20	Residual inventory lists eight hooks and omits `skills/implement/scripts/hook-stop-fail-close.sh` even though issue scope names nine kept hooks and `hooks/hooks.json` registers it as the Stop hook	E3 deletes or narrows `lib-quiet.sh` for `hook-stop-fail-close.sh` but the script is absent from `scripts/residual-bash-paths.txt` and linter scope; whole-tree compliance may misclassify it and shellcheck/bash32 may drop coverage	Add `skills/implement/scripts/hook-stop-fail-close.sh` to the final residual inventory bullets and `### NEW: scripts/residual-bash-paths.txt` rows; document it alongside the other kept hooks
2	in_scope	important	correctness	plan.txt:181-184	`### UPDATED: scripts/sessionstart-health.sh` removes `lib-quiet.sh` without a blocking emit contract while the hook still calls `larch_quiet_init` and `emit()` for SessionStart advisory JSON	After `lib-quiet.sh` retirement, probe noise can land on hook stdout or advisory JSON can fail to reach Claude; `make test-sessionstart` regressions are likely	Specify the same class of inline contract as `deny-edit-write.sh`: optional quiet log redirect for probes plus a local `hook_emit()` (FD 3 dup) for advisory JSON; require `make test-sessionstart` in Testing strategy
3	in_scope	important	correctness	plan.txt:212-214	`### UPDATED: skills/implement/scripts/hook-stop-fail-close.sh` only says to drop `lib-quiet.sh` sourcing but the Stop hook still uses `emit()` for block JSON on the contract stream	Retiring `lib-quiet.sh` without an inline FD-3 `hook_emit()` path can break post-/review halt protection (empty or misrouted block JSON)	Mirror the blocking `deny-edit-write.sh` FD-3 inline emit steps for `hook-stop-fail-close.sh` and note the contract in `SECURITY.md` / `BASH_AUTHORING.md`
4	in_scope	important	completeness	skills/implement/SKILL.md:876	`### UPDATED: skills/implement/SKILL.md` covers `extract-closes-issue-from-pr.sh` and OOS include prose but not the Step 18a helper list that still pins `scripts/lib-larch-dev-clone.sh` while the plan retires that lib	`make lint-retired-scripts` or operator docs stay stale after `lib-larch-dev-clone.sh` deletion; Step 18a points implementers at a removed helper	Add a bullet to repoint Step 18a helper text to `python/cli.py stall-recovery is-larch-dev-clone` (or the delegated equivalent used by `check-stale-plugin.sh`) and drop the deleted bash path
5	in_scope	important	completeness	plan.txt:55-59	`scripts/residual-bash-paths.txt` is new but the plan never states how the ~50 thin `python/cli.py` delegation wrappers are enumerated into the manifest	An incomplete manifest under-scopes shellcheck, bash-syntax, and bash32 on live wrappers still shipped in the plugin; over-scoping is less likely but manual omission is	After the whole-tree compliance pass, add an explicit manifest-authoring step: append every classified thin wrapper path from the pass output to `scripts/residual-bash-paths.txt` and assert manifest completeness in `python/test_residual_bash.py` (tracked `*.sh` residual set minus allowed categories equals manifest rows)

## Findings

1. **completeness** (`plan.txt:13-20`): The residual inventory names eight hooks and leaves out `skills/implement/scripts/hook-stop-fail-close.sh`, even though issue scope lists nine kept hooks and `hooks/hooks.json` wires it as the Stop hook. Add it to the inventory and manifest rows.

2. **correctness** (`plan.txt:181-184`): `sessionstart-health.sh` still depends on `larch_quiet_init` and `emit()` for SessionStart advisory JSON, but the plan only says to remove `lib-quiet.sh` without an inline emit contract. Specify quiet-log plus FD-3 `hook_emit()` parity with `deny-edit-write.sh` and require `make test-sessionstart`.

3. **correctness** (`plan.txt:212-214`): `hook-stop-fail-close.sh` uses `emit()` for block JSON; the plan does not define FD-3 replacement after `lib-quiet.sh` retirement. Mirror the `deny-edit-write.sh` inline contract.

4. **completeness** (`skills/implement/SKILL.md:876`): Step 18a still cites `scripts/lib-larch-dev-clone.sh`; the plan’s `skills/implement/SKILL.md` updates omit that removal. Repoint to `python/cli.py stall-recovery is-larch-dev-clone`.

5. **completeness** (`plan.txt:55-59`): No procedure populates `residual-bash-paths.txt` with all thin delegation wrappers from the compliance pass. Add an explicit manifest-authoring step and a completeness assertion in `python/test_residual_bash.py`.
## Reviewer stderr (<TMPDIR>/plan-review/round-5/cursor-plan-requirements-output.txt.diag)

(empty: <TMPDIR>/plan-review/round-5/cursor-plan-requirements-output.txt.diag)

## Failed-agent stderr tail (<TMPDIR>/plan-review/round-5/cursor-plan-requirements-output.txt.stderr-tail)

(file missing: <TMPDIR>/plan-review/round-5/cursor-plan-requirements-output.txt.stderr-tail)

## Launcher stderr (<TMPDIR>/plan-review/round-5/cursor-plan-requirements-output.txt.launch-stderr)

⏳ cursor agent: still running (1m elapsed)
⏳ cursor agent: still running (2m elapsed)
⏳ cursor agent: still running (3m elapsed)
⏳ cursor agent: still running (4m elapsed)
⏳ cursor agent: still running (5m elapsed)
✓ cursor agent: completed (exit code 0, output 5032 bytes)
  ```
