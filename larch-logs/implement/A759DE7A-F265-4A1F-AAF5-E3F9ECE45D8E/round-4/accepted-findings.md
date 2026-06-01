### FINDING_1: merge_pr MERGE_RESULT literals not exercised in tests
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `test_merge_pr_can_emit_each_literal` only checks membership in `MERGE_RESULTS` (or is otherwise tautological) and does not drive `merge_pr` to emit each of the eight literals. Five or more result paths (`admin_merged`, `ci_not_ready`, `version_already_published`, `policy_denied`, `admin_failed`, etc.) lack integration coverage, so Phase 7 routing and merge-state regressions can ship undetected.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_12: New-PR path pushes without upstream (`-u`)
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: New-PR path uses `push_branch` without `-u` while `create-pr.sh` uses `git push -u origin HEAD`. First push via explicit refspec may succeed but leave no upstream; a later plain `git push` fails with no upstream branch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


### FINDING_13: `flush_logs_pre` omits token/timing ledger exports
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: `flush_logs_pre` skips `token-report.sh` / `timing-report.sh` and session-env ledger exports, only scraping sidecar JSON. Pre-push flush can emit empty token/timing batches when ledger data exists but sidecars were never written.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


### FINDING_14: `tracking_issue` rename truncates before redaction only
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: Rename truncates before redaction but not after, unlike `tracking-issue-write.sh`. Post-redaction title can exceed GitHub’s 256-character limit and fail `gh issue edit`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


### FINDING_15: Missing positive / K1-style flush recovery through `merge_pr`
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Flush recovery is tested on `_flush_recoverable` (unit predicate) but not through full `merge_pr` / `_ensure_head_matches_pr` with successful `force_push_recovery` or happy-path HEAD-ahead-of-PR-OID scenarios; integration regressions can pass unit tests only.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_16: `_version_race_gate` untested
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `_version_race_gate` has no unit tests; version race on `origin/main` could emit wrong result or proceed toward double-merge undetected.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_17: MERGED noop / `admin_merged` preservation untested
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: MERGED PR noop path does not test `admin_merged` preservation from `state_file`; re-run after admin merge could remap to `merged` and confuse the Phase 7 state machine.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_2: Bash merge parity missing K1/P1/N1/N2a scenarios
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `python/test_merge_bash_parity.py` only covers BEHIND (or similar narrow cases) and omits plan-required K1/P1/N1/N2a scenarios from `scripts/test-merge-pr.sh`. Flush-recovery classification and `MERGE_RESULT=` stdout can drift between Python `merge_pr` and `merge-pr.sh` without CI failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_20: Post force-push CI re-check untested
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Post force-push CI re-check is untested; pending CI after recovery could merge when bash would return `ci_not_ready`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_25: `run_logs` test misplaced in `test_merge.py`
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: A `run_logs` test lives in `test_merge.py`, misleading coverage maps when triaging merge failures.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_26: `ensure_pr` / `update_pr_body` Mermaid sanitization gap
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: important
- **Concern**: `update_pr_body` redacts only; `ensure_pr` existing-PR path can publish unsanitized Mermaid. Phase 7 or a buggy caller passing raw agent markdown with unsafe Mermaid to `ensure_pr` would be rejected by `compose_pr_body` but still pushed via `update_pr_body`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


### FINDING_30: Merged-PR noop skips `flush_logs_post` when `post_flush=False`
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Merged-PR noop skips `flush_logs_post` when `post_flush=False` on the first probe. After merge but before post-flush, a crash and re-run seeing MERGED can return without `flush_logs_post`, leaving a partial manifest.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_31: `gh.pr_view` `ShipError` swallowed; merge continues
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-merge-state-parity-output.txt
- **Severity**: important
- **Concern**: `_merge_noop_if_pr_closed` catches `ShipError` from `gh.pr_view` and returns `None`, so transient or hard `pr view` failure is indistinguishable from “PR still open” and `merge_pr` proceeds through flush/merge instead of idempotent `merged` / `admin_merged` (or error). Post-merge re-entry when `pr view` fails can attempt merge again.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From dyn-merge-state-parity-output.txt: Fail closed on `pr_view` failure (return `MERGE_RESULT_ERROR` with a redacted diagnostic), or retry `pr_view` with the same transient budget used elsewhere before continuing; do not fall through to a merge attempt when merge-state cannot be read.


