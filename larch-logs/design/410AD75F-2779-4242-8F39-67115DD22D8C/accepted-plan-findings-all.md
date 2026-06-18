### FINDING_1: `helper.exists()` guard leaves Step 3 escalation as silent no-op after shell deletion
- **Reviewer(s)**: Cursor-Arch, Cursor-Requirements
- **Severity**: blocking
- **Concern**: The plan replaces the subprocess call to `stall-recovery-report.sh` but does not require removing the `if not helper.exists(): return 0` early return at `plan_review.py:1202-1204`. After the shell script is deleted, `step3_record_report_evidence` still returns 0 without writing `design-failure-escalation-ledger.tsv` or touching `.step3-report-<status>.recorded`, so `test_record_report_evidence_writes_escalation_ledger` and live `/design` Step 3 escalation evidence break silently while Step 3 appears successful.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: In the `### UPDATED: python/plan_review.py` section, explicitly delete the `helper` path lookup and the `if not helper.exists(): return 0` guard; always call `stall_recovery.record_escalation()` once tmpdir validation passes
  - From Cursor-Requirements: In the plan_review.py section, explicitly delete the `if not helper.exists(): return 0` guard and always invoke `stall_recovery.record_escalation()`; preserve sentinel touch only on rc 0 and warning return on failure


### FINDING_2: Direct `record_escalation()` Namespace omits CLI-default fields (`exit_code`, `failure_detail_log`)
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Cursor-Innovation, Codex-Innovation, Cursor-Pragmatic, Codex-dyn-redaction-contracts, Codex-dyn-pytest-parity
- **Severity**: blocking
- **Concern**: The planned direct `record_escalation()` call builds an `argparse.Namespace` with the current shell flags but omits fields the CLI supplies by default. `record_escalation` reads `args.exit_code` directly at `stall_recovery.py:451` (no `getattr` fallback), so a hand-built Namespace without `exit_code` raises `AttributeError` before writing the ledger or sentinel; only `OSError` is caught in `plan_review.py`. The subprocess path omits `--exit-code` because argparse defaults it to `unknown`. `failure_detail_log` is accessed via `getattr` but should still be set explicitly for CLI parity.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add `exit_code="unknown"` to the preserved field list for the direct Python call (match `record-escalation` argparse default at python/stall_recovery.py:1845)
  - From Codex-Arch: Pass `exit_code="unknown"` in the Namespace, or make `record_escalation` use `getattr(args, "exit_code", "unknown")`
  - From Cursor-Innovation: Include `exit_code="unknown"` and `failure_detail_log=""` on the Namespace (or parse argv through `record_escalation_main`) and broaden failure handling if needed
  - From Codex-Innovation: Add `exit_code="unknown"` to the Namespace, or change `record_escalation` to read it with a getattr default; keep the stdout and stderr redirect around that call
  - From Cursor-Pragmatic: Specify `exit_code="unknown"` on the Namespace (matching CLI default) alongside profile, artifact_prefix, implement_tmpdir, site, trigger, step, phase, dispatcher
  - From Codex-dyn-redaction-contracts: Add `exit_code="unknown"` to the direct `argparse.Namespace`, or call `record_escalation_main` with argv so argparse keeps the default
  - From Codex-dyn-pytest-parity: Add `exit_code="unknown"` to the direct Namespace, and add `failure_detail_log=""` explicitly for CLI parity


