### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/tests/issue/test_execution_issues.py
- **Concern**: Normalized batch-match idempotency through flush_execution_issues_main is unspecified. Scenario: The plan bullet "Extend normalized-section idempotency coverage for the batch-match rerun:" has no requirements before the next item. The testing strategy still requires pytest parity for both idempotent rerun paths. The Bash harness per-section-probe case (seed flush, remove sentinel, rerun with batch-only match) will be deleted with no named pytest replacement. Acceptance "no Bash-only behavioral assertion remains" fails for that path.
- **Proposed resolution**: Flesh out the batch-match bullet to mirror sentinel-match: call flush_execution_issues_main twice after seeding normalized per-section hashes in the batch, drop the sentinel between runs, assert FLUSH_STATUS=already-flushed, RECORDS=0, unchanged NDJSON line count, and cleared source log. Port skills/implement/scripts/test-flush-execution-issues.sh:210-236 rather than relying on test_flush_execution_issues_already_flushed_when_batch_contains_normalized_sections alone (single call via flush_execution_issues, no rerun). ## Findings ### 1. **correctness** `python/tests/issue/test_execution_issues.py` — Normalized batch-match idempotency through `flush_execution_issues_main` is unspecified The plan lists sentinel-match idempotency through `flush_execution_issues_main` with concrete assertions, but the next bullet ("Extend normalized-section idempotency coverage for the batch-match rerun:") has no sub-requirements. The following item jumps straight to the normal append-failure case. The testing strategy still requires pytest equivalents for **both** idempotent rerun paths. The Bash harness `per-section-probe` block (`skills/implement/scripts/test-flush-execution-issues.sh:210-236`) covers a distinct scenario: seed a successful flush, remove `.execution-issues-flushed.sha`, rerun when normalized per-section hashes already exist in the batch, and assert `RECORDS=0` with no duplicate NDJSON. The nearby test `test_flush_execution_issues_already_flushed_when_batch_contains_normalized_sections` only exercises a single `flush_execution_issues` call, not a `flush_execution_issues_main` rerun after sentinel removal. Without an explicit batch-match rerun case, removing the Bash assertions leaves a parity hole relative to the issue acceptance criteria. **Suggested fix:** Complete the batch-match bullet with the same contract shape as sentinel-match (via `flush_execution_issues_main`): `FLUSH_STATUS=already-flushed`, `RECORDS=0`, unchanged batch line count, and post-rerun log disposition. Port the per-section-probe sequence from the current harness. --- ### [OUT_OF_SCOPE] **architecture** `Makefile` — Wire `test-flush-execution-issues` into a `test-harnesses-*` shard like `test-write-final-report` `test-write-final-report` sits on `test-harnesses-1` and runs both pytest and bash subtargets in CI lint. `test-flush-execution-issues` is a standalone target not referenced by any `test-harnesses-*` rule, so the new delegation smoke will run only when operators invoke the focused target manually. Aligning shard membership with the write-final-report pattern would close that CI gap; it is not required by this piece's acceptance text and matches pre-existing ownership, so it belongs in a follow-up rather than blocking this plan.



### FINDING_2:
- **Reviewer(s)**: Codex-Arch
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/tests/issue/test_execution_issues.py:70-110
- **Concern**: Prior accepted fix incomplete: both idempotency paths still permit function-level or line-count-only checks, rather than wrapper-visible `RECORDS=0` and byte-unchanged batches. This leaves G-Idem-1 and G-Wire-1 unverified.. Scenario: A rerun could rewrite or replace an existing same-count NDJSON batch, or emit a nonzero record count, while the planned assertions still pass.
- **Proposed resolution**: Call `flush_execution_issues_main` for both sentinel-match and normalized batch-match reruns, assert `FLUSH_STATUS=already-flushed` and `RECORDS=0`, and compare each batch's pre- and post-rerun bytes.



