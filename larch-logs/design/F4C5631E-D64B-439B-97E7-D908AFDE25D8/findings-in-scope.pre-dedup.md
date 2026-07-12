### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Focus area**: architecture
- **Location**: python/larch/bgjob/adapt.py
- **Concern**: [SCOPE-REDUCTION] Plan contradicts itself on child argv: Approach accepts the command after `--`, but adapt.py mandates injecting adapter-owned flags and merge-env into child argv. Scenario: Step adapters pass different child argv shapes. step-5-review.sh:12-16 exits 2 on unknown args, so injecting `--merge-result-env` breaks that script on conversion. step-6-entry.sh already passes merge flags in the caller argv. Daemon-side merge already comes from JobSpec.merge_result_env.
- **Proposed resolution**: Limit adapt to passing the caller argv after `--` unchanged into JobSpec.command. Own only derived merge-result-env for JobSpec/daemon publication. Drop mandatory child-argv flag injection from adapt.py and tests unless a future conversion explicitly needs it.



### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/bgjob/adapt.py
- **Concern**: State-1 DONE short-circuit does not define what makes a result env valid. Scenario: A zero-byte or KV-free `$TMPDIR/bgjob/<step>.result.env` can make adapt emit `BGJOB_STATUS=DONE` without `BGJOB_RC`, skipping launch even when the registry row is dead or fail-closed. Callers that gate on `BGJOB_RC=0` then stall instead of starting a fresh job.
- **Proposed resolution**: Pin completed-result detection to the same regular-file/symlink checks as wait plus required keys (`BGJOB_RC` and matching `STEP`) before any DONE return. Treat empty or incomplete files as absent and continue the locked state machine.



### FINDING_3:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: minor
- **Focus area**: correctness
- **Location**: python/larch/bgjob/cli.py
- **Concern**: adapt_main does not require the same `--` child-arg stripping contract as start_main. Scenario: start_main strips a leading `--` before validating `args.command` (cli.py:61-64). adapt_main only says it parses the command after `--`; a copy-paste miss leaves `args.command=["--", "bash", ...]`, which makes Popen fail or run the wrong argv.
- **Proposed resolution**: In adapt_main, mirror start_main exactly: if `args.command` is non-empty and first token is `--`, drop it before missing-command validation and before handing argv to adapt. ### 1. architecture — [SCOPE-REDUCTION] child argv injection (`python/larch/bgjob/adapt.py`) The Approach says adapt accepts the child command after `--`. The `adapt.py` section then requires constructing child argv with adapter-owned flags and a merge-env path. Those conflict. Daemon merge already flows through `JobSpec.merge_result_env` and `daemon.write_result()`. Child-side `--merge-result-env` is only for scripts that write merge KVs during child execution, and callers already pass it when needed (for example `step-6-entry.sh:344-350`). `step-5-review.sh` accepts only `--bgjob-child` and errors on any other flag (`step-5-review.sh:12-16`). Mandating injection in `adapt` adds complexity and blocks later conversions that mirror step-5. Drop it from the firm plan; keep merge ownership on the JobSpec/daemon path only. ### 2. correctness — undefined “valid result” for state-1 DONE (`python/larch/bgjob/adapt.py`) State 1 returns DONE when a “valid result env already exists,” but validity is never defined. `wait._read_result()` treats any regular file with parseable (including empty) KVs as DONE. An empty stale `.result.env` left after a crash can make `adapt` short-circuit to DONE while a dead registry row is fail-closed under states 5/8, so no fresh launch runs. Pin DONE short-circuit to the same file safety checks as wait plus required keys (`BGJOB_RC`, matching `STEP`). Treat empty or incomplete files as no result. ### 3. correctness — missing `--` strip in `adapt_main` (`python/larch/bgjob/cli.py`) `start_main` strips a leading `--` from `args.command` before validation and dispatch (`python/larch/bgjob/cli.py:61-64`). The plan does not require the same rule for `adapt_main`. Orchestrator fences use `bgjob … -- <child>`; without the strip, `adapt` can forward `["--", …]` to Popen and fail startup. Mirror `start_main`’s strip in `adapt_main`. --- **Prior ledger note:** Round-1 accepted items (`_MACHINE_STDOUT_KEYS`, `clone_path`, child PGID on re-attach, fork-safe lock, pre-`start_daemon` result re-check, child-only-live fail-closed, malformed-registry fail-closed, nonzero `start_daemon` → `BGJOB_ERROR`) appear addressed in the current plan. I did not re-raise them. FINDING_17 (uniform child argv injection) is reopened with new evidence from `step-5-review.sh`’s unknown-argument handling. Rejected/neutral/OOS ledger rows on merge-env location, owner-flag enumeration, blocking `flock`, dead-entry operator recovery, plugin-root parser boundary, and atomic unlink races were not repeated.