### FINDING_3: Makefile `-k` shard filters not updated for ported pytest cases
- **Reviewer(s)**: Cursor-Arch, Cursor-Pragmatic, Cursor-dyn-redaction-contracts, Cursor-dyn-pytest-parity
- **Severity**: blocking
- **Concern**: The plan keeps `test-stall-recovery-report-{1,2,3}` shard target names but does not require revising pytest `-k` filters when retiring bash harness cases into new tests. CI already runs these targets via substring filters (`retry_policy`, `compose_report`, `dedup`, `validate_tier_b`, etc.). New tests named outside current `-k` substrings (generic-profile dedup, Tier B resolver fallback, legacy-gate replacements, redaction/dedup golden vectors) will not run in CI shards. `python/test_stall_recovery.py` is ENFORCED in `scripts/lint-harness-pytest-partition.py` and requires strict partition with zero uncovered tests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: In `### UPDATED: Makefile`, require updating each shard's `-k` expression (or naming new tests to match existing substrings) and running `scripts/lint-harness-pytest-partition.py` / `make lint` so every ported bash case lands in a shard
  - From Cursor-Pragmatic: Update `test-stall-recovery-report-{1,2,3}` `-k` expressions when adding tests or name new tests to match existing shard filters
  - From Cursor-dyn-redaction-contracts: Add an explicit Makefile subsection: update all three `-k '...'` expressions (or drop `-k` and partition by `@pytest.mark`) so every ported case24/case25/case23 contract test runs in CI
  - From Cursor-dyn-pytest-parity: Extend `### UPDATED: Makefile` to rebalance `-k` expressions on `test-stall-recovery-report-{1,2,3}` so every new test name is covered exactly once; run `python3 scripts/lint-harness-pytest-partition.py` before deleting bash harnesses


### FINDING_5: Bash harness cases 21–22 durability coverage not ported to pytest before deletion
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: The plan omits bash harness case 21–22 durability tests. Deleting `test-stall-recovery-report-{1,2,3}.sh` drops malformed-state exit 3 clear/seed atomic-failure coverage that pytest does not yet have.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Add pytest for case 21 symlink/malformed classify exit 3 and case 22 clear-stall/seed-terminal-state failure branches before deleting bash harnesses


### FINDING_7: `test-ci-decide.sh` cutover to `validate-token` or `lint` drops classify contract
- **Reviewer(s)**: Codex-Requirements, Codex-dyn-cutover-completeness, Codex-dyn-pytest-parity
- **Severity**: important
- **Concern**: The plan permits replacing `test-ci-decide.sh` stall checks with `validate-token` or `lint`, which drops the state-backed classify contract. The existing harness verifies that `ci-decide` `BAIL_REASON` values survive `stall-recovery classify` rendering, including `ci-local-unfixable` suffix acceptance and bare-token redaction. `validate-token` emits `TOKEN_VALID` and uses `_safe_token`, rejecting implement bail tokens instead of `_safe_bail_reason_value`; `lint` emits `LINT_OK`. Following the plan literally can fail the test or weaken the actual acceptance check.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Keep the existing fixtures and call `python3 "$ROOT/python/cli.py" stall-recovery classify --implement-tmpdir "$dir"`; use lint only as an extra check, not a substitute
  - From Codex-dyn-cutover-completeness: Revise the plan to keep this harness on `python3 "$ROOT/python/cli.py" stall-recovery classify` with the existing `--implement-tmpdir` fixtures
  - From Codex-dyn-pytest-parity: Keep the classify-based assertions for these tokens, or use stall-recovery lint only for config alignment and remove validate-token as an allowed replacement unless validate-token is fixed in scope


### FINDING_8: `test-design-stage-terminal-state.sh` asserts `VALID=true` but Python CLI emits `TOKEN_VALID=true`
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Concern**: The plan cuts the test to the Python CLI but does not account for the validate-token KV key change. The shell helper emits `VALID=true`, while `python/stall_recovery.py` emits `TOKEN_VALID=true`; after replacing the direct shell call, the unchanged `grep` for `VALID=true` makes `make test-design-stage-terminal-state` fail.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Update that assertion to expect `TOKEN_VALID=true` or assert the exit status only; keep Python CLI KV outputs unchanged if preserving the current Python surface


### FINDING_9: Record-escalation ledger output path validation missing after shell authority removal
- **Reviewer(s)**: Codex-dyn-redaction-contracts
- **Severity**: important
- **Concern**: Record-escalation output path validation is missing from the Python authority cutover. The current shell `record-escalation` path validates the canonical ledger as an absolute non-symlink write path under the tmpdir. The proposed plan keeps existing Python `record_escalation` behavior, which reads and writes the ledger path directly. A symlinked ledger inside the tmpdir can redirect writes outside the confined report surface after the shell path is removed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-redaction-contracts: Before deleting the shell body or switching plan_review.py, add minimal ledger/fallback/marker validation in `record_escalation` with the existing tmpdir write validator, preserve degraded fallback and marker behavior, and port the narrow case23 degraded-ledger coverage


