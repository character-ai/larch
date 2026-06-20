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

REVIEWER_FILE=<TMPDIR>/plan-review/round-1/dyn-cursor-plan-self-review-fallback.txt|TOOL=cursor|STATUS=NOT_SUBSTANTIVE|EXIT_CODE=0|FAILURE_REASON=structured records not found after repair

## Reviewer output (<TMPDIR>/plan-review/round-1/dyn-cursor-plan-self-review-fallback.txt)

Reviewing self-review fallback in fluff-analysis and audit-runs: locating implementation and tracing empty, missing, malformed, and non-self-review tally handling.
**Verdict:** On current `main`, there is **no self-review fallback** in `/fluff-analysis` or `/audit-runs`. Neither consumer reads `code-review-tally.json` or synthesizes tally-derived rows. Self-review runs with nonzero `accepted_count`/`rejected_count` and an empty `review-findings-full.jsonl` stay invisible to both tools.

---

## Symbols inspected

| Area | Files / symbols |
|------|-----------------|
| **fluff-analysis** | `skills/fluff-analysis/scripts/fluff-analysis.py`: `extract`, `_extract_implement`, `_extract_one_implement_run`, `render`, `threeway`, `parse_impl_tsv`; contract `skills/fluff-analysis/scripts/fluff-analysis.md`; harness `skills/fluff-analysis/scripts/test-fluff-analysis.sh` |
| **audit-runs** | `python/audit_runs.py`: `scan_run_main`, `_iter_ndjson`, `_category_string`, `_mangled_rows`, `_CANONICAL`, `compute_counters_main`, `_scan_required` (`cond("step5")`); `.claude/skills/audit-runs/SKILL.md`; `python/test_audit_runs.py` |
| **Producer** | `python/review_and_fix.py`: `write_self_review_tally`; `docs/run-logs.md` (self-review carve-out) |

---

## Scenario matrix (current behavior)

| Case | fluff-analysis | audit-runs `category-stats` |
|------|----------------|------------------------------|
| **Empty JSONL** (self-review sentinel: file exists, 0 lines) | `read_text(jf).splitlines()` yields nothing → **0 records**; tally ignored | `is_file()` true, `rows=[]` → all counters **0**, `partial_data: false` |
| **Missing JSONL** | Early return at `if not os.path.exists(jf)` → **0 records** | `partial_data: true`, `partial_reason: missing_review_findings_jsonl` |
| **Malformed JSONL** | Bad lines skipped (`except ValueError: continue`); valid lines kept; **no tally fallback** | `partial_data: true`, `partial_reason: malformed_review_findings_jsonl` |
| **Non-self-review tally** (`mode: hard`/`simple`, JSONL populated) | Normal JSONL path; tally unused (OK) | Normal JSONL aggregation (OK) |
| **Non-self-review tally, empty/missing JSONL** | Same blind spot as self-review | Same: zeros or partial; tally unused |

---

## Findings


- **Step design Step 3 — collect-results codex NOT_SUBSTANTIVE failed (exit 0)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/plan-review/round-1/dyn-codex-plan-self-review-fallback.txt|TOOL=codex|STATUS=NOT_SUBSTANTIVE|EXIT_CODE=0|FAILURE_REASON=structured records not found after repair

## Reviewer output (<TMPDIR>/plan-review/round-1/dyn-codex-plan-self-review-fallback.txt)

Found missing fallback in both consumers.

**Findings**

- **High: `fluff-analysis` drops self-review tally counts.**  
  `write_self_review_tally` writes `code-review-tally.json` with `mode: self-review` and may write an empty `review-findings-full.jsonl`. Docs say self-review counts come from tally fields, not JSONL. But `_extract_one_implement_run` only reads `review-findings-full.jsonl`. Missing JSONL returns no records. Empty JSONL returns no records. Malformed JSONL lines are skipped. `code-review-tally.json` is never read, so accepted/rejected self-review counts are lost.  
  **Paths:** `python/review_and_fix.py:3186-3234`, `docs/run-logs.md:324-334`, `skills/fluff-analysis/scripts/fluff-analysis.py:337-393`.

