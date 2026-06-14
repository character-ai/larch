# Review Round 4

- Mode: `diff`
- 18 accepted, 0 rejected (0 neutral)

## Accepted Findings

### FINDING_1: `normalize_outcome` / final-report outcome normalization lacks bash parity
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, dyn-migration-parity-output.txt, dyn-callsite-routing-output.txt
- **Severity**: important
- **Concern**: Python `stall_recovery.normalize_outcome` (lines 253–266) is a stub: it ignores `--in-memory-stall-tracking`, reads only `ship-pr-state.sh` via `_state()`, skips `finalize-state.sh` / `session-env.sh`, and maps most non-stall runs to `completed`/`true`. It omits tokens such as `merged`, `pr-created`, `pr-created-draft`, `bailed`, `bailed-needs-user-input`, `forked-dry-run`, and `design-only`, plus diagnostic KVs Step 18a.5 and `write-final-report` expect. `pr_body._normalized_outcome` (679–691) duplicates a second incomplete copy (adds `merged` / `design-only` but still misses `pr-created`, `forked-dry-run`, in-memory stall, and full layer semantics). Step 17/ship (`final-report write`) and Step 18a.5 (`stall-recovery normalize-outcome`) can diverge on the same run.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Port bash `cmd_normalize_outcome` decision tree and add parity tests from `test-stall-recovery-report-2/3`.
  - From dyn-migration-parity-output.txt: Port the full bash decision tree into `normalize_outcome`, including `--in-memory-stall-tracking` and all four stall layers, and emit the same KV set as `cmd_normalize_outcome`. Have `pr_body._normalized_outcome` call this helper instead of duplicating a second simplified copy.
  - From dyn-callsite-routing-output.txt: Port bash `normalize-outcome` fully into Python (including `--in-memory-stall-tracking`), route `pr_body.write_final_report` through the same helper, and extend `test_stall_recovery.py` for merge/stalled/in-memory cases.


### FINDING_10: `test-oos-disposition-gate` pytest filter matches almost no disposition coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Makefile runs `pytest python/test_file_oos.py -k 'disposition'`, but only one shallow `disposition_checkpoint` test exists. OOS disposition gaps (inline triage, filed URLs, rejected NDJSON markers, fork bypass) can regress silently; the old ~1000-line gate harness is out of CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add `disposition_gate` pytest matrix ported from `test-oos-disposition-gate.sh`; update `-k` filter accordingly.


### FINDING_11: `test-materialize-manifest-oos` still exercises bash harness
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Shard 18 runs `test-materialize-manifest-oos.sh` while `step2-implement.sh` uses Python `oos materialize-manifest`. CI does not exercise the production path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Retarget to pytest for `materialize_manifest_oos`; delete bash harness after parity.


### FINDING_12: `test-append-execution-issue` targets wrong pytest module
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Makefile runs `python/test_run_logs.py` instead of `python/test_execution_issues.py`. The new `execution_issues.append` API and CLI verb are not covered by the CI target named for append behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Point Makefile at `python/test_execution_issues.py` with append-focused tests.


### FINDING_13: `test-render-run-summary` / `test-compose-pr-summary` still test bash scripts
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Live callers use `python/cli.py render run-summary` and `pr compose-summary`, but CI harnesses still grep bash scripts, allowing bash/Python drift.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Retarget Makefile to `python/test_pr_body.py`; expand render/compose coverage there.


### FINDING_16: Step 7a no longer stages full pre-ship run-log batches before commit
- **Reviewer(s)**: codex-generic-output.txt
- **Severity**: important
- **Concern**: `_run_log_flush` (67–145) flushes execution issues, captures transcript, and commits whatever already exists. The old flow staged token report, timing report, vendor-failure diagnostics, parent issue, transcript metadata, prompts, commit message, and manifest batches first. Normal `/implement` runs can reach pre-PR commit with missing run-log artifacts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-generic-output.txt: Port the missing `run-log write` and vendor diagnostics steps, or call the existing Python run-log pre-flush API that stages the full batch set before `run-log commit`.


### FINDING_17: `classify` missing bash stall gate and design state-file merge
- **Reviewer(s)**: dyn-migration-parity-output.txt, dyn-callsite-routing-output.txt
- **Severity**: important
- **Concern**: Python `classify` (181–213) always runs `_classify_text` and can label non-stall runs as `test-failure` / `lint-failure` / `transient-infra`. It ignores `--in-memory-stall-tracking`, does not read `session-env.sh` for step/phase/bail metadata, omits stall-layer gating (`FAILURE_CLASS=unrecoverable` / `no-stall` when all layers false), and ignores `--primary-state-file` / `--session-env-file` that `design-failure-report.sh` passes — so design tmpdirs can miss `design-failure-terminal-state.env`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-migration-parity-output.txt: Mirror bash `cmd_classify`: compute `any_stall` from in-memory + ship + finalize + session layers before classifying; only call `_classify_text` when stalled; merge precedence from all three state files; emit the full classification KV set and write `stall-recovery-classification.env` with the same keys bash writes.
  - From dyn-callsite-routing-output.txt: Teach `classify` to merge state from `--primary-state-file` / `--session-env-file` (same precedence as bash), and add a design-shaped classify test using `design-failure-terminal-state.env`.