### FINDING_3:
- **Reviewer(s)**: Codex-Arch
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/tests/issue/test_execution_issues.py:154-169
- **Concern**: Prior accepted fix incomplete: the planned normal append-failure case omits an exact `RECORDS=0` assertion from the CLI output contract. This leaves the machine-consumed failure grammar insufficiently covered under G-Wire-1.. Scenario: A failure path could return exit 1 and `FLUSH_STATUS=failed` but report a stale or nonzero record count to callers.
- **Proposed resolution**: Parse `flush_execution_issues_main` stdout in the normal failure case and assert exact `FLUSH_STATUS=failed`, `RECORDS=0`, emitted readable `APPEND_LOG_FILE`, and exit code 1.



### FINDING_4:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/tests/issue/test_execution_issues.py:88-110
- **Concern**: FINDING_1 fix incomplete: normalized batch-match rerun assertions are missing. Scenario: The plan stops at "Extend normalized-section idempotency coverage for the batch-match rerun:" with no sub-bullets. That is not the same as test_flush_execution_issues_already_flushed_when_batch_contains_normalized_sections, which only covers a first call with a pre-seeded batch. The Bash harness per-section-probe path (seed flush, delete .execution-issues-flushed.sha, rerun) would lose parity and batch-only idempotency could regress while pytest stays green.
- **Proposed resolution**: Spell out the rerun scenario: seed via flush_execution_issues_main, remove the sentinel, restore the same issue body, rerun main; assert FLUSH_STATUS=already-flushed, RECORDS=0, unchanged NDJSON line count or contents, and cleared issue log.



### FINDING_5:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: minor
- **Focus area**: correctness
- **Location**: python/tests/issue/test_execution_issues.py:73-85
- **Concern**: Sentinel-match main idempotency omits explicit RECORDS=0 in the plan file section. Scenario: Round 1 accepted FINDING_1 required wrapper-visible RECORDS=0 for sentinel-match reruns. The sentinel-match bullets list already-flushed and unchanged batch content but not RECORDS=0 in stdout; only the Edge cases section mentions exact rerun counts, so an implementer can assert batch stability without parsing RECORDS=0 from flush_execution_issues_main output.
- **Proposed resolution**: Add RECORDS=0 to the sentinel-match flush_execution_issues_main sub-bullets, matching the Bash harness idempotent case and Edge cases. ### 1. **correctness** `python/tests/issue/test_execution_issues.py:88-110` — FINDING_1 fix incomplete: normalized batch-match rerun assertions are missing The revised plan addresses sentinel-match idempotency through `flush_execution_issues_main`, but the normalized batch-match bullet is truncated with no assertions. That leaves a real gap. `test_flush_execution_issues_already_flushed_when_batch_contains_normalized_sections` only exercises a **first** call when the NDJSON batch is already present. The Bash harness’s per-section-probe case is different: it seeds a successful flush, deletes `.execution-issues-flushed.sha`, restores the same issue text, and reruns. That path relies on `execution_issues_batch_contains_all_sections` when the sentinel is absent. Without an explicit pytest rerun scenario, that branch can regress while CI still passes. **Suggested revision:** Under the normalized-section bullet, specify the seed → remove sentinel → rerun flow and require `FLUSH_STATUS=already-flushed`, `RECORDS=0`, unchanged NDJSON batch, and cleared issue log via `flush_execution_issues_main`. ### 2. **correctness** `python/tests/issue/test_execution_issues.py:73-85` — Sentinel-match main idempotency omits explicit `RECORDS=0` in the plan file section Round 1 FINDING_1 (accepted) required wrapper-visible `RECORDS=0` for both idempotent rerun paths. The sentinel-match subsection lists status and batch stability but not `RECORDS=0` in captured stdout. Edge cases mention exact rerun counts, but the implementable file section should be self-contained. **Suggested revision:** Add `RECORDS=0` to the sentinel-match `flush_execution_issues_main` sub-bullets. --- **Already addressed (no re-raise):** Makefile chaining pytest + delegation smoke (FINDING_3/8); normal failure via `flush_execution_issues_main` with `_append_failure` parity (FINDING_2); success-path `APPEND_LOG_FILE` verification (FINDING_6). **Prior rejections respected:** `-k flush` naming (FINDING_4); parallel-test scope inflation (FINDING_7); failed-append diagnostic contract beyond `_append_failure` + `APPEND_LOG_FILE` split (FINDING_5).