- **High: `audit-runs` also lacks the self-review tally fallback.**  
  `scan_run_main` reads only `review-findings-full.jsonl` into `rows`. `category-stats` is computed only from those rows. Empty JSONL emits zero counts. Missing implement JSONL emits `partial_data=true`. Malformed JSONL emits partial zero stats. No code path validates `code-review-tally.json`, checks `mode == "self-review"`, or synthesizes count-only rows from `accepted_count` / `rejected_count`.  
  **Paths:** `python/audit_runs.py:681-812`, `python/audit_runs.py:841-868`, `.claude/skills/audit-runs/SKILL.md:241`.

- **Medium: synthetic rows are not present, so counts are not recovered.**  
  The current code does not invent canonical categories, but only because it synthesizes nothing. `_CANONICAL`, `_category_string`, and `_mangled_rows` only classify real JSONL rows. A fix should keep self-review synthetic rows out of canonical clean-category totals.  
  **Paths:** `python/audit_runs.py:22`, `python/audit_runs.py:586-603`, `python/audit_runs.py:803-812`.

- **Medium: consumer tests do not cover the fallback cases.**  
  Producer tests prove self-review tally writes empty JSONL with nonzero counts. `fluff-analysis` fixtures use JSONL rows only. `audit-runs` tests cover JSONL category stats and malformed JSONL, but not empty, missing, malformed, or non-self-review tally fallback behavior.  
  **Paths:** `python/test_review_and_fix.py:736-782`, `skills/fluff-analysis/scripts/test-fluff-analysis.sh:53-98`, `skills/fluff-analysis/scripts/test-fluff-analysis.sh:131-222`, `python/test_audit_runs.py:455-489`, `python/test_audit_runs.py:600-614`.

**Inspected symbols**

- **`skills/fluff-analysis/scripts/fluff-analysis.py`**: `_extract_one_implement_run`, `parse_impl_tsv`, `render`.
- **`python/audit_runs.py`**: `scan_run_main`, `_iter_ndjson`, `_category_string`, `_mangled_rows`, `_scan_required`, `compute_counters_main`.
- **`python/review_and_fix.py`**: `write_self_review_tally`.
- **`python/voting.py`**: `_validate_tally_args`, `compose_tally_record`.
- **Docs/tests**: `docs/run-logs.md`, `.claude/skills/audit-runs/SKILL.md`, `python/test_audit_runs.py`, `python/test_review_and_fix.py`, `skills/fluff-analysis/scripts/test-fluff-analysis.sh`.

**Tests**

- **Not run.** This was a read-only review.
## Reviewer stderr (<TMPDIR>/plan-review/round-1/dyn-codex-plan-self-review-fallback.txt.diag)

(file missing: <TMPDIR>/plan-review/round-1/dyn-codex-plan-self-review-fallback.txt.diag)

## Failed-agent stderr tail (<TMPDIR>/plan-review/round-1/dyn-codex-plan-self-review-fallback.txt.stderr-tail)

(file missing: <TMPDIR>/plan-review/round-1/dyn-codex-plan-self-review-fallback.txt.stderr-tail)

## Launcher stderr (<TMPDIR>/plan-review/round-1/dyn-codex-plan-self-review-fallback.txt.launch-stderr)

