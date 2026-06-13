### FINDING_1:
- **Reviewer(s)**: Cursor-Arch, Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/research/references/research-phase.md:117-126
- **Concern**: Research Codex ingestion calls record-vendor-sidecar without a resolvable active-ledger root. Scenario: /research sets RESEARCH_TMPDIR but not IMPLEMENT_TMPDIR, DESIGN_TMPDIR, or SESSION_ENV_PATH. record_vendor_from_sidecar uses resolve_token_ledger_path, which only checks those keys (python/tokens.py:348-357). The planned record-vendor-sidecar step is still a no-op, so Item 6 active-ledger ingestion is not delivered even when append-record succeeds.
- **Proposed resolution**: In each OK-lane ingestion block, prefix record-vendor-sidecar with IMPLEMENT_TMPDIR="$RESEARCH_TMPDIR" (mirror scripts/lint-fix-loop.sh:448-449). Keep append-record --tmpdir "$RESEARCH_TMPDIR" unchanged.


### FINDING_2:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/tokens.py:326-357
- **Concern**: Research record-vendor-sidecar calls cannot resolve an active ledger path. Scenario: The plan adds record-vendor-sidecar in research-phase.md but resolve_token_ledger_path and resolve_session_id only honor IMPLEMENT_TMPDIR and DESIGN_TMPDIR. Research sessions use RESEARCH_TMPDIR and do not write session-env.sh, so ledger ingestion stays a no-op and Item 6 ledger half remains unfixed.
- **Proposed resolution**: Add RESEARCH_TMPDIR to the resolve_session_id and resolve_token_ledger_path tmpdir key loops in the existing python/tokens.py edit, and document ingestion as env -u IMPLEMENT_TMPDIR RESEARCH_TMPDIR="$RESEARCH_TMPDIR" python3 ... token record-vendor-sidecar mirroring design-sidecar env hygiene.


### FINDING_3:
- **Reviewer(s)**: Codex-Innovation, Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/research/references/research-phase.md:186-188
- **Concern**: record-vendor-sidecar has no resolvable ledger context for standalone research. Scenario: The proposed Step 1.4 command runs with only --input. resolve_token_ledger_path reads LARCH_TOKEN_LEDGER, IMPLEMENT_TMPDIR, DESIGN_TMPDIR, or SESSION_ENV_PATH, while /research setup only establishes RESEARCH_TMPDIR, so standalone STATUS=OK Codex lane sidecars still skip active-ledger recording with exit 0.
- **Proposed resolution**: Make the research ingestion command provide a resolver-visible ledger context, for example add RESEARCH_TMPDIR support to resolve_token_ledger_path and run record-vendor-sidecar with RESEARCH_TMPDIR exported, or pass an explicit --ledger under the research tmpdir when no parent ledger context exists.


### FINDING_4:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/research/references/research-phase.md:117-136
- **Concern**: Research `record-vendor-sidecar` steps omit ledger env wiring. Scenario: Item 6 targets active-ledger rows; `record_vendor_from_sidecar` resolves the ledger only via `IMPLEMENT_TMPDIR`, `DESIGN_TMPDIR`, or `SESSION_ENV_PATH` (`python/tokens.py:334-357`). `/research` sets `RESEARCH_TMPDIR` but does not write `session-env.sh` or export `SESSION_ENV_PATH`, so the planned sidecar command will still no-op after parse.
- **Proposed resolution**: Ingestion prose runs, stderr stays quiet, Codex lane spend still missing from `larch-tokens-*.jsonl` while Item 6 is marked done. In the same `python/tokens.py` edit, add `RESEARCH_TMPDIR` to the `resolve_token_ledger_path` root scan (mirror `DESIGN_TMPDIR`). Keep research commands exporting `RESEARCH_TMPDIR` (already set).


### FINDING_5:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/checks.py:882-900
- **Concern**: Planned lint-fix append remains gated on launcher_exit == 0. Scenario: When Codex writes codex.log.token-record and exits non-zero, the default Python ship lint-fix path still drops billable usage from token-report.ndjson and the active ledger; the Bash lint-fix path ingests the sidecar before checking parsed_exit and its harness pins failed-dispatch ledger rows.
- **Proposed resolution**: In _run_codex, ingest a non-empty token_record regardless of launcher_exit; call token append-record with the effective implement tmpdir and record-vendor-sidecar with failures warned and ignored, then return launcher_exit normally.