### FINDING_6:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: minor
- **Focus area**: correctness
- **Location**: python/tests/issue/test_execution_issues.py:90-113
- **Concern**: Normalized batch-match idempotency has no stated assertions. Scenario: The blank plan bullet can leave the normalized rerun as a direct helper test, dropping wrapper-visible `RECORDS=0` and unchanged NDJSON verification when the Bash assertion is removed.
- **Proposed resolution**: Specify a `flush_execution_issues_main` normalized batch-match rerun that asserts exit 0, `FLUSH_STATUS=already-flushed`, `RECORDS=0`, and unchanged batch contents.



### FINDING_7:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/tests/issue/test_execution_issues.py
- **Concern**: The normalized batch-match idempotency pytest step is an empty bullet in the UPDATED section. Scenario: The plan line "Extend normalized-section idempotency coverage for the batch-match rerun:" has no assertions, yet acceptance and round-1 FINDING_1 require both idempotent rerun paths through `flush_execution_issues_main` with `FLUSH_STATUS=already-flushed`, `RECORDS=0`, unchanged NDJSON batch line count, and no new append. `test_flush_execution_issues_already_flushed_when_batch_contains_normalized_sections` still calls `flush_execution_issues` directly, so an implementer can satisfy the sentinel-match bullet and leave batch-match off the main CLI contract
- **Proposed resolution**: Complete that bullet explicitly: extend or add a `flush_execution_issues_main` case (pre-seeded batch and/or sentinel-removed rerun) asserting exit 0, `FLUSH_STATUS=already-flushed`, `RECORDS=0`, unchanged `execution-issues.ndjson` line count, and no new NDJSON record; keep source-log clearing behavior aligned with current Python ## 1. correctness — `python/tests/issue/test_execution_issues.py` The UPDATED pytest section ends a bullet at “Extend normalized-section idempotency coverage for the batch-match rerun:” with no requirements. The next bullet starts the normal failure case. Edge cases and testing strategy still require both idempotent rerun paths, and round-1 FINDING_1 was accepted for both sentinel-match and normalized batch-match parity through `flush_execution_issues_main`. Without a filled-in batch-match bullet, implementation can add sentinel-match `main` coverage and leave batch-match on the existing direct `flush_execution_issues` helper. That would miss the stated acceptance goal that every removed Bash behavioral assertion has a pytest equivalent on the CLI contract path. **Suggested revision:** Mirror the sentinel-match bullet for batch-match: `flush_execution_issues_main`, `FLUSH_STATUS=already-flushed`, `RECORDS=0`, unchanged NDJSON batch contents/line count, no new record; optionally a two-call sentinel-removed rerun if you want strict parity with the current Bash per-section-probe case.



### FINDING_8:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: minor
- **Focus area**: correctness
- **Location**: python/tests/issue/test_execution_issues.py:93-119
- **Concern**: Normalized batch-match idempotency coverage remains unspecified after the accepted parity finding. Scenario: The blank plan bullet can leave the existing direct helper test in place, so the focused suite never verifies CLI-visible `RECORDS=0` or unchanged batch content for this rerun path.
- **Proposed resolution**: Specify a `flush_execution_issues_main` normalized batch-match test that asserts `already-flushed`, `RECORDS=0`, and byte-unchanged NDJSON.



### FINDING_9:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/tests/issue/test_execution_issues.py
- **Concern**: Normalized batch-match idempotency bullet is truncated with no contract. Scenario: The plan line "Extend normalized-section idempotency coverage for the batch-match rerun:" has no sub-bullets; the next item starts the normal failure case. Acceptance requires both idempotent rerun paths and exact RECORDS/batch assertions. The bash harness per-section-probe (flush, remove sentinel, rerun) and unchanged-batch checks are not mapped to pytest. Implementers can ship with only sentinel-match main coverage and miss batch-match RECORDS=0 and unchanged-batch requirements.
- **Proposed resolution**: Add sub-bullets mirroring the sentinel-match block: call flush_execution_issues_main; assert FLUSH_STATUS=already-flushed, RECORDS=0, unchanged NDJSON batch line count or contents, cleared issue log, and no new append. Port the per-section-probe two-call flow (seed flush, delete sentinel, rerun) or extend the existing normalized-batch test with an explicit rerun and unchanged-batch assertion.