⏳ codex agent: still running (1m elapsed)
⏳ codex agent: still running (2m elapsed)
✓ codex agent: completed (exit code 0, output 3031 bytes)
  ```

- **Step design Step 3 — collect-results codex NOT_SUBSTANTIVE failed (exit 0)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/plan-review/round-1/dyn-cursor-plan-duplicate-code-ci-phase2.txt|TOOL=codex|STATUS=NOT_SUBSTANTIVE|EXIT_CODE=0|FAILURE_REASON=structured records not found after repair

## Reviewer output (<TMPDIR>/plan-review/round-1/dyn-cursor-plan-duplicate-code-ci-phase2.txt)

No findings.

**Verified:**
- **Makefile split:** `py-lint` runs `py-lint-main` and `py-typecheck`; **R0801** is isolated in `py-lint-duplicate-code`. See `Makefile:36-63`.
- **CI split:** `python-lint` runs `make py-lint-main`; `python-pyright` runs `make py-typecheck`. See `.github/workflows/ci.yaml:555-593`.
- **Dedicated R0801 CI path:** separate workflow job `python-lint-duplicate-code` runs `make py-lint-duplicate-code`. It does not run `make py-typecheck` or setup Node. See `.github/workflows/duplicate-code.yaml:23-42`.
- **CLI wiring:** `lint duplicate-code` dispatches to `duplicate_code.duplicate_code_main`. See `python/cli.py:164-165`.
- **Runner symbols inspected:** `run_duplicate_code`, `_find_commonalities`, `_clusters_from_commonalities`, `_render_digest`, `_render_findings`, `duplicate_code_main`. See `python/duplicate_code.py:252-282`, `303-318`, `422-481`, `515-531`.
- **Parity tests:** serial vs parallel assertions compare structured `digest`, `exit_code`, `pair_count`, and spans. They do not depend on Pylint prose. See `python/test_duplicate_code.py:294-378`, `380-393`, `465-475`, `526-535`.
- **Local CI fixer wiring:** `python-lint-duplicate-code` maps to `make py-lint-duplicate-code`, and its toolchain check requires only `pylint`, not `pyright`. See `python/ci_monitor.py:783-788`, `794-810`; tests at `python/test_ci_monitor.py:1076-1109`.

**Note:** the duplicate-code workflow still installs shared `python/requirements-dev.txt`, which includes `pyright`. That is install overhead only, not duplicated pyright execution. See `python/requirements-dev.txt:1-4`.

**Tests not run:** read-only review only.
## Reviewer stderr (<TMPDIR>/plan-review/round-1/dyn-cursor-plan-duplicate-code-ci-phase2.txt.diag)

(file missing: <TMPDIR>/plan-review/round-1/dyn-cursor-plan-duplicate-code-ci-phase2.txt.diag)

## Failed-agent stderr tail (<TMPDIR>/plan-review/round-1/dyn-cursor-plan-duplicate-code-ci-phase2.txt.stderr-tail)

(file missing: <TMPDIR>/plan-review/round-1/dyn-cursor-plan-duplicate-code-ci-phase2.txt.stderr-tail)

## Launcher stderr (<TMPDIR>/plan-review/round-1/dyn-cursor-plan-duplicate-code-ci-phase2.txt.launch-stderr)

⏳ codex agent: still running (1m elapsed)
✓ codex agent: completed (exit code 0, output 1647 bytes)
  ```

- **Step design Step 3 — collect-results codex NOT_SUBSTANTIVE failed (exit 0)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/plan-review/round-1/dyn-codex-plan-duplicate-code-ci.txt|TOOL=codex|STATUS=NOT_SUBSTANTIVE|EXIT_CODE=0|FAILURE_REASON=structured records not found after repair

## Reviewer output (<TMPDIR>/plan-review/round-1/dyn-codex-plan-duplicate-code-ci.txt)

Found **2 issues**.

**Findings**

- **[P2] R0801 runner still redoes serial similarity work.**  
  `run_duplicate_code()` computes pair commonalities and clusters through `_find_commonalities()` at `python/duplicate_code.py:263-270`, but `_exit_code_like_pylint()` then calls `checker.close()` at `python/duplicate_code.py:450-452`. In Pylint 4.0.5, that close path recomputes similarities through the checker. This undercuts the Makefile claim that the path parallelizes pair comparisons without `_iter_sims` pre-scan, `Makefile:55-63`. The parity guard only spies `_find_commonalities()` and restores `_iter_sims` before close, so it does not catch the second serial pass, `python/test_duplicate_code.py:396-440`.

- **[P3] Duplicate-code CI still installs pyright.**  
  The dedicated workflow runs only `make py-lint-duplicate-code`, `.github/workflows/duplicate-code.yaml:38-42`, but it installs `python/requirements-dev.txt`, `.github/workflows/duplicate-code.yaml:31-37`. That file includes `pyright==1.1.409`, `python/requirements-dev.txt:1-3`. So the job avoids running `make py-typecheck`, but it still duplicates pyright install/cache work. Use a Pylint-only requirements file if the goal is no unrelated pyright work.

**Verified**

- **CI split:** `python-lint` runs `make py-lint-main`, `.github/workflows/ci.yaml:555-574`.  
- **Pyright split:** `python-pyright` runs `make py-typecheck`, `.github/workflows/ci.yaml:576-593`.  
- **R0801 CI path:** `python-lint-duplicate-code` runs on `push: main` and `workflow_dispatch`, `.github/workflows/duplicate-code.yaml:8-25`.  
- **Local mapping:** `ci_monitor.per_job_command()` maps `python-lint-duplicate-code` to `make py-lint-duplicate-code`, `python/ci_monitor.py:783-788`.  
- **Tool verification:** duplicate-code local replay checks only `pylint`, not `pyright`, `python/ci_monitor.py:803-810`.  
- **Parity tests:** the serial/parallel parity cases compare exit codes and normalized digests, not Pylint prose, `python/test_duplicate_code.py:294-390` and `python/test_duplicate_code.py:465-534`.