### FINDING_6:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/research/references/research-phase.md:186-200
- **Concern**: Research Codex sidecar ingestion omits ledger path binding for record-vendor-sidecar. Scenario: Item 6 requires both NDJSON append and active-ledger rows when Codex research sidecars exist; resolve_token_ledger_path only checks IMPLEMENT_TMPDIR DESIGN_TMPDIR and SESSION_ENV_PATH not RESEARCH_TMPDIR so bare record-vendor-sidecar no-ops during /research and ledger rows stay missing despite new prose
- **Proposed resolution**: Mirror design-step2b-drafter.sh: wrap record-vendor-sidecar with env -u IMPLEMENT_TMPDIR DESIGN_TMPDIR="$RESEARCH_TMPDIR" (or pass explicit --ledger) and document unsetting inherited IMPLEMENT_TMPDIR; align failure-modes text with that contract instead of accepting ledger no-op


### FINDING_7:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/research/references/research-phase.md:179-188; python/tokens.py:334-357
- **Concern**: Research active-ledger ingestion has no resolvable ledger in standalone /research. Scenario: /research sets RESEARCH_TMPDIR from SESSION_TMPDIR, but token ledger resolution ignores RESEARCH_TMPDIR. The planned record-vendor-sidecar command can return success without writing active-ledger rows, so Item 6 remains incomplete for successful Codex research lanes.
- **Proposed resolution**: Revise the plan so the research ingestion command provides a ledger context, for example by setting an explicit LARCH_TOKEN_LEDGER or adding minimal RESEARCH_TMPDIR support to token ledger resolution before calling record-vendor-sidecar.


### FINDING_8:
- **Reviewer(s)**: Cursor-dyn-cli-contract
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/research/references/research-phase.md:121-126
- **Concern**: Research `record-vendor-sidecar` omits ledger env binding that existing Codex ingestion uses. Scenario: `resolve_token_ledger_path` only resolves an active ledger from `IMPLEMENT_TMPDIR`, `DESIGN_TMPDIR`, `LARCH_TOKEN_LEDGER`, or `SESSION_ENV_PATH` (`python/tokens.py:334-357`); `RESEARCH_TMPDIR` is not consulted. The plan’s bare `token record-vendor-sidecar --input "$OUTPUT.token-record"` call can no-op when those vars are unset, or write to a leaked `IMPLEMENT_TMPDIR` ledger when it is set. Item 6’s NDJSON append via `--tmpdir "$RESEARCH_TMPDIR"` would succeed while active-ledger ingestion still fails silently.
- **Proposed resolution**: Mirror `skills/design/scripts/design-step2b-drafter.sh:215-216`: wrap `record-vendor-sidecar` as `env -u IMPLEMENT_TMPDIR DESIGN_TMPDIR="$RESEARCH_TMPDIR" python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" token record-vendor-sidecar --input "$OUTPUT.token-record"` so session `session-id` under `$RESEARCH_TMPDIR` drives the ledger path without a `tokens.py` refactor.


### FINDING_9:
- **Reviewer(s)**: Codex-dyn-cli-contract
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/research/SKILL.md:122-130; skills/research/references/research-phase.md:177-188; python/tokens.py:334-357,951-962
- **Concern**: Research Codex sidecar active-ledger command does not bind a ledger tmpdir. Scenario: record-vendor-sidecar resolves only LARCH_TOKEN_LEDGER, IMPLEMENT_TMPDIR, DESIGN_TMPDIR, or SESSION_ENV_PATH. Research setup gives SESSION_TMPDIR/RESEARCH_TMPDIR, so the planned bare command can exit 0 without recording an active-ledger row, or use an inherited IMPLEMENT_TMPDIR ledger.
- **Proposed resolution**: Invoke vendor ingestion with an explicit research ledger env, for example env -u IMPLEMENT_TMPDIR DESIGN_TMPDIR="$RESEARCH_TMPDIR" python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" token record-vendor-sidecar --input "$OUTPUT.token-record"; keep append-record as planned.