### FINDING_18: `disposition_checkpoint_main` commit-range fallback diverges from bash
- **Reviewer(s)**: dyn-migration-parity-output.txt
- **Severity**: important
- **Concern**: `commit_range` is `merge-base..HEAD` or bare `HEAD` (550–551). Bash falls back to `origin/main..HEAD` when merge-base is missing. Bare `HEAD` makes `_count_inline_triage` walk full history and can inflate inline-triage counts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-migration-parity-output.txt: Match bash range selection: prefer `merge-base..HEAD`, else `origin/main..HEAD` when `origin/main` resolves, else a safe empty/single-commit fallback; add pytest coverage for the merge-base-absent path.


### FINDING_19: Step 7a `REBASE_OUTCOME` read from dead `7a.r` file overwrites probe stdout
- **Reviewer(s)**: dyn-migration-parity-output.txt
- **Severity**: important
- **Concern**: After successful rebase probe, terminal `REBASE_OUTCOME` comes from tmpdir file `7a.r` (251–260), which nothing writes. Probe stdout already emits `REBASE_OUTCOME=ok|skipped`, so the tail usually overwrites the real value with `skipped`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-migration-parity-output.txt: Parse `REBASE_OUTCOME` from the probe stdout capture (last wins), default to `skipped` only when absent, and drop the dead `7a.r` file read unless a real writer is added.


### FINDING_2: `compose_report` stub drops bash parity, design argv, and Tier B safety
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-generic-output.txt, dyn-callsite-routing-output.txt
- **Severity**: important
- **Concern**: `compose_report` (354–385) hard-codes `stall-recovery-*.env/md` paths, ignores caller overrides (`--classification-file`, `--root-cause-file`, `--bounded-root-cause-file`, `--attempts-file`, `--sensitive-corpus-file`, etc.) that `design-failure-report.sh` passes. Reports are minimal stubs (fixed `Larch version | unknown`, no attempt table, escalation ledger, or allowlist-driven chat-print sections). There is no sensitive-corpus validation, Tier B redaction, or path confinement before posting bounded-root-cause prose to public GitHub issues/chat. `/design` terminal reports can show `Failure class: unknown` and omit prepared root-cause content while exiting 0.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Port `cmd_compose_report` from `stall-recovery-report.sh` or delegate until parity; expand tests.
  - From cursor-specialist-edge-cases-output.txt: Port bash `cmd_compose_report` safety pipeline (corpus build, token rejection, tier surfaces, upstream filing) into Python.
  - From codex-generic-output.txt: Add and honor the same artifact-path arguments as the bash contract, defaulting through `artifact_prefix` only when the caller does not provide paths.
  - From dyn-callsite-routing-output.txt: Port the full bash `compose-report` contract: accept all caller file overrides, honor `--profile generic` / `--artifact-prefix design-failure`, and add pytest coverage that mirrors `design-failure-report.sh` argv shapes.


### FINDING_20: `test-render-cost-line-callsites.sh` still greps retired bash call site
- **Reviewer(s)**: dyn-callsite-routing-output.txt
- **Severity**: important
- **Concern**: Harness requires `render-final-summary.sh` to invoke `render-run-summary.sh`, but the live call site is `python3 "$PLUGIN_ROOT/python/cli.py" render run-summary` (`render-final-summary.sh:566`). `make test-render-cost-line-callsites` (shard 11) will fail while sibling `test-render-run-summary-callsites.sh` was updated.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-callsite-routing-output.txt: Align `test-render-cost-line-callsites.sh` with `test-render-run-summary-callsites.sh`: grep for `python/cli.py render run-summary` and per-bucket token flags instead of `render-run-summary.sh`.


### FINDING_21: `write-final-report.sh` retains divergent bash authority vs production Python CLI
- **Reviewer(s)**: dyn-callsite-routing-output.txt
- **Severity**: important
- **Concern**: Production paths (`step-17.sh`, `ship-pr.sh`) call `python/cli.py final-report write`, but the retained bash wrapper still invokes `stall-recovery-report.sh normalize-outcome` and `scripts/render-run-summary.sh`. Offline harnesses exercise the bash wrapper, not `python/pr_body.py`, so live-path regressions may escape CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-callsite-routing-output.txt: Either delete or thin `write-final-report.sh` to a one-line `exec python3 … final-report write`, retarget harnesses to the CLI, and drop the bash `render-run-summary.sh` dependency from the implement summary path.