**Tests**

- **Not run.** Read-only review.
## Reviewer stderr (<TMPDIR>/plan-review/round-1/dyn-codex-plan-duplicate-code-ci.txt.diag)

(file missing: <TMPDIR>/plan-review/round-1/dyn-codex-plan-duplicate-code-ci.txt.diag)

## Failed-agent stderr tail (<TMPDIR>/plan-review/round-1/dyn-codex-plan-duplicate-code-ci.txt.stderr-tail)

(file missing: <TMPDIR>/plan-review/round-1/dyn-codex-plan-duplicate-code-ci.txt.stderr-tail)

## Launcher stderr (<TMPDIR>/plan-review/round-1/dyn-codex-plan-duplicate-code-ci.txt.launch-stderr)

⏳ codex agent: still running (1m elapsed)
⏳ codex agent: still running (2m elapsed)
✓ codex agent: completed (exit code 0, output 2109 bytes)
  ```

- **Step design Step 3 — collect-results codex NOT_SUBSTANTIVE failed (exit 0)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/plan-review/round-1/dyn-cursor-plan-orchestrator-recovery-phase2.txt|TOOL=codex|STATUS=NOT_SUBSTANTIVE|EXIT_CODE=0|FAILURE_REASON=structured records not found after repair

## Reviewer output (<TMPDIR>/plan-review/round-1/dyn-cursor-plan-orchestrator-recovery-phase2.txt)

Found **1 issue**.

**Findings**

- **Medium: implement recovery probes are not implement-specific.**  
  **Where:** `skills/implement/SKILL.md:46`, `skills/shared/orchestrator-never.md:9-11`, and implement long-running fences at `skills/implement/SKILL.md:500-504`, `604-610`, `632-650`, `690-694`, `733-737`, `788-796`.  
  **Issue:** `/implement` NEVER #8 permits one foreground terminal-sentinel probe, but it only gives a design-shaped example, `.completed/step-3-terminal`. The shared rule lists only design sentinels and `DESIGN_TMPDIR`. I found no implement-specific terminal sentinel names for Step 3, Step 5, Step 6, Step 7a, or Step 8.  
  **Impact:** On a premature empty notification during `/implement`, the operator cannot tell which foreground sentinel probe is allowed. That ambiguity may push them toward forbidden fallbacks: Monitor, `ps`, result-file reads, or background waiters.  
  **Fix:** Add concrete implement sentinel names and probe forms for each long-running implement fence, or state that `/implement` has no sentinel recovery path and must end the turn until the real `<task-notification>` arrives.

**Loophole check**

- **Monitor:** Banned in `/implement` NEVER #8. See `skills/implement/SKILL.md:46`.
- **Background waiters:** Banned in `/implement` and shared rules. See `skills/implement/SKILL.md:46` and `skills/shared/orchestrator-never.md:9-11`.
- **`ps` polling:** Banned by the shared rule’s absent-sentinel recovery path. See `skills/shared/orchestrator-never.md:9`.
- **Mechanical guard note:** `scripts/hook-bg-poll-guard.sh:71-98` and `273-328` only recognize design steps and `DESIGN_TMPDIR`, so it does not make implement recovery guidance concrete.

**Inspected**

- `skills/implement/SKILL.md`: NEVER #8 and long-running fences.
- `skills/shared/orchestrator-never.md`: shared NEVER #3 and #4.
- `scripts/hook-bg-poll-guard.sh`: `marker_step_completed`, `bash_is_step3_recovery_waiter`, `bash_is_terminal_sentinel_foreground_probe`.
- `scripts/hook-bg-poll-guard.md`: recovery-contract docs.
- `scripts/test-implement-anti-polling-rule.sh`: literal coverage.
## Reviewer stderr (<TMPDIR>/plan-review/round-1/dyn-cursor-plan-orchestrator-recovery-phase2.txt.diag)

(file missing: <TMPDIR>/plan-review/round-1/dyn-cursor-plan-orchestrator-recovery-phase2.txt.diag)

## Failed-agent stderr tail (<TMPDIR>/plan-review/round-1/dyn-cursor-plan-orchestrator-recovery-phase2.txt.stderr-tail)

(file missing: <TMPDIR>/plan-review/round-1/dyn-cursor-plan-orchestrator-recovery-phase2.txt.stderr-tail)

## Launcher stderr (<TMPDIR>/plan-review/round-1/dyn-cursor-plan-orchestrator-recovery-phase2.txt.launch-stderr)

⏳ codex agent: still running (1m elapsed)
✓ codex agent: completed (exit code 0, output 2111 bytes)
  ```