### FINDING_11:
- **Reviewer(s)**: Cursor-dyn-prompt-vs-exec
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/research/references/research-phase.md:186-188
- **Concern**: Proposed Codex sidecar ingestion is gated on collector STATUS=OK. Scenario: launch-codex-exec writes ${OUTPUT}.token-record after every run (python/agents.py:1842) regardless of substantive validation; collect-agent-results can emit NOT_SUBSTANTIVE TIMED_OUT or FAILED while the sidecar still holds billable usage; Item 6 targets missing ledger rows when sidecars exist
- **Proposed resolution**: Ingest when ${REVIEWER_FILE}.token-record exists (or loop the four codex-research-*-output.txt paths when codex_available=true), not only when STATUS=OK; keep warn-not-fail


### FINDING_12:
- **Reviewer(s)**: Codex-dyn-prompt-vs-exec
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/research/SKILL.md:168-170; skills/research/references/research-phase.md:150-186; scripts/collect-agent-results.sh:1001-1157; python/agents.py:1842-1863
- **Concern**: Fixed slot-to-output mappings ignore collector REVIEWER_FILE retry outputs. Scenario: research-phase.md is loaded as prompt instructions, not executed as a bash script. Even if the orchestrator follows the proposed prose, collect-agent-results.sh can turn a lane into STATUS=OK with REVIEWER_FILE=...-retry.txt, while launch-codex-exec writes the token sidecar beside that retry output. The proposed arch/edge/ext/sec mapping would ingest the original codex-research-*-output.txt.token-record, missing the retry sidecar or recording the failed initial attempt instead.
- **Proposed resolution**: When parsing collector output, store REVIEWER_FILE per slot and run both token commands against "${REVIEWER_FILE}.token-record" for STATUS=OK. Keep the fixed arch/edge/ext/sec paths only as launch and fallback defaults when REVIEWER_FILE is absent.



### FINDING_1: Wrong implement tmpdir passed into `_run_codex`
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: The plan misstates how `implement_tmpdir` is derived for lint-fix Codex ingestion. `run_lint_fix` sets `allowed_root` to `Path(run_parent).resolve().parent` when `allowed_tmpdir` is absent (session implement root), not `run_parent` itself. Passing `run_parent` would append `token-report.ndjson` under `lint-fix-loop/` instead of the session implement root.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: In checks.py pass str(allowed_root) into _run_codex (allowed_tmpdir when set else parent of run_parent) and document that contract explicitly in the plan checks.py section


### FINDING_2: `record-vendor-sidecar` needs `IMPLEMENT_TMPDIR` via `runner.run(..., env=...)`, not a shell prefix
- **Reviewer(s)**: Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements, Cursor-dyn-api-contract-verify
- **Severity**: important
- **Concern**: The plan documents token ingestion with a shell-style `IMPLEMENT_TMPDIR=` prefix, but `_run_codex` invokes the CLI through `runner.run(argv)` without a shell. `run_lint_fix` threads `allowed_tmpdir` as a Python parameter only; it does not export it into `os.environ`. `token record-vendor-sidecar` resolves the active ledger from child-process environment keys (`resolve_token_ledger_path` in `python/tokens.py`); when no ledger resolves, `record_vendor_from_sidecar` returns success with no row. Meanwhile `token append-record --tmpdir` can succeed. Result: NDJSON and active-ledger ingestion diverge (Item 4/7 half-fixed), especially in isolated tests or direct API callers outside `ship.py`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Specify runner.run(..., env={**os.environ, "IMPLEMENT_TMPDIR": str(implement_tmpdir)}) for record-vendor-sidecar; keep append-record on explicit --tmpdir only
  - From Cursor-Pragmatic: Pass env={**os.environ, "IMPLEMENT_TMPDIR": implement_tmpdir} on the record-vendor-sidecar runner.run call; assert that binding in python/test_checks.py
  - From Cursor-Requirements: Require `_run_codex` to pass `env={**os.environ, "IMPLEMENT_TMPDIR": str(implement_tmpdir)}` (or `--ledger <resolved-path>`) on the `runner.run` call for `token record-vendor-sidecar`; do not rely on a shell env prefix alone
  - From Cursor-dyn-api-contract-verify: Mirror `_mark_step_ledger` (checks.py:246-247): pass `env={**os.environ, "IMPLEMENT_TMPDIR": str(implement_tmpdir)}` on the `record-vendor-sidecar` `runner.run` call; use `implement_tmpdir` for `append-record --tmpdir` and extend `python/test_checks.py` to assert the vendor subprocess env includes `IMPLEMENT_TMPDIR`.


