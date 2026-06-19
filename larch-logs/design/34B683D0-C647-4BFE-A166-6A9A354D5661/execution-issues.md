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

- **Step review Step 2 — cursor-review failed (exit 1 — unknown — auth-retries=2, transient-retries=1)**:
  ```
===== sidecar.history =====
===== cursor auth attempt diag =====
Error: Password not found for account 'cursor-user' and service 'cursor-refresh-token'
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
Error: Password not found for account 'cursor-user' and service 'cursor-refresh-token'
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

- **Step design Step 3 — collect-results codex NOT_SUBSTANTIVE failed (exit 0)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/plan-review/round-1/dyn-cursor-plan-contract-preservation-phase2.txt|TOOL=codex|STATUS=NOT_SUBSTANTIVE|EXIT_CODE=0|FAILURE_REASON=structured records not found after repair

## Reviewer output (<TMPDIR>/plan-review/round-1/dyn-cursor-plan-contract-preservation-phase2.txt)


- **Step design Step 3 — collect-results codex NOT_SUBSTANTIVE failed (exit 0)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/plan-review/round-1/dyn-codex-plan-contract-preservation.txt|TOOL=codex|STATUS=NOT_SUBSTANTIVE|EXIT_CODE=0|FAILURE_REASON=structured records not found after repair

## Reviewer output (<TMPDIR>/plan-review/round-1/dyn-codex-plan-contract-preservation.txt)

Found **3 missing parity-test gaps** in `larch-logs/design/CB785C9E-0FB5-4786-A95B-2231738432D8/plan.txt`.

**Findings:**

- **[P1] Exact gather KV envelope is not pinned.**
  - **Plan bullet:** `python/test_review_dispatch.py` only says to “assert output files and KVs exist.” `larch-logs/design/CB785C9E-0FB5-4786-A95B-2231738432D8/plan.txt:148-151`
  - **Contract:** retired `scripts/gather-branch-context.sh` emits exactly four KV rows: `DIFF_FILE`, `FILE_LIST_FILE`, `COMMIT_LOG_FILE`, `COMMIT_COUNT`. `scripts/gather-branch-context.sh:69-73`
  - **Gap:** Add a parity test for exact key set, row count, values under the output dir, and no extra stdout rows.

- **[P1] Collector failure sidecar section order and placeholders are under-tested.**
  - **Plan bullet:** failure-log tests list scenarios, but do not require exact section order or placeholder text. `larch-logs/design/CB785C9E-0FB5-4786-A95B-2231738432D8/plan.txt:155-169`
  - **Contract:** retired composer writes ordered sections for structured record, reviewer output, `.diag`, `.stderr-tail`, and `.launch-stderr`, with exact missing/empty/no-path placeholders. `scripts/compose-collector-failure-log.sh:48-75`
  - **Gap:** Add golden-output parity for section headings, order, empty reviewer-file behavior, missing-file placeholders, and tail sidecar handoff paths.

- **[P2] Wait final diagnostics are named in the plan but not pinned.**
  - **Plan bullet:** implementation must “keep compact stderr progress and final summary diagnostics.” `larch-logs/design/CB785C9E-0FB5-4786-A95B-2231738432D8/plan.txt:53-72`
  - **Contract:** retired wait helper emits final stderr summaries after machine rows: timeout count or all-complete duration. `scripts/wait-for-reviewers.sh:154-174`
  - **Gap:** Add parity tests for the exact timeout summary and all-complete summary diagnostics, separate from the `DONE` / `TIMEOUT` stdout rows.

**Note:** I did not find `LARCH_FINAL_SUMMARY_BEGIN` / `LARCH_FINAL_SUMMARY_END` marker output in these three retired helpers, so I have no marker-specific finding for this plan.
## Reviewer stderr (<TMPDIR>/plan-review/round-1/dyn-codex-plan-contract-preservation.txt.diag)

(file missing: <TMPDIR>/plan-review/round-1/dyn-codex-plan-contract-preservation.txt.diag)

## Failed-agent stderr tail (<TMPDIR>/plan-review/round-1/dyn-codex-plan-contract-preservation.txt.stderr-tail)

(file missing: <TMPDIR>/plan-review/round-1/dyn-codex-plan-contract-preservation.txt.stderr-tail)

## Launcher stderr (<TMPDIR>/plan-review/round-1/dyn-codex-plan-contract-preservation.txt.launch-stderr)

⏳ codex agent: still running (1m elapsed)
⏳ codex agent: still running (2m elapsed)
⏳ codex agent: still running (3m elapsed)
⏳ codex agent: still running (4m elapsed)
⏳ codex agent: still running (5m elapsed)
⏳ codex agent: still running (6m elapsed)
⏳ codex agent: still running (7m elapsed)
✓ codex agent: completed (exit code 0, output 2088 bytes)
  ```