- **Step design Step 3 — collect-results codex NOT_SUBSTANTIVE failed (exit 0)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/plan-review/round-1/dyn-codex-plan-orchestrator-recovery.txt|TOOL=codex|STATUS=NOT_SUBSTANTIVE|EXIT_CODE=0|FAILURE_REASON=structured records not found after repair

## Reviewer output (<TMPDIR>/plan-review/round-1/dyn-codex-plan-orchestrator-recovery.txt)

Found **one issue**.

## Findings

- **P1: `/implement` premature-notification recovery is not implement-specific enough.**  
  `skills/implement/SKILL.md:46` permits only one foreground terminal-sentinel probe, but the example sentinel is design-only: `.completed/step-3-terminal`. It also says `scripts/hook-bg-poll-guard.sh` denies the background waiter. That hook is explicitly `/design`-scoped and only recognizes design markers and `$DESIGN_TMPDIR` sentinels: `scripts/hook-bg-poll-guard.sh:71-97`, `scripts/hook-bg-poll-guard.sh:273-287`, `scripts/hook-bg-poll-guard.sh:430-441`, and `scripts/hook-bg-poll-guard.md:5,16-20`.  
  The implement long-running fences do not name equivalent `$IMPLEMENT_TMPDIR` terminal sentinels: Step 3 checks at `skills/implement/SKILL.md:500-504`, Step 5 review at `skills/implement/SKILL.md:604-610`, Step 5 resume at `skills/implement/SKILL.md:647-655`, Step 7a at `skills/implement/SKILL.md:733-739`, and Step 8 ship at `skills/implement/SKILL.md:788-795`. Shared guidance also names only the design sentinels and `$DESIGN_TMPDIR`: `skills/shared/orchestrator-never.md:9-11`.  
  **Impact:** a compliant `/implement` orchestrator has no concrete allowed probe target after a premature empty notification. This can strand recovery or push agents toward ad-hoc `ps`, Monitor, or result-file probes despite the ban.  
  **Fix:** either define and document per-implement terminal sentinels for each long-running fence, or state that `/implement` has no foreground-probe exception and must end the turn until the platform re-fires `<task-notification>`. Also qualify the hook-denial claim as design-only unless the hook is extended.

## Checked

- **NEVER #8:** `skills/implement/SKILL.md:46`.
- **Shared NEVER #3/#4:** `skills/shared/orchestrator-never.md:9-11`.
- **Hook symbols:** `marker_step_completed`, `bash_is_step3_recovery_waiter`, `bash_is_terminal_sentinel_foreground_probe`.
- **Harness coverage:** `scripts/test-hook-bg-poll-guard.sh:130-235`, `scripts/test-implement-anti-polling-rule.sh:89-131`.

## Notes

- The shared prose does ban **Monitor fallback**, **ps polling**, and **background waiters**.
- The remaining gap is **implement-specific sentinel guidance**.
- **Tests not run.** Read-only review only.
## Reviewer stderr (<TMPDIR>/plan-review/round-1/dyn-codex-plan-orchestrator-recovery.txt.diag)

(file missing: <TMPDIR>/plan-review/round-1/dyn-codex-plan-orchestrator-recovery.txt.diag)

## Failed-agent stderr tail (<TMPDIR>/plan-review/round-1/dyn-codex-plan-orchestrator-recovery.txt.stderr-tail)

(file missing: <TMPDIR>/plan-review/round-1/dyn-codex-plan-orchestrator-recovery.txt.stderr-tail)

## Launcher stderr (<TMPDIR>/plan-review/round-1/dyn-codex-plan-orchestrator-recovery.txt.launch-stderr)