### FINDING_11: Tier A dedup non-dry cases omitted from pytest migration
- **Reviewer(s)**: Codex-dyn-pytest-parity
- **Severity**: important
- **Concern**: Tier A dedup non-dry cases are omitted from the pytest migration. The bash harness covers `dedup-tier-a-report` no-match, lookup-failed-open, dedup-comment, `LARCH_STALL_RECOVERY_DRY_RUN`, and `DRY_RUN_DECISION`; current pytest only covers dry-run, and the plan's Tier A bullets cover compose issue-input parsing and denial. Deleting the harness leaves real Tier A dedup behavior unverified.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-pytest-parity: Add a compact pytest for dedup-tier-a-report no-match, lookup failure, duplicate comment, and DRY_RUN_DECISION using the existing gh/helper stubs; keep the existing dry-run test




### FINDING_1: Split record_escalation ledger pre-write failure branches
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements
- **Severity**: blocking
- **Concern**: The plan and current Python sketch collapse two distinct bash `cmd_record_escalation` pre-write paths into one degraded fallback. Bash treats an existing non-writable regular ledger as degraded fallback/marker with return 0 (`stall-recovery-report.sh:1910-1912`), but symlink/outside-tmpdir/invalid ledger paths fail `validate_tmpdir_write_file`, write a tagged Tool Failure, and exit 1 (`:1914-1916`). Routing all `_validate_tmpdir_write_path` failures through the case23 fallback would return 0, touch `.step3-report-*.recorded` sentinels, and violate the non-goal of no verb behavior change.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Split branches: existing regular ledger not rw → degraded fallback return 0; validate_tmpdir_write_path failure → write tool failure and return 1 (mirror bash 1914-1916); append OSError → degraded write-failed
  - From Cursor-Innovation: Split branches: keep the existing `OSError`/non-writable degraded path; on validation failure call a ported `_write_record_escalation_tool_failure` (mirror `review_and_fix.py:1947`) with reason `canonical-ledger-validation-failed` and return `1`
  - From Cursor-Pragmatic: Split the two branches in `record_escalation()`: keep the case23 chmod-444/non-writable regular-file path on fallback/marker with return 0; on `_validate_tmpdir_write_path` failure (symlink/outside tmpdir) return 1 after writing the execution-issues tool-failure tag, matching bash lines 1914-1916
  - From Cursor-Requirements: Split record_escalation pre-write handling to mirror bash: if ledger exists and is non-writable, write fallback/marker and return 0; if _validate_tmpdir_write_path fails, emit canonical-ledger-validation-failed tool failure and return 1. Align pytest for non-writable vs symlink/outside-tmpdir cases with those distinct KVs/exit codes


### FINDING_2: Port record-escalation Tool Failure writer for bash parity
- **Reviewer(s)**: Cursor-Innovation, Cursor-Pragmatic
- **Severity**: important
- **Concern**: The plan does not require porting bash `write_record_escalation_tool_failure` into `stall_recovery.py`. Python `record_escalation()` only catches `OSError` and writes fallback/marker files; it never appends the `## Tool Failure: record-escalation` block to `execution-issues.md`. After deleting the shell body, `compose_report` escalation-success paths that consult `_record_escalation_tool_failure_present()` can miss degraded record-escalation evidence.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Add the writer helper to `stall_recovery.py` and invoke it on validation-failed and other bash parity failure paths before returning non-zero
  - From Cursor-Pragmatic: Port the bash tool-failure append helper into Python and invoke it from both degraded branches (non-writable fallback and validation-failed), with pytest asserting the execution-issues marker for case23-style failures


### FINDING_6: test-ci-decide.sh classify replacement references undefined ROOT
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Concern**: A planned classify replacement that uses `python3 "$ROOT/python/cli.py"` will fail under `set -u` because `scripts/test-ci-decide.sh` defines `SCRIPT_DIR` but not `ROOT`, so `make test-ci-decide` would abort before exercising the stall-recovery classify contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Generic: Define ROOT after SCRIPT_DIR, for example ROOT="$(cd "$SCRIPT_DIR/.." && pwd -P)", or use "$SCRIPT_DIR/../python/cli.py" in the replacement commands