- **Step design Step 3 — collect-results codex NOT_SUBSTANTIVE failed (exit 0)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/plan-review/round-1/dyn-cursor-plan-cutover-risk-phase2.txt|TOOL=codex|STATUS=NOT_SUBSTANTIVE|EXIT_CODE=0|FAILURE_REASON=body too thin: 22/30 words after stripping fenced code

## Reviewer output (<TMPDIR>/plan-review/round-1/dyn-cursor-plan-cutover-risk-phase2.txt)

**Findings:** None.

**Result:** I found no launcher, Python import, or prompt `.sh` reference that appears to dangle after the planned deletion sequence.
## Reviewer stderr (<TMPDIR>/plan-review/round-1/dyn-cursor-plan-cutover-risk-phase2.txt.diag)

(file missing: <TMPDIR>/plan-review/round-1/dyn-cursor-plan-cutover-risk-phase2.txt.diag)

## Failed-agent stderr tail (<TMPDIR>/plan-review/round-1/dyn-cursor-plan-cutover-risk-phase2.txt.stderr-tail)

(file missing: <TMPDIR>/plan-review/round-1/dyn-cursor-plan-cutover-risk-phase2.txt.stderr-tail)

## Launcher stderr (<TMPDIR>/plan-review/round-1/dyn-cursor-plan-cutover-risk-phase2.txt.launch-stderr)

