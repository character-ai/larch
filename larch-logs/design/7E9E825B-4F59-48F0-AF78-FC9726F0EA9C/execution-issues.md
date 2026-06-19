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

- **Step design Step 3 — collect-results cursor NOT_SUBSTANTIVE failed (exit 0)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/plan-review/round-1/dyn-cursor-plan-stage-scope.txt|TOOL=cursor|STATUS=NOT_SUBSTANTIVE|EXIT_CODE=0|FAILURE_REASON=structured records not found after repair

## Reviewer output (<TMPDIR>/plan-review/round-1/dyn-cursor-plan-stage-scope.txt)

Searching the codebase for the `_collect_round_stage_paths` plan and baseline-handling logic.
**Verdict:** OOS_1 closes the **missing** and **empty-baseline** whole-tree staging hole with a small `_collect_round_stage_paths` change, but **`since_committed=True` without a valid `post-coder-head.txt` is under-specified** and can still stage unrelated paths via `_round_diff_base`’s `pre_head` fallback.


- **Step design Step 3 — collect-results codex NOT_SUBSTANTIVE failed (exit 0)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/plan-review/round-1/dyn-codex-plan-stage-scope.txt|TOOL=codex|STATUS=NOT_SUBSTANTIVE|EXIT_CODE=0|FAILURE_REASON=structured records not found after repair

## Reviewer output (<TMPDIR>/plan-review/round-1/dyn-codex-plan-stage-scope.txt)


- **Step design Step 3 — collect-results cursor NOT_SUBSTANTIVE failed (exit 0)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/plan-review/round-1/dyn-cursor-plan-lint-delta.txt|TOOL=cursor|STATUS=NOT_SUBSTANTIVE|EXIT_CODE=0|FAILURE_REASON=structured records not found after repair

## Reviewer output (<TMPDIR>/plan-review/round-1/dyn-cursor-plan-lint-delta.txt)

I'll locate the `_lint_fix_delta_paths` plan and trace Step 5 lint-fix behavior in the codebase.
**Verdict:** The `_lint_fix_delta_paths` plan mostly matches the shipped Step 5 lint-fix path, but one core dirty-baseline scenario (`no-changes` + in-place pre-dirty edit) is still not closed, and several test/envelope gaps remain.

---

## Summary

The implementation in `python/review_and_fix.py` follows the plan’s snapshot helpers, `lint_applied_ever` gate, sorted path union, pathspec-only commit, and `lint-fix-commit-failed` stall wiring. The main gap is between **plan edge case / failure-mode claims** (snapshot closes in-place pre-dirty edits) and **plan behavior bullet 160 + code** (`lint_applied_ever` must be true before any post-loop commit). On a dirty baseline, `checks._delta_paths_after_dispatch` treats in-place edits to already-tracked files as `no-changes`, so `lint_applied_ever` never flips and `_lint_fix_delta_paths` never runs, even when recheck passes.

---

## Findings


- **Step design Step 3 — collect-results codex NOT_SUBSTANTIVE failed (exit 0)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/plan-review/round-1/dyn-codex-plan-lint-delta.txt|TOOL=codex|STATUS=NOT_SUBSTANTIVE|EXIT_CODE=0|FAILURE_REASON=structured records not found after repair

## Reviewer output (<TMPDIR>/plan-review/round-1/dyn-codex-plan-lint-delta.txt)


- **Step design Step 3 — collect-results cursor NOT_SUBSTANTIVE failed (exit 0)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/plan-review/round-1/dyn-cursor-plan-cleanup-test-first.txt|TOOL=cursor|STATUS=NOT_SUBSTANTIVE|EXIT_CODE=0|FAILURE_REASON=structured records not found after repair

## Reviewer output (<TMPDIR>/plan-review/round-1/dyn-cursor-plan-cleanup-test-first.txt)