### FINDING_4: Token subprocess argv must use plugin-absolute CLI path, not cwd-relative `python/cli.py`
- **Reviewer(s)**: Cursor-dyn-api-contract-verify, Cursor-dyn-caller-compat
- **Severity**: important
- **Concern**: The plan documents new token ingestion calls as cwd-relative `python3 python/cli.py`, but existing `_run_codex` and `_mark_step_ledger` invoke the plugin-root CLI via `_agent_cli()` / `scripts_dir.parent / "python" / "cli.py"` with `cwd=repo_root`. Consumer repos have no repo-root `python/cli.py`. Literal plan adoption makes subprocesses fail or hit the wrong entrypoint; ingestion legs can warn-and-continue or fail silently.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-api-contract-verify: Specify `_run_codex` token subprocess argv uses `python3`, `str(_agent_cli())`, and the same flag order as `scripts/lint-fix-loop.sh:443-449`; do not use cwd-relative `python3 python/cli.py`.
  - From Cursor-dyn-caller-compat: Spell out that new _run_codex ingestion must reuse the plugin-absolute CLI argv already used at python/checks.py:887-889 (str(scripts_dir.parent / "python" / "cli.py") or _agent_cli()) and pass IMPLEMENT_TMPDIR via runner.run env= per _mark_step_ledger at python/checks.py:246-247


### FINDING_5: Research ingestion may skip first-pass sidecar when collector selects retry output
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Concern**: Research sidecar selection follows only the collector's `REVIEWER_FILE`, falling back to the fixed slot output path only when `REVIEWER_FILE` is absent. After a retry, `collect-agent-results` can set `REVIEWER_FILE` to a `*-retry.txt` while the original fixed output still has a billable `${OUTPUT}.token-record` from the first pass. Ingesting only the retry path drops first-pass usage from `token-report.ndjson` and the active ledger (Item 6 gap persists).
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Generic: For each slot, collect candidates from both the collector REVIEWER_FILE and the fixed slot output path, dedupe, then ingest every existing non-empty ${OUTPUT}.token-record; keep REVIEWER_FILE first but do not make the fixed path exclusive.




### FINDING_2: Research ingestion leaves `LARCH_TOKEN_SESSION_ID` unset
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: Research active-ledger ingestion unsets parent tmpdir vars but not `LARCH_TOKEN_SESSION_ID`. `resolve_session_id` prefers `LARCH_TOKEN_SESSION_ID` before any tmpdir session-id file, so a leaked parent value can write Codex usage to the wrong `larch-tokens` slug under `RESEARCH_TMPDIR` even after `RESEARCH_TMPDIR` resolver support lands.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Add `-u LARCH_TOKEN_SESSION_ID` to the documented env wrapper for `record-vendor-sidecar` or set it from `$RESEARCH_TMPDIR/session-id` before ingestion.


### FINDING_3: Lint-fix subprocess env spreads stale `LARCH_TOKEN_SESSION_ID`
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: Python lint-fix active-ledger ingestion spreads `os.environ` without clearing `LARCH_TOKEN_SESSION_ID`. The new `env={**os.environ, IMPLEMENT_TMPDIR=...}` subprocess can bind the wrong ledger slug inside the implementation tmpdir when a stale `LARCH_TOKEN_SESSION_ID` is present while `IMPLEMENT_TMPDIR/session-id` differs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Build the subprocess env from `os.environ` with `LARCH_TOKEN_SESSION_ID` removed or set from `implement_tmpdir/session-id` before calling `record-vendor-sidecar`.


### FINDING_4: Token subprocess failures not surfaced in `_run_codex`
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: The plan requires warn-on-failure for lint-fix token append and active-ledger ingestion but does not require surfacing subprocess stderr or exit codes. `_run_codex` uses `Runner.run` with default captured stderr; token CLI warnings and `record-vendor-sidecar` failures are discarded when results are ignored, repeating the silent-failure pattern Items 1/4 target.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: After each token subprocess in `_run_codex`, inspect `CommandResult.returncode` and stderr; emit operator-visible warnings (`sys.stderr` write and/or `implement_tmpdir` `execution-issues.md`) matching `scripts/lint-fix-loop.sh` `larch_err` behavior; add a `test_checks` assertion that a failing append-record surfaces a warning.