⏳ codex agent: still running (1m elapsed)
⏳ codex agent: still running (2m elapsed)
⏳ codex agent: still running (3m elapsed)
⏳ codex agent: still running (4m elapsed)
⏳ codex agent: still running (5m elapsed)
✓ codex agent: completed (exit code 0, output 154 bytes)
  ```

- **Step design Step 3 — collect-results codex NOT_SUBSTANTIVE failed (exit 0)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/plan-review/round-1/dyn-codex-plan-cutover-risk.txt|TOOL=codex|STATUS=NOT_SUBSTANTIVE|EXIT_CODE=0|FAILURE_REASON=structured records not found after repair

## Reviewer output (<TMPDIR>/plan-review/round-1/dyn-codex-plan-cutover-risk.txt)


- **Step design Step 3 — collect-results cursor NOT_SUBSTANTIVE failed (exit 0)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/plan-review/round-1/dyn-cursor-plan-tmpdir-security.txt|TOOL=cursor|STATUS=NOT_SUBSTANTIVE|EXIT_CODE=0|FAILURE_REASON=structured records not found after repair

## Reviewer output (<TMPDIR>/plan-review/round-1/dyn-cursor-plan-tmpdir-security.txt)

Searching the codebase for tmpdir validation, path-safety checks, and related plan references.
**Verdict:** Several **SECURITY.md** tmpdir contracts are met in bash wrappers and core validators, but **Python plan/design entry points still write artifacts or quiet logs before allowlist validation**, and **`pause-load` never validates `--design-tmpdir`**.

---

## Coverage summary

| Area | Status |
|------|--------|
| Core allowlist validator (`validate_design_tmpdir`) | Present; canonical prefix walk, `..`/control-char rejection, symlink-to-file rejection |
| Bash quiet wrappers (step3-mav, stage-terminal, failure-report) | Validate before `larch_quiet_init` |
| `plan validate` log routing for disallowed tmpdir | Falls back to system temp log (tested) |
| `pause-save` allowlist | Routed through validator |
| Symlink dir rejection | **Inconsistent** across callers |
| Evidence token safety (plan commands) | `_unsafe_token` blocks tier-3 dry-run on metacharacters |
| Validation-before-logging (Python) | **Gaps** in multiple `plan_quality` / `session_env` / `decompose` entry points |

---

## Findings


- **Step design Step 3 — collect-results codex NOT_SUBSTANTIVE failed (exit 0)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/plan-review/round-1/dyn-codex-plan-tmpdir-security.txt|TOOL=codex|STATUS=NOT_SUBSTANTIVE|EXIT_CODE=0|FAILURE_REASON=structured records not found after repair

## Reviewer output (<TMPDIR>/plan-review/round-1/dyn-codex-plan-tmpdir-security.txt)

### In-Scope Findings

1. **Important** — security — `python/design_pause.py:272-273`, `python/design_pause.py:407-412`  
   **What:** `pause_load_main` creates `--design-tmpdir` before validating it, then installs restored artifacts into that path without calling `validate_design_tmpdir`. This misses the plan’s tmpdir guard coverage from `larch-logs/implement/6E3EED73-D852-48E6-86E9-8C776053D455/plan-goals-test.md:22` and the load/save guard scope at `plan-goals-test.md:11`.  
   **Concrete failing scenario:** invoke `design pause-load --design-tmpdir /tmp/link-to-unrelated-dir ...` where the path is a symlinked directory. Line 273 accepts or creates the path, then lines 407-412 copy `manifest.json`, `run-params.json`, and other restored files through it.  
   **Suggested fix:** validate `--design-tmpdir` before `mkdir`, use the canonical resolved path, reject symlinked leaves/ancestors for load, and return `LOAD_OK=false ERROR=tmpdir-not-allowed` before any write.

2. **Important** — security — `python/design_pause.py:407-412`  
   **What:** the restore install step does not reject pre-existing symlinks or special files inside the destination tmpdir before `copytree` / `copy2`. This leaves a gap in the plan’s restored-path safety bullet at `larch-logs/implement/6E3EED73-D852-48E6-86E9-8C776053D455/plan-goals-test.md:20`.  
   **Concrete failing scenario:** if `$DESIGN_TMPDIR/manifest.json` or a nested restored target is a symlink, `shutil.copy2` can overwrite the symlink target during resume after the snapshot has already passed validation.  
   **Suggested fix:** preflight the destination tree before install. Refuse symlink or non-regular target leaves, reject symlinked directories, and copy only after canonical destination containment is proven for every restored artifact.

**Tests not run:** read-only review.
## Reviewer stderr (<TMPDIR>/plan-review/round-1/dyn-codex-plan-tmpdir-security.txt.diag)

(file missing: <TMPDIR>/plan-review/round-1/dyn-codex-plan-tmpdir-security.txt.diag)

## Failed-agent stderr tail (<TMPDIR>/plan-review/round-1/dyn-codex-plan-tmpdir-security.txt.stderr-tail)

(file missing: <TMPDIR>/plan-review/round-1/dyn-codex-plan-tmpdir-security.txt.stderr-tail)

## Launcher stderr (<TMPDIR>/plan-review/round-1/dyn-codex-plan-tmpdir-security.txt.launch-stderr)

⏳ codex agent: still running (1m elapsed)
⏳ codex agent: still running (2m elapsed)
⏳ codex agent: still running (3m elapsed)
⏳ codex agent: still running (4m elapsed)
⏳ codex agent: still running (5m elapsed)
⏳ codex agent: still running (6m elapsed)
⏳ codex agent: still running (7m elapsed)
✓ codex agent: completed (exit code 0, output 1857 bytes)
  ```
### F1 — HIGH: `pause-load` writes before allowlist validation

**Plan bullet:** SECURITY.md **`/design` `--design-tmpdir` allowlist`** (L185); **`/design` pause/resume marker binding`** (L134–L166) — restore installs into caller tmpdir.

**File:** `python/design_pause.py`

`pause_load_main` calls `mkdir` on the caller-supplied path immediately, with **no** `validate_design_tmpdir` anywhere on the load path (save validates at L167; load does not).

```272:273:python/design_pause.py
    design_tmpdir = Path(parsed["--design-tmpdir"])
    design_tmpdir.mkdir(parents=True, exist_ok=True)
```

Later, restored snapshot files are copied into that directory (L407–L412). A misconfigured orchestrator can create directories and install pause artifacts **outside** `${XDG_CACHE_HOME}/larch/sessions/`, `$TMPDIR`, or `/tmp` before any allowlist gate runs.

**Gap vs tests:** `test_pause_save_rejects_non_allowlisted_tmpdir` covers save (Guard 6); **no load-path allowlist test** exists.

---

### F2 — HIGH: `design publish` never validates `--design-tmpdir`