⏳ codex agent: still running (1m elapsed)
⏳ codex agent: still running (2m elapsed)
✓ codex agent: completed (exit code 0, output 2262 bytes)
  ```
### FINDING_1: Self-review fallback is not implemented in fluff-analysis
- **Severity**: blocker
- **Concern**: `_extract_one_implement_run` is JSONL-only. It returns immediately when `review-findings-full.jsonl` is missing, and when the file exists but is empty (self-review sentinel) it produces zero implement records. There is no read of `code-review-tally.json`, no `mode == "self-review"` branch, and no synthetic row emission. Baselines (`render` → `threeway` on `i_all`) under-count self-review runs with real tally counts.
- **Evidence**:

```337:339:skills/fluff-analysis/scripts/fluff-analysis.py
    jf = os.path.join(run_dir, "review-findings-full.jsonl")
    if not os.path.exists(jf):
        return records
```

```348:359:skills/fluff-analysis/scripts/fluff-analysis.py
    for line in read_text(jf).splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            data = json.loads(line)
        except ValueError:
            continue
        phase = data.get("phase", "")
        outcome = data.get("outcome", "") or ""
        if phase == "retroactive-backfill" or not outcome:
            continue
```

- **Suggested revision**: After JSONL parse, if `rows` is empty and `code-review-tally.json` has `mode: "self-review"` with valid nonnegative integers, append synthetic records (`outcome: accepted` × `accepted_count`, `outcome: rejected` × `rejected_count`) with **empty `category`** and generic prose (no canonical category injection). Gate on tally `mode`, not merely empty JSONL.

---

### FINDING_2: Self-review fallback is not implemented in audit-runs category-stats
- **Severity**: blocker
- **Concern**: `scan_run_main` always derives `category-stats` from JSONL via `_iter_ndjson`. Empty self-review sentinel JSONL yields `canonical=0`, `blank=0`, `mangled=0` with `partial_data: false`, so cumulative `OOS_CATEGORIES_*` counters miss self-review volume. `compute_counters_main` only treats **missing** JSONL as a special partial case; empty sentinel is not partial and tally is never consulted.
- **Evidence**:

```803:812:python/audit_runs.py
    # category-stats
    if (run_dir/"review-findings-full.jsonl").is_file():
        if jsonl_err:
            _json_line({"scan":"category-stats","pr":pr,"partial_data":True,"partial_reason":"malformed_review_findings_jsonl",...})
        else:
            mangled=mangled_cache if mangled_cache is not None else _mangled_rows(rows)
            _json_line({"scan":"category-stats","pr":pr,"partial_data":False,"canonical":sum(1 for r in rows if _category_string(r) in _CANONICAL),...})
    else:
        if args.skill=="design": ...
        else: _json_line({"scan":"category-stats","pr":pr,"partial_data":True,"partial_reason":"missing_review_findings_jsonl",...})
```

```859:862:python/audit_runs.py
            elif r.get("scan")=="category-stats":
                if r.get("partial_data") is True: partial=True
                if not (r.get("partial_data") is True and "review-findings-full.jsonl not found" in str(r.get("detail") or "")):
                    dc+=num_or_zero(r.get("canonical")); db+=num_or_zero(r.get("oos_blank"))