### FINDING_4:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/bgjob/adapt.py
- **Concern**: [SCOPE-REDUCTION] Fresh-launch merge-env init must be create-if-absent, not unconditional truncate. Scenario: The plan says to initialize merge env atomically before every fresh launch. Live adapters already write identity or seed KVs into the derived bgjob merge path before `bgjob start` (for example `skills/implement/scripts/step-6-entry.sh:327-337` and `skills/implement/scripts/run-step-checks.sh:378-386`). `bgjob start` never truncates that file today. If `adapt` always reinitializes on launch, later conversions lose preseeded merge rows and daemon result merge omits required KVs.
- **Proposed resolution**: Only create the derived merge file when it is missing: validate path safety, then atomic empty write with mode 0o600. If a regular file already exists at the derived path, leave its contents intact. Restrict re-attach paths from touching merge env. State this explicitly in Approach and `adapt.py`, and add a test that preseeds merge KVs then calls `adapt` and asserts the file is unchanged.



### FINDING_5:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: minor
- **Focus area**: correctness
- **Location**: python/larch/bgjob/adapt.py
- **Concern**: DONE branch must match `wait_once` stdout row parity. Scenario: The plan requires returning through the `BGJOB_STATUS=DONE` contract, but tests only require DONE without a launch. `python/larch/bgjob/wait.py` prints `BGJOB_STATUS=DONE` plus every result-env row (`python/tests/bgjob/test_wait.py`). Emitting DONE alone breaks callers that parse `BGJOB_RC` and merged keys after a completed job.
- **Proposed resolution**: Reuse the same emission helper as `wait_once` (or call into it): print `BGJOB_STATUS=DONE` followed by all readable result-env KVs on exit 0. Extend `python/tests/bgjob/test_bgjob_adapt.py` to assert `BGJOB_RC` and at least one merged custom key, mirroring `test_wait_done_prints_result_rows`.



### FINDING_6:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: minor
- **Focus area**: risk-integration
- **Location**: python/larch/bgjob/adapt.py
- **Concern**: Per-run-step adapter lock must block, not fail fast on contention. Scenario: The plan requires lock serialization and a concurrency regression, but it does not pin blocking semantics. `python/larch/implement/dispatch_step2.py` uses `LOCK_NB`, which makes a second caller error instead of waiting. Non-blocking acquisition can also race into duplicate `start_daemon` forks before either row is visible.
- **Proposed resolution**: Use blocking `fcntl.flock(..., LOCK_EX)` for the per-run-and-step lock (same posture as `python/larch/report/progress_file.py:413`). Hold it through the final result check and launch decision, then release before `start_daemon` via fork-safe close or `FD_CLOEXEC`. Document blocking semantics in `adapt.py` and keep the concurrent second-caller test.



### FINDING_7:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/bgjob/adapt.py (planned)
- **Concern**: Adapter-owned merge-env path is only specified for child-argv construction, not for the JobSpec passed to the daemon. Scenario: The daemon merges result rows from `spec.merge_result_env` in `daemon.write_result`; it does not inspect the child command's `--merge-result-env` flag. If adapt leaves `_build_spec`'s field unset while injecting the path only into child argv, the final `BGJOB_STATUS=DONE` result omits the accumulated merge rows and fails the feature's merge-result-env acceptance
- **Proposed resolution**: Explicitly assign the validated adapter merge-env path to `JobSpec.merge_result_env` before calling `daemon.start_daemon`, and test the resulting DONE output with preseeded and child-written merge rows