**Plan bullet:** SECURITY.md **`/design` `--design-tmpdir` allowlist`** (L185).

**File:** `python/design_publish.py`

The publish path resolves the tmpdir and writes session artifacts with **no** `validate_design_tmpdir` call:

```160:182:python/design_publish.py
    design_tmpdir = Path(parsed["--design-tmpdir"]).resolve()
    ...
        _ = result_env.write_text("\n".join(f"{k}={v}" for k, v in kvs) + "\n", encoding="utf-8")
```

Early exits write `.design-publish-result.env` (L182, L204, L262); success path mutates `composed-plan.md` (L226–L228) and more. All of this can target a disallowed path.

---

### F3 — MEDIUM: Python `quiet_init` runs before tmpdir allowlist check

**Plan bullet:** SECURITY.md **`/design` `--design-tmpdir` allowlist`** (L185): *"validates the candidate path **before initializing quiet logging** so a disallowed existing `DESIGN_TMPDIR` cannot receive `larch-quiet-*.log` writes ahead of the allowlist check."*

**Root mechanism:** `python/logging_util.py` L65–L84 picks `DESIGN_TMPDIR` / `IMPLEMENT_TMPDIR` from the environment and **creates/appends** `larch-quiet-*.log` with no allowlist check.

**Call sites that invoke `quiet_init` before `validate_design_tmpdir`:**

| Function | `quiet_init` | `validate_design_tmpdir` |
|----------|-------------|--------------------------|
| `validate_plan_main` | L1010 | L1033 |
| `check_plan_size_main` | L1254 | L1259 |
| `auto_fix_plan_commands_main` | L1999 | L2014 |
| `revise_plan_with_waterfall_main` | L1524 | L1539 |
| `write_design_env_main` | L925 | L941 |
| `decompose.prepare_main` (and siblings) | L635 | L642 |

Example:

```1009:1033:python/plan_quality.py
def validate_plan_main(argv: list[str]) -> int:
    quiet_init(argv0="plan validate")
    ...
    design_tmpdir_raw = args.design_tmpdir or os.environ.get("DESIGN_TMPDIR", "")
    ...
    if design_tmpdir_raw:
        ok, _message = validate_design_tmpdir(design_tmpdir_raw)
```

**Amplifier:** `quiet_init` keys off **environment** `DESIGN_TMPDIR`, not necessarily the CLI `--design-tmpdir` being validated. A poisoned env can receive quiet-log writes even when the CLI arg would fail allowlist.

**Contrast (correct):** bash wrappers validate first:

```91:92:skills/design/scripts/design-step3-mav.sh
python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" session validate-design-tmpdir "$DESIGN_TMPDIR" || exit 2
larch_quiet_init
```

---

### F4 — MEDIUM: Symlink-directory rejection is inconsistent

**Plan bullet:** SECURITY.md **`/design` `--design-tmpdir` allowlist`** (L185): *"rejects existing non-directory leaves (including symlink-to-file leaves)"*; scope-anchor bullet (L113): *"readable regular non-symlink files"*.

**Core validator** allows a **symlink leaf that resolves to a directory**:

```745:751:python/session_env.py
    if cand.exists():
        if cand.is_symlink() and not cand.is_dir():
            return False, "design-tmpdir: leaf symlink must resolve to a directory"
        if not cand.is_dir():
            return False, "design-tmpdir: path must name a directory"
```

**Stricter callers** reject symlink directories outright:

```112:116:python/plan_review.py
    ok, message = validate_design_tmpdir(raw)
    if not ok:
        return False, message, path
    if path.is_symlink():
        return False, "design-tmpdir must not be a symlink", path
```

Same pattern in `finalize.kill_background_processes_main` (L811–L812). A symlinked `DESIGN_TMPDIR` can pass `validate_design_tmpdir` on paths that `plan-review preview`, step-3 flows, and kill-background reject.

---

### F5 — MEDIUM: `validate-plan-commands` writes log before path containment check

**Plan bullet:** SECURITY.md **`/design` `--design-tmpdir` allowlist`** (L185); plan-command validator trust boundary (L177).

**File:** `python/plan_quality.py`

`validate_plan_commands_main` calls `quiet_init` (L986), then writes to caller-supplied `--log-file` (L1004) with **no** containment check against a session root:

```985:1005:python/plan_quality.py
def validate_plan_commands_main(argv: list[str]) -> int:
    quiet_init(argv0="plan validate-commands")
    ...
    _atomic_write(Path(args.log_file), summary.log_text)
```

A caller supplying an absolute path outside the session tree gets an atomic write before any tmpdir validation (this subcommand has none).

---

### F6 — LOW: Evidence-token / cycle-key hygiene is mostly sound, one read-side gap

**Plan bullet:** SECURITY.md **plan-command validator auto-fix trust boundary** (L177); stall-recovery token vocabulary (L79–L83).

**Sound:**
- `_unsafe_token` (L780–L781) blocks `..`, shell metacharacters, etc. from tier-3 dry-run argv; defects are logged with redacted token label (L944–L946).
- `validator_autofix_main` sanitizes `cycle_key` with `[^A-Za-z0-9._-]` (L2316), keeping `.plan-command-autofix-{cycle_key}.attempted` under `design_tmpdir`.
- `stall_recovery._safe_token` (L127–L150) closes enum surfaces for escalation site/trigger/step/phase.

**Gap:** `VALIDATE_LOG_FILE` from the environment is hashed for `evidence_key` (L2312–L2315) **without** verifying the path is under `design_tmpdir` and non-symlink. Sanitization prevents path traversal in the filename, but a poisoned env can force a read of an arbitrary regular file for SHA-256 (read-side, not write-side).

```2311:2316:python/plan_quality.py
    evidence_key = f"{os.environ.get('VALIDATE_DEFECT_COUNT','unknown')}-..."
    validate_log_path = Path(validate_log) if validate_log else None
    if validate_log_path is not None and validate_log_path.is_file() and not validate_log_path.is_symlink():
        evidence_key = f"{evidence_key}-{_sha256_file(validate_log_path)}"
```

---

### F7 — LOW: Shell sentinel touch bypasses explicit allowlist in one branch

**Plan bullet:** SECURITY.md **`/design` `--design-tmpdir` allowlist`** (L185); `plan-review preview --variant step3` validates before sentinel touch.

**File:** `skills/design/scripts/design-step3-entry-preview.sh`

The allowlist gate (`_step3_entry_tmpdir_allowed`, L96–L100) guards the early-exit sentinel read (L101–L102), but the post-preview `touch` (L109–L110) checks only `-d "$DESIGN_TMPDIR"`, not `_step3_entry_tmpdir_allowed`:

```109:110:skills/design/scripts/design-step3-entry-preview.sh
if [[ -d "$DESIGN_TMPDIR" && "$_preview_out" == *'## Plan Candidate for Review'* ]]; then
  touch "$DESIGN_TMPDIR/.step3-entry-plan-printed" || true
```

In practice, `plan-review preview` validates before emitting that header (`plan_review.py` L526–L554), so exploitability is low. The shell branch is still weaker than the documented contract.

---

## What is working (no finding)

- **`validate_design_tmpdir`** (`session_env.py` L726–L763): absolute path, `..`/CRLF rejection, ancestor canonicalization, allowlist prefix check.
- **`pause-save` allowlist** (`design_pause.py` L167–L170).
- **`plan validate` log fallback** for disallowed `--design-tmpdir` (`plan_quality.py` L1036–L1043; tested in `test_validate_plan_uses_temp_log_for_disallowed_design_tmpdir`).
- **`pause-load` restore hardening** (rev-parse pin L329–L340, recovery-branch pin L310–L311, subtree rejection L363–L372, manifest cross-check L388–L403).
- **Implement tmpdir validation** (`checks.validate_tmpdir`, L185–L213): basename prefix, symlink rejection, canonical roots.
- **Bash quiet-init ordering** in `design-step3-mav.sh`, `design-stage-terminal-state.sh`, `design-failure-report.sh`.

---

## Recommended fix order (guidance only; Ask mode)

1. Add `validate_design_tmpdir` to **`pause_load_main`** before `mkdir` / restore install; add regression test mirroring save Guard 6.
2. Add allowlist validation to **`design_publish.py`** before any write.
3. Move **`quiet_init`** after `validate_design_tmpdir` in all `plan_quality` / `session_env` / `decompose` entry points; validate env `DESIGN_TMPDIR` when used as quiet-log target.
4. Align symlink-directory policy: either reject symlink leaves in `validate_design_tmpdir`, or document the intentional split.
5. Contain `--log-file` in `validate_plan_commands_main`; validate `VALIDATE_LOG_FILE` under `design_tmpdir` before hashing in `validator_autofix_main`.
## Reviewer stderr (<TMPDIR>/plan-review/round-1/dyn-cursor-plan-tmpdir-security.txt.diag)

(empty: <TMPDIR>/plan-review/round-1/dyn-cursor-plan-tmpdir-security.txt.diag)

## Failed-agent stderr tail (<TMPDIR>/plan-review/round-1/dyn-cursor-plan-tmpdir-security.txt.stderr-tail)

(file missing: <TMPDIR>/plan-review/round-1/dyn-cursor-plan-tmpdir-security.txt.stderr-tail)

## Launcher stderr (<TMPDIR>/plan-review/round-1/dyn-cursor-plan-tmpdir-security.txt.launch-stderr)

❌ cursor agent: FAILED (exit code 1, output 0 bytes)
⏳ cursor agent: still running (1m elapsed)
⏳ cursor agent: still running (2m elapsed)
⏳ cursor agent: still running (3m elapsed)
⏳ cursor agent: still running (4m elapsed)
✓ cursor agent: completed (exit code 0, output 10946 bytes)
  ```