```

- **Suggested revision**: When JSONL is empty/malformed/missing **and** tally is `mode: self-review` with valid counts, emit synthetic blank rows for `accepted_count + rejected_count` (category `""` only). Do **not** increment `canonical` or `mangled`. For panel runs (`mode` not `self-review`), keep today’s JSONL-only / partial semantics.

---

### FINDING_3: Empty sentinel is indistinguishable from “no findings” in fluff-analysis
- **Severity**: important
- **Concern**: Producer intentionally writes empty JSONL for self-review (`write_self_review_tally` at `python/review_and_fix.py:3220-3221`). Without tally fallback, fluff-analysis cannot distinguish “review ran, 3 accepted” from “no JSONL rows at all.” This was logged as OOS follow-up for #4618.
- **Evidence**: `python/review_and_fix.py:3189-3221`; `larch-logs/design/3FF362C2-A58C-45EB-8FCB-B4DDE88F6E1A/execution-issues.md` (requirements row citing `fluff-analysis.py:337-350` and `audit_runs.py:804-809`).

---

### FINDING_4: Malformed JSONL does not fall back to tally
- **Severity**: important
- **Concern**: fluff-analysis drops malformed lines and never consults tally. audit-runs sets `category-stats` `partial_data: true` on any JSONL parse error and emits zero counters. A self-review run with corrupt JSONL but valid `code-review-tally.json` still loses recoverable counts in both consumers.
- **Evidence**: fluff `354-355`; audit `805-806`, `681`.

---

### FINDING_5: Non-self-review runs with tally but no JSONL are also uncovered
- **Severity**: latent
- **Concern**: Fallback logic must be gated on `tally["mode"] == "self-review"`. Panel runs (`hard`/`simple`) with missing JSONL should remain partial/error, not synthesize from tally (tally counts are cumulative JSONL derivatives per `docs/run-logs.md:317-322`). Any implementation that keys only on “empty JSONL” would mis-handle panel anomalies.
- **Evidence**: `docs/run-logs.md:317-334`; `python/voting.py:766` (`allowed_modes = {"simple", "hard", "self-review"}`).

---

### FINDING_6: No regression coverage for consumer self-review paths
- **Severity**: important
- **Concern**: `skills/fluff-analysis/scripts/test-fluff-analysis.sh` has no self-review / tally fixture. `python/test_audit_runs.py` has `category-stats` tests for malformed/non-string categories but nothing for `mode: self-review` + empty JSONL + nonzero tally. The requested edge cases are unenforced.
- **Evidence**: harness ends at line 235 with no self-review block; `test_audit_runs.py` grep shows no `self-review` / `code-review-tally` tests.

---

### FINDING_7: Contract docs omit tally fallback (accurate today, misleading if fallback lands)
- **Severity**: nit
- **Concern**: `skills/fluff-analysis/scripts/fluff-analysis.md:18-19` lists only JSONL + TSV inputs. No mention of `code-review-tally.json` self-review recovery. Operators reading docs after a fallback lands would not know the contract changed.
- **Evidence**: `fluff-analysis.md:18-27`; `.claude/skills/audit-runs/SKILL.md:241` documents `CATEGORY_STATS_PARTIAL` but not self-review tally synthesis.

---

## Synthetic-row / canonical-category check

**Cannot pass on `main`.** No code synthesizes rows from tally. Therefore:

- Count recovery from `accepted_count`/`rejected_count` does not happen.
- Canonical category invention is moot (nothing is synthesized).
- A correct implementation should use **blank** `category`, generic IDs (e.g. `SELF_REVIEW_ACCEPTED_1`), and `reviewer_slots: ["main-agent"]` or similar, without mapping into `_CANONICAL` (`code-quality`, `risk-integration`, `correctness`, `architecture`, `security`).

---

## What already works (producer / other consumers)

- **Tally write path**: `write_self_review_tally` writes nonempty `code-review-tally.json` and empty JSONL sentinel (`python/review_and_fix.py:3220-3244`).
- **Final report**: `_derive_review_line` handles self-review zero case (`python/final_report.py:330-331`); nonzero uses generic `N/M accepted`.
- **audit-runs Step 5 detection**: `cond("step5")` accepts `code-review-tally.json` OR `review-findings-full.jsonl` (`python/audit_runs.py:522-523`), so self-review runs are not flagged as “review skipped” for required-file presence.

---

## Summary

The **self-review consumer fallback described in the review prompt is absent** on `main`. Both fluff-analysis and audit-runs are JSONL-primary; empty self-review sentinel files produce zero findings and zero category stats despite documented nonzero tally semantics in `docs/run-logs.md:324-334`. Implement tally-gated synthetic rows (blank category only), add harness tests for empty / missing / malformed JSONL and non-self-review tally guardrails, then update `fluff-analysis.md` and audit-runs SKILL counter docs.
## Reviewer stderr (<TMPDIR>/plan-review/round-1/dyn-cursor-plan-self-review-fallback.txt.diag)

(empty: <TMPDIR>/plan-review/round-1/dyn-cursor-plan-self-review-fallback.txt.diag)

## Failed-agent stderr tail (<TMPDIR>/plan-review/round-1/dyn-cursor-plan-self-review-fallback.txt.stderr-tail)

(file missing: <TMPDIR>/plan-review/round-1/dyn-cursor-plan-self-review-fallback.txt.stderr-tail)

## Launcher stderr (<TMPDIR>/plan-review/round-1/dyn-cursor-plan-self-review-fallback.txt.launch-stderr)

❌ cursor agent: FAILED (exit code 1, output 0 bytes)
✓ cursor agent: completed (exit code 0, output 303 bytes)
⏳ cursor agent: still running (1m elapsed)
⏳ cursor agent: still running (2m elapsed)
⏳ cursor agent: still running (3m elapsed)
✓ cursor agent: completed (exit code 0, output 10745 bytes)
  ```