### FINDING_3: Design failure-report tests must preserve CLAUDE_PROJECT_DIR on cutover
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: `assert_sensitive_leak_blocked` calls `stall-recovery-report.sh` with `CLAUDE_PROJECT_DIR="$consumer"` (empty non-dev clone); the plan only says swap to `python3 cli.py stall-recovery` without pinning that env. After cutover, populate/compose may resolve `_tier_a_allowed` against the real repo root instead of the empty consumer dir; sensitive-corpus leak tests false-pass or false-fail.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: In the `### UPDATED: skills/design/scripts/test-design-failure-report.sh` section, require preserving `CLAUDE_PROJECT_DIR="$consumer"` (and `env -u CLAUDE_PLUGIN_ROOT` if still used) on every direct `populate-sensitive-corpus` / `compose-report` invocation


### FINDING_4: Classifier redaction and state-file validation parity omitted
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Concern**: The plan omits classifier redaction and state-file validation parity while deleting the bash authority. After shell deletion, `classify` can read caller-supplied state paths without the bash confinement/symlink/malformed-state checks and can persist raw `STALL_STEP`, `PHASE`, `BAIL_REASON`, `EXIT_CODE`, `MATCHED_CLASSIFIER_PATTERN`, and `DISPATCHER` values, breaking the stated sanitized Tier-A/Tier-B and no-behavior-change contracts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Generic: Add the minimal bash-parity classifier work to python/stall_recovery.py: validate primary/finalize/session state files under tmpdir, reject symlinked or malformed state with the existing bash exit semantics, and sanitize persisted/emitted classifier fields before report composition uses them



### FINDING_1: classify() lacks bash-equivalent malformed primary ship-pr-state.sh syntax gate
- **Reviewer(s)**: Cursor-Arch
- **Severity**: blocking
- **Concern**: The plan omits explicit malformed primary `ship-pr-state.sh` handling on `classify`. Current `classify()` reads state via `_merged_state()` / `_read_state_file()` with no upfront syntax gate. Bash `validate_ship_pr_state` exits 3 before classification (case21-malformed). Python `_state_file_syntax_ok()` is also weaker than bash `check_ship_pr_state_syntax`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: In ### UPDATED: python/stall_recovery.py classify section, require primary ship-pr-state.sh pass bash-equivalent syntax validation before KV merge; on failure print malformed ship-pr-state.sh stderr and exit 3 with no classification file write


### FINDING_2: classify subparser omits --profile for generic-profile routing
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: The plan adds generic-profile classify routing but omits `--profile` on the classify subparser. Bash case25 invokes `--profile generic … classify --primary-state-file …` (test-stall-recovery-report-3.sh:876). Python `classify` never reads `profile` from CLI today; generic terminal-state routing cannot run from harness/CLI cutover.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Add `p.add_argument("--profile", default="implement")` to the classify branch in `main()` and thread `profile` into `classify()` before generic `validate_terminal_state` routing


### FINDING_3: classify() omits bash same-cause-repeat guard for terminal failure classes
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: `classify()` omits the bash same-cause-repeat guard for terminal failure classes. When `--attempts-file` has a matching failed signature, Python promotes any repeat to `same-cause-repeat`; bash skips promotion when the class is `contract-failure` or `unrecoverable` (case20b). Step-6 contract stalls and adopted-issue-closed repeats misclassify and get wrong retry hints.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: In `classify()`, mirror bash `cmd_classify` (~line 1244): only apply same-cause-repeat when `klass` is not `contract-failure` and not `unrecoverable`; set `MATCHED_CLASSIFIER_PATTERN=same-cause-repeat` on that branch. Add pytest for case20b parity.