### FINDING_1: Active-ledger ingestion env omits `LARCH_TOKEN_LEDGER` unset
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-dyn-env-isolation, Cursor-Pragmatic
- **Severity**: important
- **Concern**: Planned `record-vendor-sidecar` / active-ledger ingestion in `python/checks.py` does not unset `LARCH_TOKEN_LEDGER` (and related inherited ledger env) the way research ingestion does. `resolve_token_ledger_path` prefers `LARCH_TOKEN_LEDGER` over `IMPLEMENT_TMPDIR`, while `append-record` writes NDJSON under `--tmpdir`. A parent env that leaks `LARCH_TOKEN_LEDGER` can send active-ledger rows to a different path than NDJSON, recreating Item 3 split behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Match research-phase.md: build record-vendor-sidecar env from os.environ with LARCH_TOKEN_LEDGER LARCH_TOKEN_SESSION_ID and other inherited ledger keys removed then IMPLEMENT_TMPDIR set; add a test_checks assertion that LARCH_TOKEN_LEDGER is absent from the env dict
  - From Cursor-Innovation: Build the `record-vendor-sidecar` subprocess `env=` from `os.environ` with `LARCH_TOKEN_SESSION_ID`, `LARCH_TOKEN_LEDGER`, `DESIGN_TMPDIR`, `RESEARCH_TMPDIR`, and `SESSION_ENV_PATH` removed, then set `IMPLEMENT_TMPDIR`. Mirror research-phase `env -u` contract. Extend `python/test_checks.py` to assert `LARCH_TOKEN_LEDGER` is absent from that env.
  - From Cursor-Pragmatic: Mirror research-phase.md: build env from os.environ, pop LARCH_TOKEN_SESSION_ID and LARCH_TOKEN_LEDGER, then set IMPLEMENT_TMPDIR for the record-vendor-sidecar runner call; extend test_checks.py to assert LARCH_TOKEN_LEDGER is absent


### FINDING_3: Research Codex sidecar ingestion misses per-slot and retry artifact paths
- **Reviewer(s)**: Cursor-Arch, Codex-Generic
- **Severity**: important
- **Concern**: Planned research-phase Codex ingestion does not cover all billable sidecar outputs. Per-slot ingestion may not bind collector `REVIEWER_FILE` to the four slot keys, so retry sidecars beside `REVIEWER_FILE` are skipped when a loop scans only fixed `codex-research-*-output.txt` paths. Separately, `collect-agent-results.sh` can write retry sidecars beside `<fixed>-retry.txt` or `<fixed>-ns-retry.txt` while reporting `REVIEWER_FILE` as the original fixed output; those Codex retry token records would still be absent from NDJSON and the active ledger.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: After parsing collector output in COLLECT_ARGS order map each arch edge ext sec result to its slot then for that slot dedupe and ingest REVIEWER_FILE plus the fixed codex-research-*-output.txt path when non-empty
  - From Codex-Generic: Add the derived retry outputs for each fixed slot path, ${fixed%.txt}-retry.txt and ${fixed%.txt}-ns-retry.txt, to the candidate output list before deduplication, then run the same best-effort ingestion for any non-empty .token-record sidecar.


### FINDING_4: Lint-fix tests do not verify `implement_tmpdir` threading at `run_lint_fix` call site
- **Reviewer(s)**: Cursor-dyn-tmpdir-root-derivation
- **Severity**: important
- **Concern**: Planned tests only cover direct `_run_codex` calls and reference `run_parent` though `_run_codex` takes `run_dir`; they do not verify `run_lint_fix` passes session `allowed_root` as `implement_tmpdir`. If `run_lint_fix` passes `run_parent` or `run_dir.parent` (lint-fix-loop) at the call site, unit tests that invoke `_run_codex` with correct kwargs still pass and token `append-record` writes to `lint-fix-loop/token-report.ndjson` instead of the session root.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-tmpdir-root-derivation: Add a run_lint_fix integration test with _lint_fix_dirs canonical layout (run_dir under implement_tmpdir/lint-fix-loop); spy _run_codex or assert append-record --tmpdir is the session root not lint-fix-loop; require direct _run_codex fixtures to use the same nesting so run_dir.parent is not the session root