### In-Scope Findings

1. **Important** **risk-integration**: `skills/design/SKILL.md:452-487` still names deleted `design-postplan-emit.sh` even though the G5 plan says Step 2b postplan now runs in-process through `python/cli.py design ...` and `postplan_emit_main`. `python/migrated-scripts.tsv:880-883` marks that wrapper and harness deleted, so this prompt/debug path may dangle after deletion. Relevant plan bullet: `docs/python-migration.md:173-175`. Fix the prompt and Python diagnostics at `python/design_lifecycle.py:2153-2160` to name `python/cli.py design postplan-emit` or `python/design_postplan.py`.

2. **Important** **correctness**: Gate C docs point at nonexistent `design-step4b-preview.sh`. `skills/design/SKILL.md:745-748` says `design-step3b-tail.sh` owns the combined tail, and `skills/design/scripts/design-step3b-tail.sh:113-117` directly calls `python/cli.py plan-review preview --variant gatec`, but `skills/design/SKILL.md:764-767` and `skills/design/references/approval-gates.md:193` still tell readers that `design-step4b-preview.sh` is invoked. The launcher would only map unmapped `.sh` names to `skills/design/scripts/$script` per `python/session_env.py:846-848`, so that basename dangles. Relevant plan bullet: `docs/python-migration.md:20`. Replace it with the actual tail wrapper or direct Python CLI entrypoint.

3. **Important** **risk-integration**: `skills/design/references/approval-gates.md:96` says `awaiting-continuation` runs only `plan-review-continuation.sh`, but that file is deleted in `python/migrated-scripts.tsv:1072-1075`. The live route is `design-step3-review.sh --phase awaiting-continuation` per `skills/design/references/approval-gates.md:86` and `skills/design/scripts/design-step3-review.sh:198`, with Python continuation registered at `python/cli.py` and implemented in `python/plan_review.py:1039-1040` / `python/plan_review.py:1561-1562`. Relevant plan bullet: `docs/python-migration.md:20`. Rewrite the stale basename to `python/cli.py plan-review continuation` or the owning Step 3 review wrapper path.
## Reviewer stderr (<TMPDIR>/plan-review/round-1/dyn-codex-plan-cutover-risk.txt.diag)

(file missing: <TMPDIR>/plan-review/round-1/dyn-codex-plan-cutover-risk.txt.diag)

## Failed-agent stderr tail (<TMPDIR>/plan-review/round-1/dyn-codex-plan-cutover-risk.txt.stderr-tail)

(file missing: <TMPDIR>/plan-review/round-1/dyn-codex-plan-cutover-risk.txt.stderr-tail)

## Launcher stderr (<TMPDIR>/plan-review/round-1/dyn-codex-plan-cutover-risk.txt.launch-stderr)