### FINDING_4: Plan omits pytest ports for bash classify bail-precedence fixtures case7g–7k6
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Concern**: The plan omits pytest ports for bash harness classify bail-precedence fixtures case7g–7k6 (dispatch-failure, protected-path vs stale evidence, submodule-restricted incl. case7k5). Deleting `test-stall-recovery-report-1.sh` drops the only tests proving submodule-restricted and dispatch-failure tokens beat transient grep on stale state-file evidence; pytest currently has one protected-path case and no submodule or dispatch-failure classify tests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Add explicit pytest cases mirroring case7g–7k6 (at minimum case7k2 protected-path+stale note, case7k5 submodule+stale note, case7k dispatch-failure argv-only) before harness deletion; name them in the plan pytest inventory


### FINDING_5: Converted Python CLI examples use wrong domain/verb ordering
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Concern**: Converted Python CLI examples put stall-recovery options before the verb. `python/cli.py` requires `cli.py <domain> <verb> [args...]`, so `stall-recovery --profile ... populate-sensitive-corpus` is rejected before `stall_recovery.py` runs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Generic: Change converted calls to `python3 "$ROOT/python/cli.py" stall-recovery populate-sensitive-corpus --profile generic ...` and `python3 "$ROOT/python/cli.py" stall-recovery compose-report --profile generic ...`



### FINDING_1: Generic-profile `classify()` omits terminal-state path
- **Reviewer(s)**: Cursor-Arch
- **Severity**: blocking
- **Concern**: Python `classify()` always follows the implement merge path (`ship-pr-state.sh` / `finalize-state.sh` / `session-env.sh`) and an implement-style signature seed. Bash routes `--profile generic` with `--primary-state-file` through `cmd_classify_generic_from_terminal_state`: it validates terminal state first, forces `STALL_TRACKING=true` and `RESUME_HINT=none`, hashes signatures with `profile`/`skill_label`, and sets `DISPATCHER` from `SOURCE_SCRIPT`. After the shell body is deleted, `/design` terminal-state classification and Tier A/B dedup signatures diverge from bash behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add a dedicated generic branch (validate_terminal_state first) mirroring bash:1091-1112 signature seed, SOURCE_SCRIPT-based DISPATCHER, fixed RESUME_HINT/STALL_TRACKING, and generic artifact naming; cover in test_stall_recovery.py per plan line 127


### FINDING_2: `init_attempts` / `record_attempt` lack bash append-and-containment parity
- **Reviewer(s)**: Cursor-Innovation, Cursor-Pragmatic, Codex-Generic
- **Severity**: blocking
- **Concern**: The plan targets retiring `stall-recovery-report.sh` while leaving `init_attempts` and `record_attempt` behaviorally incomplete. Current Python `record_attempt()` replaces the attempts file with flat `last_*` keys via `write_kvs()` instead of atomically preserving prior rows and appending `attempt.N.{class,signature,resume_hint,outcome,utc}`. Python `init_attempts()` also omits bash containment checks (`validate_tmpdir_write_file`), required `--attempts-file` handling, and stdout KVs (`ATTEMPTS_FILE`, `ATTEMPT_COUNT`). `compose_report()` `_attempts_table()` reads only `attempt.{idx}.*` rows, so harness cases 7/11/13/21, Step 18a Tier A "full attempts" reports, same-cause-repeat promotion, and multi-attempt history break after cutover even if the classify guard is fixed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Add an UPDATED stall_recovery.py step: rewrite record_attempt to increment attempt_count in place, append attempt.N.{class,signature,resume_hint,outcome,utc} rows without dropping prior attempt.* entries, and add pytest parity for case7 (two failed classifies promote same-cause-repeat) plus attempt_count=2 after alternate outcome
  - From Cursor-Pragmatic: Add a `record_attempt()` subsection mirroring bash `cmd_record_attempt` (lines 1309-1337): validate `--attempts-file` under tmpdir, increment `attempt_count`, append `attempt.N.{class,signature,resume_hint,outcome,utc}`, preserve prior rows; port harness case11/13/21 pytest coverage
  - From Codex-Generic: Add the minimal bash parity for init_attempts and record_attempt: validate attempts files under the tmpdir, preserve append-style attempt.N fields, emit the bash KVs, and port the existing init/record containment and stress cases before deleting the harnesses