Searching the repo for the OOS_3 plan and related verification/cleanup scope.
**Verdict:** The plan in `larch-logs/design/BD9CFCF6-95EC-49B8-B0BD-7A3DCF227885/plan.txt` (issue #4712; OOS_3 = `lint_applied_ever` from implement `55C91B5E`) is **mostly scope-disciplined on production changes**, but it does **not** require a narrow partial-verification regression **before** the cleanup/self-heal code lands, and its test guidance invites **blanket monkeypatching** that can bypass the very paths under review.

---

## Partial verification regression before cleanup code

**Partially confirmed for content, not for ordering.**

The plan **does** specify the narrow partial-verification regression for the cleanup/self-heal path:

- **Plan bullet** (`plan.txt` **§Files → `python/test_ci_agentic_fix.py`**, mixed-failure case): when a known harness signature matches **and** another fixable job still fails local verify, `_run_cycle` must rollback, delegate via `agents.launch_tier`, and not early-exit on partial mechanical success.
- **Plan bullet** (`plan.txt` **§Approach → Self-heal #1/#2**, partition helper): rewrite is limited to `test-implement-cleanup-script:` with `-k cleanup` only (no broad Makefile cleanup).

It **does not** sequence that regression **before** the cleanup helper:

- **Plan bullet** (`plan.txt` **§Files**): `python/ci_agentic_fix.py` (including `_apply_finalize_cleanup_partition_fix`) is listed **before** `python/test_ci_agentic_fix.py`.
- **Plan bullet** (`plan.txt` **§Testing strategy**): “Run focused tests first” means at **validation** time, not **implementation** order (test-first TDD).

**Implemented state** (for fidelity check): `python/test_ci_agentic_fix.py` has `test_run_cycle_mixed_mechanical_failure_rolls_back_then_delegates` at ```1034:1082:python/test_ci_agentic_fix.py```, but it **stubs** `_apply_known_harness_fix` (line 1049) instead of exercising the real partition rewrite.

---

## OOS_3 (`lint_applied_ever`) scope

**Confirmed narrow on production; regression exists but is not ordered before code.**

OOS_3 concern (implement `55C91B5E` round-2): missing `lint_applied_ever` guard at `python/review_and_fix.py:1267-1278`.

Plan coverage:

- **Plan bullet** (`plan.txt` **§`python/review_and_fix.py` → Behavior**): track `lint_applied_ever`; **do not** call `_commit_lint_fix_delta_paths` when false (lines 159-164 in plan).
- **Plan bullet** (`plan.txt` **§`python/test_review_and_fix.py` → Cover**): “When no lint-fix was applied, the commit helper does not run” (line 186).

Again, **no test-before-code** mandate: `review_and_fix.py` is specified before `test_review_and_fix.py`.

**Implemented:** guard at ```1771:1775:python/review_and_fix.py```; regression at ```2084:2106:python/test_review_and_fix.py``` (`test_step5_lint_fix_no_changes_without_applied_lint_does_not_commit`).

---

## Findings (scope / test discipline)


- **Step design Step 3 — collect-results codex NOT_SUBSTANTIVE failed (exit 0)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/plan-review/round-1/dyn-codex-plan-cleanup-test-first.txt|TOOL=codex|STATUS=NOT_SUBSTANTIVE|EXIT_CODE=0|FAILURE_REASON=structured records not found after repair

## Reviewer output (<TMPDIR>/plan-review/round-1/dyn-codex-plan-cleanup-test-first.txt)

**Finding 1: minor, test-first ordering is not explicit.**

- **Plan bullet:** `larch-logs/design/074668FC-3A89-432E-9668-44BC978C0A67/plan.txt:224-245`
- **Issue:** The plan adds the narrow OOS_3 regression by extending `python/test_upgrade_larch.py` to add the six root config files to `_populate_cleanup_fixture()` and assert removal.
- **But:** The cleanup code change in `python/upgrade_larch.py` is listed first at lines 224-237, and the regression is listed after it at lines 239-245.
- **Why it matters:** If the instruction is “regression before cleanup code change,” the plan should say that explicitly.
- **Fix:** Move or prefix the `python/test_upgrade_larch.py` bullet with “Add this failing regression before changing cleanup patterns.”

**Confirmed scope discipline:**

- **OOS_3 source:** `feature-description.txt:43-47`
- **Cleanup plan:** exact six root config files only. No broad dotfile glob. `plan.txt:224-237`
- **Regression plan:** fixture plus removal assertions only. `plan.txt:239-245`
- **No proactive cleanup rewrite found.**
- **No blanket monkeypatch found that weakens this OOS_3 test.**
## Reviewer stderr (<TMPDIR>/plan-review/round-1/dyn-codex-plan-cleanup-test-first.txt.diag)

(file missing: <TMPDIR>/plan-review/round-1/dyn-codex-plan-cleanup-test-first.txt.diag)

## Failed-agent stderr tail (<TMPDIR>/plan-review/round-1/dyn-codex-plan-cleanup-test-first.txt.stderr-tail)

(file missing: <TMPDIR>/plan-review/round-1/dyn-codex-plan-cleanup-test-first.txt.stderr-tail)

## Launcher stderr (<TMPDIR>/plan-review/round-1/dyn-codex-plan-cleanup-test-first.txt.launch-stderr)

⏳ codex agent: still running (1m elapsed)
⏳ codex agent: still running (2m elapsed)
⏳ codex agent: still running (3m elapsed)
⏳ codex agent: still running (4m elapsed)
✓ codex agent: completed (exit code 0, output 1127 bytes)
  ```

- **Step design Step 3 — collect-results cursor NOT_SUBSTANTIVE failed (exit 0)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/plan-review/round-2/cursor-plan-arch-output.txt|TOOL=cursor|STATUS=NOT_SUBSTANTIVE|EXIT_CODE=0|FAILURE_REASON=structured records not found after repair

## Reviewer output (<TMPDIR>/plan-review/round-2/cursor-plan-arch-output.txt)

Reviewing the plan against the codebase: reading the plan and the cited implementation paths.
{"no_issues_found": true}
## Reviewer stderr (<TMPDIR>/plan-review/round-2/cursor-plan-arch-output.txt.diag)

(empty: <TMPDIR>/plan-review/round-2/cursor-plan-arch-output.txt.diag)

## Failed-agent stderr tail (<TMPDIR>/plan-review/round-2/cursor-plan-arch-output.txt.stderr-tail)

(file missing: <TMPDIR>/plan-review/round-2/cursor-plan-arch-output.txt.stderr-tail)

## Launcher stderr (<TMPDIR>/plan-review/round-2/cursor-plan-arch-output.txt.launch-stderr)

⏳ cursor agent: still running (1m elapsed)
⏳ cursor agent: still running (2m elapsed)
⏳ cursor agent: still running (3m elapsed)
✓ cursor agent: completed (exit code 0, output 438 bytes)
  ```

- **Step design Step 3 — collect-results cursor NOT_SUBSTANTIVE failed (exit 0)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/plan-review/round-2/cursor-plan-requirements-output.txt|TOOL=cursor|STATUS=NOT_SUBSTANTIVE|EXIT_CODE=0|FAILURE_REASON=structured records not found after repair

## Reviewer output (<TMPDIR>/plan-review/round-2/cursor-plan-requirements-output.txt)

Reviewing the plan against the binding scope; reading the plan and cited code paths.
{"no_issues_found": true}
## Reviewer stderr (<TMPDIR>/plan-review/round-2/cursor-plan-requirements-output.txt.diag)

(empty: <TMPDIR>/plan-review/round-2/cursor-plan-requirements-output.txt.diag)

## Failed-agent stderr tail (<TMPDIR>/plan-review/round-2/cursor-plan-requirements-output.txt.stderr-tail)

(file missing: <TMPDIR>/plan-review/round-2/cursor-plan-requirements-output.txt.stderr-tail)

## Launcher stderr (<TMPDIR>/plan-review/round-2/cursor-plan-requirements-output.txt.launch-stderr)

⏳ cursor agent: still running (1m elapsed)
⏳ cursor agent: still running (2m elapsed)
⏳ cursor agent: still running (3m elapsed)
⏳ cursor agent: still running (4m elapsed)
✓ cursor agent: completed (exit code 0, output 426 bytes)
  ```

- **Step review Step 2 — cursor-review failed (exit 1 — unknown — auth-retries=2, transient-retries=1)**:
  ```
===== sidecar.history =====
===== cursor auth attempt diag =====
Error: Security command failed: Security process exited with code: 45
Failed with exit code 1. Output size: 0 bytes.
===== diag =====
[31m✗ Failed to reach the Cursor API. If you are behind a corporate proxy, set the HTTPS_PROXY environment variable.[0m
Failed with exit code 1. Output size: 0 bytes.
===== launch-stderr =====
❌ cursor agent: FAILED (exit code 1, output 0 bytes)
❌ cursor agent: FAILED (exit code 1, output 0 bytes)

===== additional failure diagnostics =====
===== sidecar.history =====
===== cursor auth attempt diag =====
Error: Security command failed: Security process exited with code: 45
Failed with exit code 1. Output size: 0 bytes.
===== diag =====
[31m✗ Failed to reach the Cursor API. If you are behind a corporate proxy, set the HTTPS_PROXY environment variable.[0m
Failed with exit code 1. Output size: 0 bytes.
===== launch-stderr =====
❌ cursor agent: FAILED (exit code 1, output 0 bytes)
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
### 1. No explicit “regression first, then cleanup code” sequencing

| Item | Plan reference | Issue |
|------|----------------|-------|
| File order puts production before tests | `plan.txt` §Files: `python/ci_agentic_fix.py` then `python/test_ci_agentic_fix.py` | Mixed-failure regression is specified but not required to land **before** `_apply_finalize_cleanup_partition_fix` |
| Validation ≠ implementation order | `plan.txt` §Testing strategy (lines 312-320) | “Run focused tests first” does not bind implementer sequencing |

**Risk:** cleanup rewrite can ship before the partial-verify rollback path is pinned by a failing test.

---

### 2. Mixed-failure test uses blanket monkeypatch that bypasses cleanup code

| Item | Plan reference | Code |
|------|----------------|------|
| “Use existing monkeypatch patterns” | `plan.txt` §`python/test_ci_agentic_fix.py` (line 136) | ```1049:1049:python/test_ci_agentic_fix.py``` stubs `_apply_known_harness_fix` entirely |
| Mixed-failure scenario | `plan.txt` §Mixed failure bullet (line 134) | Test checks rollback+delegate on verify matrix, **not** that partition rewrite ran or was rolled back |

**Effect:** the regression guards orchestration only; a broken or over-broad `_apply_finalize_cleanup_partition_fix` can still pass. This matches the rejected OOS note in implement `55C91B5E` (`OOS_CR2_8`: single-job mixed fixture; wanted stronger multi-job signal).

---

### 3. `lint_applied_ever` tests rely on broad helper monkeypatching

| Item | Plan reference | Code |
|------|----------------|------|
| “Prefer monkeypatching … where helpful” | `plan.txt` §`python/test_review_and_fix.py` (line 191) | ```2096:2101:python/test_review_and_fix.py``` patches `_run_lint_fix_loop`, `_lint_fix_delta_paths`, `_commit_lint_fix_delta_paths`, porcelain, snapshot |
| OOS_3 regression intent | `plan.txt` line 186 | Asserts commit count == 0, but never runs real `_lint_loop_successful_break` integration without stubs |

**Effect:** the test proves the **gate** when `_run_lint_fix_loop` returns `no-changes`, but a regression that drops the `lint_applied_ever` check inside `_lint_loop_successful_break` while leaving stubs unchanged could still be missed if someone only stubs at the loop boundary.

**Mitigating factor:** production guard is simple and localized at ```1773:1775:python/review_and_fix.py```.

---

### 4. Cleanup rewrite itself is **not** a proactive broad rewrite (good)

| Item | Plan reference | Code |
|------|----------------|------|
| Incident-scoped partition fix | `plan.txt` §Partition helper constraints (lines 94-104) | ```181:223:python/ci_agentic_fix.py``` — signature-gated, single target, in-place `-k` substitution, tab guard, no-op when already fixed |
| Legacy-prefix scope | `plan.txt` §Legacy-prefix helper constraints (lines 81-88) | Only auto-fixes `python/preflight.py` |

**Scope discipline on production:** **pass**. No blanket Makefile or allow-list rewrite.

---

## Summary table

| Criterion | Meets plan? |
|-----------|-------------|
| Narrow partial-verification regression **specified** | Yes (`plan.txt` mixed-failure bullet) |
| Regression **before** cleanup code change | **No** (file order + no TDD sequencing) |
| Proactive cleanup rewrite | **No** (partition fix is signature- and line-scoped) |
| Blanket monkeypatch weakens test | **Yes** (`_apply_known_harness_fix` stub in mixed-failure test; broad stubs in lint-fix tests) |

---

## Recommendations (plan-only; no edits)

1. Add an explicit **implementation sequencing** bullet: land `test_run_cycle_mixed_mechanical_failure_rolls_back_then_delegates` (or a stricter two-fixable-job variant) **before** `_apply_finalize_cleanup_partition_fix`, and require the test to call the **real** helper (not stub `_apply_known_harness_fix`).
2. For OOS_3, add sequencing: `test_step5_lint_fix_no_changes_without_applied_lint_does_not_commit` **before** `_lint_loop_successful_break` / `lint_applied_ever` production change; narrow monkeypatch surface (avoid stubbing `_commit_lint_fix_delta_paths` when testing the gate).
3. Tighten `plan.txt` line 191 from “prefer monkeypatching … where helpful” to **named, minimal** stubs per case so implementers cannot stub the unit under test.

If you meant a different **OOS_3** (e.g. duplicate-code parity in `536A41B2` or Item 3 in `5AE8D621`), say which issue/run log and I can re-review that plan slice the same way.
## Reviewer stderr (<TMPDIR>/plan-review/round-1/dyn-cursor-plan-cleanup-test-first.txt.diag)

(empty: <TMPDIR>/plan-review/round-1/dyn-cursor-plan-cleanup-test-first.txt.diag)

## Failed-agent stderr tail (<TMPDIR>/plan-review/round-1/dyn-cursor-plan-cleanup-test-first.txt.stderr-tail)

(file missing: <TMPDIR>/plan-review/round-1/dyn-cursor-plan-cleanup-test-first.txt.stderr-tail)

## Launcher stderr (<TMPDIR>/plan-review/round-1/dyn-cursor-plan-cleanup-test-first.txt.launch-stderr)

⏳ cursor agent: still running (1m elapsed)
⏳ cursor agent: still running (2m elapsed)
⏳ cursor agent: still running (3m elapsed)
⏳ cursor agent: still running (4m elapsed)
⏳ cursor agent: still running (5m elapsed)
⏳ cursor agent: still running (6m elapsed)
✓ cursor agent: completed (exit code 0, output 7789 bytes)
  ```
### In-Scope Findings

1. **Important** — `risk-integration` — `larch-logs/design/BD9CFCF6-95EC-49B8-B0BD-7A3DCF227885/composed-plan.md:350`  
   What: The acceptance bullet says the lint-fix delta commit uses `git add -- <path>`, but the detailed plan requires `git add --pathspec-from-file` and `git-commit.sh --only --pathspec-from-file` at `larch-logs/design/BD9CFCF6-95EC-49B8-B0BD-7A3DCF227885/composed-plan.md:147-151`.  
   Concrete breakage path: an implementer following the acceptance bullet can break the existing pathspec contract pinned by `python/test_review_and_fix.py:2134-2155` and the workflow contract in `scripts/git-commit.md:5`.  
   Suggested fix: change the acceptance bullet to say **pathspec-file staging and `--only --pathspec-from-file` commit**, not `git add -- <path>`.

2. **Important** — `risk-integration` — `larch-logs/design/BD9CFCF6-95EC-49B8-B0BD-7A3DCF227885/composed-plan.md:147-158`  
   What: The plan starts `_lint_fix_delta_paths` from accumulated `unioned_delta_paths`, but does not say to filter those paths against the **current** dirty state before writing the pathspec.  
   Concrete breakage path: if one lint-fix attempt reports a new path in `LINT_FIX_DELTA_PATHS` and a later attempt removes or reverts it before checks pass, `python/review_and_fix.py:1788-1794` can still feed the stale path into `_commit_lint_fix_delta_paths`; `git add --pathspec-from-file` at `python/review_and_fix.py:1157-1163` can then fail on a path that no longer exists.  
   Suggested fix: specify that `_lint_fix_delta_paths` must filter accumulated `LINT_FIX_DELTA_PATHS` to paths that still differ from `pre_lint_head` or appear in current porcelain, then sort.

### Out-of-Scope Observations

1. **Nit** — `risk-integration` — `python/review_and_fix.py:1741-1743`, `python/review_and_fix.py:1791-1794`  
   What: `LINT_FIX_DELTA_PATHS` is comma-joined and comma-split, so repo paths containing commas can be split into invalid pathspec entries.  
   Suggested fix: use a sidecar pathspec file or another lossless encoding if this field ever becomes a public workflow envelope.  
   Why out of scope: the current plan only needs internal Step 5 plumbing, and existing tests do not cover comma-containing paths.
## Reviewer stderr (<TMPDIR>/plan-review/round-1/dyn-codex-plan-lint-delta.txt.diag)

(file missing: <TMPDIR>/plan-review/round-1/dyn-codex-plan-lint-delta.txt.diag)

## Failed-agent stderr tail (<TMPDIR>/plan-review/round-1/dyn-codex-plan-lint-delta.txt.stderr-tail)

(file missing: <TMPDIR>/plan-review/round-1/dyn-codex-plan-lint-delta.txt.stderr-tail)

## Launcher stderr (<TMPDIR>/plan-review/round-1/dyn-codex-plan-lint-delta.txt.launch-stderr)

⏳ codex agent: still running (1m elapsed)
⏳ codex agent: still running (2m elapsed)
⏳ codex agent: still running (3m elapsed)
⏳ codex agent: still running (4m elapsed)
⏳ codex agent: still running (5m elapsed)
✓ codex agent: completed (exit code 0, output 2256 bytes)
  ```
### 1. Critical — In-place pre-dirty lint edits on `no-changes` still skip post-loop commit

**Plan bullets:** Edge cases § “Two pre-dirty tracked files, one lint-touched” (`plan.txt:292`); Failure modes § “pre-lint per-path snapshot path closes that gap” (`plan.txt:305`); Tests § “edited in place … without appearing in `delta_paths`” (`plan.txt:179`).

**Issue:** `checks.run_lint_fix` on a dirty baseline uses `_delta_paths_after_dispatch`, which only picks **new** tracked paths, not in-place edits to paths already in `baseline_tracked`. An in-place fix returns `status="no-changes"`, not `"applied"`:

```2040:2058:python/checks.py
        delta_paths = _delta_paths_after_dispatch(
            baseline_tracked,
            baseline_untracked,
            current_tracked,
            current_untracked,
        )
        if not delta_paths:
            return FixOutcome(
                status="no-changes",
                delta_paths=(),
                ...
            )
```

Step 5 only sets `lint_applied_ever` on `"applied"` and `_lint_loop_successful_break` bails out when it is false:

```1773:1775:python/review_and_fix.py
        def _lint_loop_successful_break(reason: str) -> tuple[str | None, str | None]:
            if not lint_applied_ever:
                return None, None
```

```1823:1828:python/review_and_fix.py
                if lint_status == "no-changes":
                    recheck = _run_relevant_checks_captured(implement_tmpdir)
                    if recheck.get("RELEVANT_CHECKS_SKIPPED") == "true" or recheck.get("RELEVANT_CHECKS_OK") == "true":
                        terminal, reason = _lint_loop_successful_break("no-changes-pass")
```

So `_lint_fix_delta_paths`’s `git diff --name-only <pre_lint_head>` walk (`plan.txt:147-149`, `review_and_fix.py:1148-1153`) never runs for the exact scenario the plan says the snapshot fixes. Porcelain can stay dirty through `complete` and stall at Step 8.

**Compatibility:** Matches accepted implement-run finding “Lint-fix `no-changes` path can miss in-place edits” (`larch-logs/implement/55C91B5E…/review-findings-full.jsonl`).

---

### 2. Important — Omitted `LINT_FIX_DELTA_PATHS` is only safe when `lint_applied_ever` is true

**Plan bullet:** Track and union `delta_paths` / `LINT_FIX_DELTA_PATHS` (`plan.txt:156`); `_lint_fix_delta_paths` starts from `unioned_delta_paths` then unions `git diff --name-only` (`plan.txt:147-149`).

**Behavior:**

- `_run_lint_fix_loop` omits the KV when `outcome.delta_paths` is empty (`review_and_fix.py:1742-1743`).
- The loop tolerates omission via `.get("LINT_FIX_DELTA_PATHS", "")` (`review_and_fix.py:1793`).
- Recovery for missed paths depends on `_lint_fix_delta_paths`’s HEAD diff walk (`review_and_fix.py:1148-1153`).

That recovery only runs inside `_lint_loop_successful_break`, which requires `lint_applied_ever` (`review_and_fix.py:1774-1780`). So omission is covered for `"applied"` iterations (including union + diff walk), but **not** for the `no-changes` in-place case above.

**Test gap:** `test_step5_lint_fix_commits_union_paths_before_complete` mocks `_lint_fix_delta_paths` and always supplies `LINT_FIX_DELTA_PATHS` (`test_review_and_fix.py:2020-2021`). No test exercises `applied` with the key omitted and the real helper.

---

### 3. Important — Plan-required end-to-end “two pre-dirty files” test is missing

**Plan bullet:** Tests § “Two pre-dirty tracked files: one edited in place … only the lint-touched path is staged/committed” (`plan.txt:179`).

**Shipped coverage:** Only a **unit** test of `_lint_fix_delta_paths` in isolation:

```2158:2176:python/test_review_and_fix.py
def test_lint_fix_delta_paths_excludes_unchanged_pre_dirty_file(tmp_path, monkeypatch):
    ...
    paths = review_and_fix._lint_fix_delta_paths(round_dir, "head", ())
    assert paths == ("linted.py",)
```

Gate-level tests monkeypatch `_lint_fix_delta_paths` and `_commit_lint_fix_delta_paths` (`test_review_and_fix.py:2021-2027`, `2099-2101`), so they do not prove `_step5_post_round_gates` end-to-end behavior for the plan scenario. Implement review flagged this as a coverage gap (`OOS_CR2_10` in `larch-logs/implement/55C91B5E…`).

**Compatibility:** Existing tests pass via mocks; regression risk for the real dirty-baseline path stays high.

---

### 4. Latent — Index-only lint deltas not enumerated in `_lint_fix_delta_paths`

**Plan bullet:** `_lint_fix_delta_paths` unions paths from `git diff --name-only <pre_lint_head>` (`plan.txt:148`).

**Issue:** Enumeration is worktree-vs-HEAD only (`review_and_fix.py:1148`). Index-only changes (wt matches `pre_lint_head`, index differs) may not appear in that diff while porcelain stays dirty. `_path_matches_pre_lint_snapshot` compares cached diffs (`review_and_fix.py:1134-1136`), but paths never enter the commit set if they are absent from the `git diff --name-only` loop.

**Compatibility:** Stall risk at Step 8, not a sweep-into-commit risk. Aligns with implement-run OOS finding on index-only deltas (`OOS_CR3_9`).

---

### 5. Latent — Empty `commit_paths` after `lint_applied_ever` completes without stall

**Plan bullets:** Stall when commit fails and tree dirty (`plan.txt:159`, `plan.txt:307`); no-op when nothing to commit (`plan.txt:293`).

**Issue:** When `lint_applied_ever` is true, porcelain is non-empty, but `_lint_fix_delta_paths` returns `()`, `_lint_loop_successful_break` returns `(None, None)` without stalling:

```1780:1782:python/review_and_fix.py
            commit_paths = _lint_fix_delta_paths(result.round_dir, pre_lint_head, tuple(sorted(lint_delta_paths)))
            if not commit_paths:
                return None, None
```

The loop then breaks to `complete` with a dirty tree. Plan failure mode 307 expects `lint-fix-commit-failed` for commit failures, not silent completion with residual dirt.

---

### 6. OK — Pre-lint dirty snapshot capture matches plan

**Plan bullet:** Before lint loop when porcelain non-empty, call `_write_pre_lint_snapshot` (`plan.txt:155`).

**Implementation:** Snapshot is written only when porcelain is non-empty; `pre_lint_head` is bound (`review_and_fix.py:1769`). `_write_pre_lint_snapshot` captures head, tracked paths, and per-path wt/index patches (`review_and_fix.py:1101-1124`). Unchanged pre-dirty files are excluded via `_path_matches_pre_lint_snapshot` (`review_and_fix.py:1151-1152`), consistent with plan edge case (`plan.txt:291-292`).

---

### 7. OK — Deterministic ordering matches plan

**Plan bullet:** “Deduplicate and sort” (`plan.txt:150`).

**Implementation:** `lint_delta_paths` passed as `tuple(sorted(lint_delta_paths))` (`review_and_fix.py:1780`); helper returns `tuple(sorted(paths))` (`review_and_fix.py:1154`). Pathspec file order follows sorted tuple (`review_and_fix.py:1159`).

---

### 8. Partial — Commit-message contract preserved in code, lightly tested

**Plan bullet:** `_commit_lint_fix_delta_paths` — “same contract as before: pathspec file, `git add --pathspec-from-file`, `git-commit.sh --only --pathspec-from-file`” (`plan.txt:151`).

**Implementation:**

```1157:1171:python/review_and_fix.py
def _commit_lint_fix_delta_paths(round_num: int, round_dir: Path, commit_paths: tuple[str, ...], reason: str) -> str:
    ...
    msg = f"Address lint fixes after review round {round_num}: {reason}"
    commit = _run([
        str(_plugin_root() / "scripts" / "git-commit.sh"),
        "--only",
        "--pathspec-from-file",
        str(stage_file),
        "-m",
        msg,
    ])
```

`_lint_loop_successful_break` passes reason tokens (`cap-success`, `recheck-pass`, `no-changes-pass`, etc.) at `review_and_fix.py:1798-1826`.

**Gaps:** Only `test_commit_lint_fix_delta_paths_uses_pathspec_file` hits the real commit helper, with `reason="recheck-pass"` (`test_review_and_fix.py:2146`). No test asserts the full message template or other reason suffixes. Gate tests mock `_commit_lint_fix_delta_paths`, so message preservation is not regression-locked at the gate level.

---

### 9. OK — Workflow envelope / stall-recovery compatibility for new bail tokens

**Plan bullets:** `config.py` SSOT for `lint-fix-commit-failed` and `resume-handoff-commit-failed` (`plan.txt:191-195`); `step5-review-branches.md` stall table (`plan.txt:204-208`).

**Implementation:** Tokens are in `config.LINT_FIX_BAIL_REASON_TOKENS` (`config.py:99-105`). Tests derive parametrization from that tuple (`test_stall_recovery.py:702-713`). `lint-fix-commit-failed` propagates: gate → loop → `_emit_step5_envelope("stall", …, stall_reason, …)` (`review_and_fix.py:1785`, `2862-2863`). `step5-review-branches.md:11` lists both tokens under Tool Failures and durable bail set.

**Minor envelope note:** `FILES_CHANGED_HINT` still comes from `result.coder.commit_sha`, not the lint-fix post-loop commit (`review_and_fix.py:2874`). Pre-existing; lint-only deltas may not flip the hint even after a successful lint commit.

---

## Plan vs implementation matrix

| Concern | Plan intent | Step 5 behavior | Match? |
|--------|-------------|-----------------|--------|
| Omitted `LINT_FIX_DELTA_PATHS` | Union + HEAD diff walk | Works when `lint_applied_ever` | Partial |
| Pre-dirty unchanged files | Snapshot exclude | `_path_matches_pre_lint_snapshot` | Yes |
| Pre-dirty in-place lint edit | Snapshot include | Blocked by `no-changes` + `lint_applied_ever` | **No** |
| Deterministic ordering | Sort | `sorted()` at union + return | Yes |
| Commit message | pathspec + `-m` with reason | Implemented; lightly tested | Partial |
| `lint-fix-commit-failed` stall | Durable bail | Wired through envelope + config | Yes |

---

## Test / workflow compatibility risks

1. **All current gate tests mock `_lint_fix_delta_paths`** — they validate orchestration wiring, not snapshot semantics (`test_review_and_fix.py:2005-2130`).
2. **Plan-mandated e2e “two pre-dirty files” test absent** — plan `plan.txt:179`; only helper unit test at `test_review_and_fix.py:2158-2176`.
3. **`test_step5_lint_fix_no_changes_without_applied_lint_does_not_commit`** correctly guards the `lint_applied_ever` gate (`test_review_and_fix.py:2084-2106`), but also encodes that snapshot-diverged paths on `no-changes-pass` will **not** commit even if the mock helper would return paths.
4. **Stall-recovery / Step 5 branch docs** — aligned for `lint-fix-commit-failed`; no breaking envelope change for existing `STEP5_REVIEW_STATUS=stall` consumers.
5. **`checks` tests** do not cover dirty-baseline in-place edit → Step 5 commit path; `test_checks.py` `no-changes` cases are empty-log / launcher-failure scenarios (`test_checks.py:912-932`, `2040-2063`).

---

## Bottom line

The snapshot machinery and pathspec commit path are implemented as specified for the **`applied` + dirty baseline** path. The plan’s central dirty-baseline guarantee (in-place lint on a pre-dirty tracked file that never appears in `delta_paths` / `LINT_FIX_DELTA_PATHS`) is **not** satisfied because `checks.run_lint_fix` surfaces that work as `no-changes`, and plan bullet 160 prevents post-loop commit when `lint_applied_ever` is false. Until that interaction is resolved (e.g. snapshot-divergence commit on `no-changes-pass`, or `run_lint_fix` reporting snapshot-diverged paths as `applied`), plan bullets `plan.txt:179`, `plan.txt:292`, and `plan.txt:305` overstate what Step 5 actually does.
## Reviewer stderr (<TMPDIR>/plan-review/round-1/dyn-cursor-plan-lint-delta.txt.diag)

(empty: <TMPDIR>/plan-review/round-1/dyn-cursor-plan-lint-delta.txt.diag)

## Failed-agent stderr tail (<TMPDIR>/plan-review/round-1/dyn-cursor-plan-lint-delta.txt.stderr-tail)

(file missing: <TMPDIR>/plan-review/round-1/dyn-cursor-plan-lint-delta.txt.stderr-tail)

## Launcher stderr (<TMPDIR>/plan-review/round-1/dyn-cursor-plan-lint-delta.txt.launch-stderr)

⏳ cursor agent: still running (1m elapsed)
⏳ cursor agent: still running (2m elapsed)
⏳ cursor agent: still running (3m elapsed)
✓ cursor agent: completed (exit code 0, output 12970 bytes)
  ```
### In-Scope Findings

1. **Important** — `correctness` — `python/review_and_fix.py:933-938`, `python/review_and_fix.py:2031-2042`, `python/review_and_fix.py:3047-3065`  
   What: The **since-committed** path still stages untracked files against the **pre-coder** baseline, not a post-commit or handoff baseline. Plan bullet: `larch-logs/design/058F6917-3DE7-4955-8257-B7EFE9700FA2/composed-plan.md:87-91`, especially the full-mode untracked rule at line 89. Concrete failing scenario: after a coder round commits and writes `post-coder-head.txt`, an unrelated `scratch.txt` appears before Step 7. `commit-fixes --stage-all` calls `_collect_round_stage_paths(..., since_committed=True)`, which still includes `scratch.txt` via `_round_coder_untracked_delta_paths`, then `git add --pathspec-from-file` stages it. Suggested fix: add an explicit since-committed untracked baseline rule, or skip/fail untracked paths in since-committed mode unless they are proven review deltas.

2. **Important** — `correctness` — `python/review_and_fix.py:887-932`, `python/review_and_fix.py:2016-2024`  
   What: An **empty** `pre-coder-head.txt` is treated as an existing head-only snapshot, then `_round_diff_base` returns empty and `_collect_round_stage_paths` falls back to all current tracked paths. Plan bullet: `larch-logs/design/058F6917-3DE7-4955-8257-B7EFE9700FA2/composed-plan.md:35-43`, which classifies by file existence only and never handles zero-byte/corrupt heads. Concrete failing scenario: a zero-byte `pre-coder-head.txt` plus unrelated dirty `notes.md` reaches a successful no-op coder. The no-changes gate sees `notes.md` as a stage path, and `_stage_and_commit_round` can commit it. Suggested fix: require a non-empty head for `full` and `head_untracked`; otherwise fail closed or treat it as missing before staging. Do not let empty-head snapshots use the all-tracked fallback.

### Out-of-Scope Observations

1. **Latent** — `risk-integration` — `python/review_and_fix.py:928-938`  
   What: The explicit **missing mode** fallback still returns all tracked and untracked paths, matching the plan bullet at `larch-logs/design/058F6917-3DE7-4955-8257-B7EFE9700FA2/composed-plan.md:91` and `:257`. Current production callers mostly guard it via `_ensure_pre_coder_snapshot` and full-snapshot filtering, so this is only a direct-helper or future-caller hazard. Suggested fix: keep the legacy fallback only behind a clearly named legacy path, or return empty/fail closed for commit staging.
## Reviewer stderr (<TMPDIR>/plan-review/round-1/dyn-codex-plan-stage-scope.txt.diag)

(file missing: <TMPDIR>/plan-review/round-1/dyn-codex-plan-stage-scope.txt.diag)

## Failed-agent stderr tail (<TMPDIR>/plan-review/round-1/dyn-codex-plan-stage-scope.txt.stderr-tail)

(file missing: <TMPDIR>/plan-review/round-1/dyn-codex-plan-stage-scope.txt.stderr-tail)

## Launcher stderr (<TMPDIR>/plan-review/round-1/dyn-codex-plan-stage-scope.txt.launch-stderr)

⏳ codex agent: still running (1m elapsed)
⏳ codex agent: still running (2m elapsed)
⏳ codex agent: still running (3m elapsed)
⏳ codex agent: still running (4m elapsed)
⏳ codex agent: still running (5m elapsed)
✓ codex agent: completed (exit code 0, output 2504 bytes)
  ```
### In-Scope Findings

- **correctness** `python/review_and_fix.py:928-938` — **Plan bullet** (OOS_1, lines 29–33 in `plan.txt`): remove tracked/untracked whole-tree fallback for `mode == "missing"`. **Current code** still calls `_capture_round_tracked_paths()` / `_capture_round_untracked_paths()` when `mode` is not `full`/`head_untracked` or `diff_base` is empty. That is the direct staging leak the plan targets; the planned edit is minimal and correctly scoped. **Suggested fix:** Implement as written; no extra helpers needed.

- **correctness** `python/review_and_fix.py:887-896` — **Plan bullet** (line 37): `since_committed=True` should use `post-coder-head.txt` only when present and non-empty. **Edge case** (line 127): empty/missing `post-coder-head.txt` must not fall back to whole-tree capture. The plan’s only guard is `_round_diff_base(...) == ""` (lines 26–27), but `_round_diff_base` **falls through to `pre-coder-head.txt`** when post is missing/empty. With a valid `pre_head`, `diff_base` is non-empty, so the early guard does not run and `_collect_review_fix_stage_paths` (line 2042) can still union stale `git diff <pre_head>` paths into Step 7 / `--stage-all` (FINDING_9 class). **Suggested fix:** Add an explicit `since_committed` guard in `_collect_round_stage_paths` (or tighten `_round_diff_base`) so missing/empty post returns `[]`; add an OOS_1 test for this case.

- **correctness** `python/test_review_and_fix.py` (no test yet) — **Plan bullets** (lines 72–79, 127): OOS_1 tests cover missing snapshot and empty `pre-coder-head.txt`, but **not** `since_committed=True` with empty/missing `post-coder-head.txt`. Without that test, the pre_head fallback gap above can regress. **Suggested fix:** Add a test mirroring the missing-snapshot pattern: full snapshot + valid `pre_head`, no/empty `post-coder-head.txt`, monkeypatched whole-tree helpers, assert `[]`.

- **correctness** `python/test_review_and_fix.py` (no dedicated OOS_1 test) — **Plan bullet** (line 128): preserve head-only scoped attempt behavior. OOS_1 tests do not assert `head_untracked` staging still uses attempt-relative deltas only; coverage relies on older tests (e.g. `test_apply_findings_with_coder_head_untracked_preserves_staged_carryover`). **Suggested fix:** Optional small unit test: head-only round, pre-existing dirty carryover, assert `_collect_round_stage_paths(round_dir)` does not include carryover and does not call whole-tree capture.

- **correctness** `python/review_and_fix.py:2040-2041` — **Not in OOS_1 plan text**, but affects staging surface: `_collect_review_fix_stage_paths` skips rounds without a **full** pre-coder snapshot. Head-only MAV rounds never reach `since_committed=True` collection here (see `test_collect_review_fix_stage_paths_skips_head_only_mav_round`). That avoids MAV whole-tree sweeps but means head-only review deltas are **not** staged via `--stage-all`; per-round commit (`python/review_and_fix.py:2118`) still uses head_untracked attempt logic. **Suggested fix:** Confirm this tradeoff is acceptable; no code change required for OOS_1 if intentional.

- **correctness** `python/review_and_fix.py:631-647` + `python/review_and_fix.py:2042` — **Plan bullet** (lines 34–37): full + `since_committed` scoped behavior is preserved and already has regression coverage (`test_collect_round_stage_paths_excludes_pre_dirty_unrelated_since_committed`). **Residual leak:** paths that differ from `post-coder-head` and **fail** `_path_matches_pre_coder_snapshot` against `pre-coder-head` can still be staged (e.g. new unrelated edits after post-coder commit). The plan does not narrow this further; it is outside OOS_1’s missing/empty/fallback scope. **Suggested fix:** Accept for this plan, or add a separate intersect-with-wt-vs-HEAD filter (out of scope for minimal OOS_1).

- **correctness** `python/review_and_fix.py:1139-1154` — **Plan OOS_2** (lines 46–53): `_lint_fix_delta_paths` unconditionally re-scans `git diff --name-only pre_lint_head` and can sweep unreported dirty paths into lint commits. Plan change is minimal and correct. **Suggested fix:** Implement OOS_2 as written; unrelated dirty paths on the lint path are covered there, not in OOS_1.

- **correctness** `python/review_and_fix.py:680-684` — **Plan bullet** (line 36): `head_untracked` uses `_round_attempt_tracked_delta_paths`. Paths dirty vs `diff_base` **outside** `attempt-pre-tracked-paths.txt` are always included. That is intentional for coder-introduced dirt, but a tracked file that was clean at attempt capture and later dirtied externally during the coder window could still be staged on per-round commit (`python/review_and_fix.py:2118`). The plan does not change this. **Suggested fix:** Out of OOS_1 scope unless you want attempt-window external-edit exclusion.

### Out-of-Scope Observations

| Case | Plan coverage | Staging risk after plan |
|------|---------------|-------------------------|
| **Missing snapshot** | Covered (lines 26–33, 72–75, 125) | Closed: `[]` instead of whole-tree |
| **Empty `pre-coder-head.txt`** | Covered (lines 26–27, 76–79, 126) | Closed via `_round_diff_base` → `""` |
| **Full snapshot** | Covered (lines 35, 34–38) | Scoped deltas; snapshot exclusion unchanged |
| **Head-only (`head_untracked`)** | Covered (lines 36, 128) | Per-round scoped; `--stage-all` skips via `python/review_and_fix.py:2040-2041` |
| **`since_committed=True` with valid post** | Covered (lines 37, 80–82) | Pre-dirty exclusion tested; see residual leak above |
| **`since_committed=True` without post** | **Incomplete** (line 37 vs lines 26–27) | **Still leaks** via `python/review_and_fix.py:889-895` pre_head fallback |

**Minimal-change assessment:** OOS_1 is appropriately small (one function, two new unit tests). The one addition needed for full baseline-case coverage is a **`since_committed` post-head guard** (a few lines, no new helpers), plus its test. OOS_2 and OOS_3 are orthogonal but necessary for lint and cleanup verification paths.
## Reviewer stderr (<TMPDIR>/plan-review/round-1/dyn-cursor-plan-stage-scope.txt.diag)

(empty: <TMPDIR>/plan-review/round-1/dyn-cursor-plan-stage-scope.txt.diag)

## Failed-agent stderr tail (<TMPDIR>/plan-review/round-1/dyn-cursor-plan-stage-scope.txt.stderr-tail)

(file missing: <TMPDIR>/plan-review/round-1/dyn-cursor-plan-stage-scope.txt.stderr-tail)

## Launcher stderr (<TMPDIR>/plan-review/round-1/dyn-cursor-plan-stage-scope.txt.launch-stderr)

⏳ cursor agent: still running (1m elapsed)
⏳ cursor agent: still running (2m elapsed)
⏳ cursor agent: still running (3m elapsed)
⏳ cursor agent: still running (4m elapsed)
✓ cursor agent: completed (exit code 0, output 6789 bytes)
  ```