⏳ codex agent: still running (1m elapsed)
⏳ codex agent: still running (2m elapsed)
⏳ codex agent: still running (3m elapsed)
⏳ codex agent: still running (4m elapsed)
⏳ codex agent: still running (5m elapsed)
⏳ codex agent: still running (6m elapsed)
✓ codex agent: completed (exit code 0, output 2066 bytes)
  ```
### In-Scope Findings

1. **Important**; `risk-integration`; plan bullet `skills/implement/SKILL.md:874`; issue paths `skills/implement/references/stall-recovery.md:39-42`, `python/stall_recovery.py:433-448`, `scripts/test-implement-structure.sh:253-257`.
   **What:** The plan names the `BAIL_FAILURE_DETAIL_LOG` handoff, but there is no parity test pinning that Step 18a reads the value from `ship-pr-state.sh` and passes it as `--failure-detail-log`.
   **Breakage path:** A stalled run with only a detailed failure sidecar can classify from state-file text alone, because `python/stall_recovery.py` only reads the sidecar when the explicit flag is present.
   **Suggested fix:** Add a Step 18a structure or orchestration parity test that requires the exact read, validation, and `--failure-detail-log` classify argv.

2. **Important**; `risk-integration`; plan bullet `skills/implement/scripts/step-18.md:73-78`; issue paths `skills/implement/scripts/step-18.sh:213-241`, `skills/implement/scripts/test-step-18.sh:109-110`, `python/test_finalize.py:184-199`.
   **What:** The plan claims the Step 18 safety net uses exact log paths, but the wrapper test does not assert the `flush-safety-net` call or its `--log-root`, `--run-id`, and `--issue-log` paths.
   **Breakage path:** A future change can route the safety net to the wrong `larch-logs` root, omit `RUN_ID`, or move it after teardown without failing parity coverage.
   **Suggested fix:** Add a spy assertion for `log_root == $IMPLEMENT_TMPDIR/larch-logs`, `issue_log == $IMPLEMENT_TMPDIR/execution-issues.md`, and ordering before restore or teardown.

3. **Important**; `risk-integration`; plan bullet `skills/implement/scripts/step-18.md:91-97`; issue paths `python/finalize.py:924-939`, `skills/implement/scripts/test-step-18.sh:69-85`, `skills/implement/scripts/test-step-18.sh:208-214`.
   **What:** The teardown KV relay test only covers a subset of the real machine-readable rows.
   **Breakage path:** `STATUS`, `OUTCOME`, `LOG_WRITE_STATUS`, `REBASE_STATUS`, `FORCE_PUSH_STATUS`, `LOCAL_CLEANUP_STATUS`, or `VERIFY_MAIN_STATUS` can disappear from stdout while the Step 18 harness still passes.
   **Suggested fix:** Make the fake teardown emit the full `_emit_finalize_result` row set and assert every KV survives captured finalize stdout.

4. **Important**; `correctness`; plan bullet `skills/implement/scripts/step-18.md:52-66`; issue paths `python/final_report.py:564-590`, `python/test_final_report.py:35-39`, `skills/implement/scripts/test-step-18.sh:218-224`.
   **What:** There is no parity test for the `.step17-emitted` plus changed `summary-final.md` path where Step 18b must promote `EMIT_BODY=true` and print final-summary markers.
   **Breakage path:** A refreshed final summary after Step 17 top-chat emission can be silently skipped, even though `SNAPSHOT_OK` and marker emission are the contract protecting that update.
   **Suggested fix:** Add a test with a pre-existing summary, `.step17-emitted`, a changed rewritten summary, and assertions for `SNAPSHOT_OK=true`, `EMIT_BODY=true`, and one balanced marker pair.
## Reviewer stderr (<TMPDIR>/plan-review/round-1/dyn-cursor-plan-contract-preservation-phase2.txt.diag)

(file missing: <TMPDIR>/plan-review/round-1/dyn-cursor-plan-contract-preservation-phase2.txt.diag)

## Failed-agent stderr tail (<TMPDIR>/plan-review/round-1/dyn-cursor-plan-contract-preservation-phase2.txt.stderr-tail)

(file missing: <TMPDIR>/plan-review/round-1/dyn-cursor-plan-contract-preservation-phase2.txt.stderr-tail)

## Launcher stderr (<TMPDIR>/plan-review/round-1/dyn-cursor-plan-contract-preservation-phase2.txt.launch-stderr)

⏳ codex agent: still running (1m elapsed)
⏳ codex agent: still running (2m elapsed)
⏳ codex agent: still running (3m elapsed)
⏳ codex agent: still running (4m elapsed)
⏳ codex agent: still running (5m elapsed)
⏳ codex agent: still running (6m elapsed)
✓ codex agent: completed (exit code 0, output 3103 bytes)
  ```