### FINDING_22: `skills/design/SKILL.md` still references retired `stall-recovery-report.sh`
- **Reviewer(s)**: dyn-callsite-routing-output.txt
- **Severity**: important
- **Concern**: Operator docs say design terminal-state validation goes through `stall-recovery-report.sh`, but `design-stage-terminal-state.sh` already calls `python/cli.py stall-recovery validate-token` / `validate-terminal-state`. Runbook drift can send maintainers to a retired entrypoint after bash deletion.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-callsite-routing-output.txt: Update `skills/design/SKILL.md` (and any linked contract prose) to reference `python/cli.py stall-recovery …` consistently with the cutover scripts.


### FINDING_3: `record_escalation` failure paths ignore `artifact_prefix`
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: On ledger write failure (346–350), Python writes unprefixed `stall-recovery-escalation-record-failure.env` and `stall-recovery-escalation-ledger.fallback.tsv`, ignoring `--artifact-prefix`. Generic `/design` escalation write failures leave markers where `design-failure-report.sh` does not look.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Use `_artifact_path` for ledger, fallback, and marker on all branches.


### FINDING_4: `populate-sensitive-corpus` still delegates to bash
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-generic-output.txt, dyn-callsite-routing-output.txt, dyn-lint-readiness-output.txt
- **Severity**: important
- **Concern**: `populate_sensitive_corpus` (742–745) is the only subcommand still routed through `_delegate_stall_recovery_subcommand()` to `skills/implement/scripts/stall-recovery-report.sh`. `design-failure-report.sh` depends on this before `compose-report`. Deleting the bash script breaks Tier B corpus population at runtime and violates the C4c direct-cutover / no-shim goal; pytest does not cover this path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Port `cmd_populate_sensitive_corpus` to Python; remove bash delegate.
  - From cursor-specialist-edge-cases-output.txt: Port `populate-sensitive-corpus` and `build_sensitive_corpus_from_evidence` fully into Python.
  - From codex-generic-output.txt: Port `populate-sensitive-corpus` into `python/stall_recovery.py` and remove the `_delegate_stall_recovery_subcommand` path for this migrated verb.
  - From dyn-callsite-routing-output.txt: Port `populate-sensitive-corpus` to Python and remove `_delegate_stall_recovery_subcommand` once parity tests pass.
  - From dyn-lint-readiness-output.txt: Port `populate-sensitive-corpus` into `stall_recovery.py` (mirror the bash corpus builder), remove `_STALL_RECOVERY_SH` / `_delegate_stall_recovery_subcommand`, add pytest for corpus population, then retire the bash script and register it in `python/migrated-scripts.tsv`.


### FINDING_5: C4c sh-to-py cutover incomplete — bash surfaces, harnesses, and `migrated-scripts.tsv`
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, dyn-callsite-routing-output.txt, dyn-lint-readiness-output.txt
- **Severity**: important
- **Concern**: Core absorbed bash helpers (`stall-recovery-report.sh`, `write-final-report.sh`, `implement-finalize.sh`, `flush-execution-issues.sh`, `materialize-manifest-oos.sh`, `oos-disposition-checkpoint.sh`, etc.) remain in-tree alongside Python replacements. `python/migrated-scripts.tsv` has no C4c rows, so `lint-retired-scripts` cannot gate deletion; dual implementations drift. `skills/implement/SKILL.md` S030 reachability pins still list retired bash paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Complete cutover, register retired paths, port harnesses to pytest, delete absorbed scripts.
  - From cursor-specialist-testing-output.txt: Add all plan-listed retired paths with issue number; finish deletion and run `lint-retired-scripts`.
  - From dyn-callsite-routing-output.txt: Add all C4c retired paths with the tracking issue number to `migrated-scripts.tsv` as scripts are deleted, and finish deleting bash once call sites and harnesses are fully on Python.
  - From dyn-lint-readiness-output.txt: Update S030 reachability lists to Python-only paths, add all retired C4c scripts to `migrated-scripts.tsv`, and run `make lint-retired-scripts` before deleting the bash files.


### FINDING_7: `validate_tier_b_public_file` scans static corpus only
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `validate_tier_b_public_file` (627–652) scans only the passed corpus file. Bash rebuilds the effective corpus from all session evidence first. Tier-B comments can pass validation while secrets in `classification.env` or the escalation ledger are omitted from the corpus copy.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Rebuild effective sensitive corpus from evidence files inside `validate_tier_b_public_file` before scanning the public candidate.


### FINDING_8: Stall-recovery CI retargeted to shallow pytest without sensitive-leak parity
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Makefile targets `test-stall-recovery-report-{1,2,3}` now run filtered `pytest -k` subsets (~211 lines) instead of ~2671-line bash harnesses. `compose_report` and `validate_tier_b` regressions (classification, dedup, sensitive-leak, path confinement) can merge without CI catching public secret leaks.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Port bash harness sensitive-leak and path-confinement cases into `python/test_stall_recovery.py`.
  - From cursor-specialist-testing-output.txt: Port critical cases from `test-stall-recovery-report-{1,2,3}.sh` into `test_stall_recovery.py` before relying on pytest-only CI.