### FINDING_32: `flush_logs_pre` with `cwd=None` still attempts git commit
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-flush-contract-output.txt
- **Severity**: important
- **Concern**: When `flush_logs_pre` is called with `cwd=None` (as `merge_pr` allows), copying the run tree into the repo is skipped but `_larch_log_commit` still runs against the process cwd. Pre-merge flush can commit stale or unrelated `larch-logs/` content without publishing tmpdir batches, while appearing to succeed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From dyn-flush-contract-output.txt: Require an explicit repo `cwd` before attempting commit (fail-closed `RefreshSkip`), or resolve/copy to the repo root when `cwd` is omitted so the pre-flush publish+commit steps are atomic.


### FINDING_33: Manifest recovery picks newest implement dir by mtime without `RUN_ID`
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Manifest recovery picks the newest `implement/` child by mtime without validating `RUN_ID`; multiple run dirs in one tmpdir can recover the wrong `run_id` and corrupt batches/manifest.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_35: Idempotent merged path loses `admin_merged` when state missing
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Idempotent merged path infers `admin_merged` only from state `MERGE_RESULT`; if state is lost after admin merge, re-entry reports `merged` not `admin_merged`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_36: `_ensure_head_matches_pr` treats empty/missing local HEAD as success
- **Reviewer(s)**: dyn-merge-state-parity-output.txt
- **Severity**: important
- **Concern**: `_ensure_head_matches_pr` treats failed/empty `git rev-parse HEAD` (`try_rev_parse` returns `None` or `""`) as success via `if not local_head or local_head == state.head_ref_oid`, skipping bash-parity mismatch handling. After CI/admin gates, `merge_pr` can continue into `_version_race_gate` and `_attempt_merge` without establishing local HEAD matches PR head OID.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-merge-state-parity-output.txt: Only short-circuit when `local_head` is non-empty and equals `state.head_ref_oid`; if `local_head` is missing/empty, return `MergeResult(result=MERGE_RESULT_ERROR, error=...)` (mirror bash’s mismatch message, or a dedicated “could not resolve local HEAD” diagnostic) before flush recovery or the version gate.


### FINDING_37: State file read raises on unreadable / invalid UTF-8
- **Reviewer(s)**: dyn-flush-contract-output.txt
- **Severity**: latent
- **Concern**: `_read_state_kv` only treats a missing path as empty; unreadable or non–UTF-8 `ctx.state_file` raises through `read_state_kv` into `merge._merge_noop_if_pr_closed`, crashing idempotent merge re-entry instead of safe empty sentinel + `gh pr view` classification.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-flush-contract-output.txt: Wrap state-file reads in a narrow try/except (or read with `errors="replace"`) and return `""` on any read/decode failure, matching the fail-closed “missing file → empty” behavior `refresh-run-logs.sh` assumes for probes.


### FINDING_38: `flush_logs_post` redaction `ShipError` uncaught in `merge_pr`
- **Reviewer(s)**: dyn-flush-contract-output.txt
- **Severity**: important
- **Concern**: `flush_logs_post` can raise `ShipError` from `_redact_batch_payload` during token/timing rendering; `merge_pr` calls `_post_flush` on terminal paths without catching it, aborting with an uncaught exception instead of a `MergeResult`, breaking the Phase 7 frozen-dataclass routing contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-flush-contract-output.txt: Either catch `ShipError` inside `flush_logs_post` and return a `RefreshSkip`/`PostFlushResult` failure, or wrap `_post_flush` in `merge_pr` and map flush failures to `MergeResult(result=MERGE_RESULT_ERROR, error=...)`.


### FINDING_4: `commit-failed` from `flush_logs_pre` hard-aborts `merge_pr`
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: When `flush_logs_pre` returns `commit-failed`, Python `merge_pr` aborts merge, while current `ship-pr.sh` treats refresh commit failure as non-fatal (`|| true`) and still proceeds to `merge-pr.sh`. A transient log commit failure during pre-merge flush blocks merge in Python though bash would continue.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_7: `LEGACY_TRACKING_PREFIXES` unused dead config
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `LEGACY_TRACKING_PREFIXES` in `python/config.py` is unused dead config that misleads readers about rename behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


### FINDING_9: No-op `time.sleep(0)` in `pr.py`
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `time.sleep(0)` adds noise without behavior and confuses readers about retry timing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