### FINDING_10:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: minor
- **Focus area**: correctness
- **Location**: python/tests/issue/test_execution_issues.py
- **Concern**: Round-1 failure contract still omits stdout RECORDS=0. Scenario: Accepted FINDING_2 required exact FLUSH_STATUS, RECORDS, APPEND_LOG_FILE, and exit-code assertions for the normal flush-failure path. The plan lists exit 1, FLUSH_STATUS=failed, and APPEND_LOG_FILE but not KV RECORDS=0 from flush_execution_issues_main. A regression that omits or mis-emits RECORDS on failure could pass the written plan.
- **Proposed resolution**: Add RECORDS=0 to the normal failure-case assertions alongside exit 1 and FLUSH_STATUS=failed. ## Findings ### 1. **correctness** — Normalized batch-match idempotency bullet is incomplete The plan fully specifies sentinel-match idempotency through `flush_execution_issues_main` (`FLUSH_STATUS=already-flushed`, unchanged batch, `RECORDS=0`). The normalized batch-match bullet ends at a colon and immediately jumps to the failure case. That leaves a gap against piece acceptance ("both idempotent rerun paths") and the bash harness `per-section-probe` block in `skills/implement/scripts/test-flush-execution-issues.sh` (lines 210–236): seed flush, remove sentinel, rerun, assert `RECORDS=0` and unchanged batch. `test_flush_execution_issues_already_flushed_when_batch_contains_normalized_sections` calls the library helper once with a pre-seeded batch; it does not exercise `flush_execution_issues_main` KV output or a rerun with unchanged-batch checks. ### 2. **correctness** — Normal failure case should assert `RECORDS=0` on stdout Round 1 accepted FINDING_2 for full CLI contract on the normal (non-safety-net) append failure. The revised plan covers exit code, `FLUSH_STATUS=failed`, `APPEND_LOG_FILE`, and `_append_failure` text, but not stdout `RECORDS=0`, which `flush_execution_issues_main` emits on failure (`python/larch/issue/execution_issues.py` lines 236–242). ## Prior-round ledger - **FINDING_1, 2, 3, 8**: Plan text now addresses Makefile dual-lane, main-path failure parity, and sentinel idempotency; finding 2 is only partially closed (`RECORDS` on failure). - **FINDING_6**: Addressed via success-path `APPEND_LOG_FILE` requirement. - **FINDING_4, 5, 7**: Rejected; not re-raised. - **OOS items**: `test-flush-execution-issues.md` rewrite is in firm files; parent `flush-execution-issues.md` stale harness claims remain out of firm scope for this piece. ## Accepted coverage that looks complete Makefile dual-lane (`pytest` + delegation smoke), empty/single/multi success paths via main, sentinel idempotency through main, normal failure `_append_failure` parity (minus `RECORDS` KV), safety-net separation, delegation smoke scope, and contract doc rewrite are otherwise aligned with scope and minimum-change intent.



### FINDING_11:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: minor
- **Focus area**: correctness
- **Location**: python/tests/issue/test_execution_issues.py
- **Concern**: Normalized-section idempotency coverage remains unspecified after the empty plan bullet. Scenario: The test may exercise the helper rather than the CLI and miss wrapper-visible RECORDS=0 or a changed NDJSON batch on a normalized batch-match rerun
- **Proposed resolution**: Require a flush_execution_issues_main test that asserts already-flushed, RECORDS=0, and byte-identical NDJSON contents for the normalized-section rerun



### FINDING_12:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: minor
- **Focus area**: correctness
- **Location**: python/tests/issue/test_execution_issues.py
- **Concern**: Normal append-failure coverage omits exact RECORDS and emitted APPEND_LOG_FILE assertions. Scenario: The failure test can pass while the CLI reports a nonzero record count or emits an absent or wrong append-log path
- **Proposed resolution**: Parse CLI stdout and assert FLUSH_STATUS=failed, RECORDS=0, and APPEND_LOG_FILE equals the readable captured-stderr log, plus exit 1



