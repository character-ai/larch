Normalizing the supplied reviewer findings into one merged list (first-seen IDs, severity max on merge, verbatim revision bullets where provided).

### FINDING_1: merge_pr MERGE_RESULT literals not exercised in tests
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `test_merge_pr_can_emit_each_literal` only checks membership in `MERGE_RESULTS` (or is otherwise tautological) and does not drive `merge_pr` to emit each of the eight literals. Five or more result paths (`admin_merged`, `ci_not_ready`, `version_already_published`, `policy_denied`, `admin_failed`, etc.) lack integration coverage, so Phase 7 routing and merge-state regressions can ship undetected.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_2: Bash merge parity missing K1/P1/N1/N2a scenarios
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `python/test_merge_bash_parity.py` only covers BEHIND (or similar narrow cases) and omits plan-required K1/P1/N1/N2a scenarios from `scripts/test-merge-pr.sh`. Flush-recovery classification and `MERGE_RESULT=` stdout can drift between Python `merge_pr` and `merge-pr.sh` without CI failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_3: Duplicated `gh` PR merge-state JSON parsing in `_refresh_pr_info`
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: `_refresh_pr_info` in `python/merge.py` duplicates `gh.pr_merge_state` JSON parsing; fixes to merge-state retries or field names can land in one module but not the other.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_4: `commit-failed` from `flush_logs_pre` hard-aborts `merge_pr`
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: When `flush_logs_pre` returns `commit-failed`, Python `merge_pr` aborts merge, while current `ship-pr.sh` treats refresh commit failure as non-fatal (`|| true`) and still proceeds to `merge-pr.sh`. A transient log commit failure during pre-merge flush blocks merge in Python though bash would continue.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_5: Duplicated PR checks logic vs `ci_monitor`
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: `python/gh.py` duplicates PR checks logic vs `ci_monitor._gh_pr_checks`; CI monitor and merge can disagree on whether checks passed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_6: `run_logs.py` multi-responsibility module size
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: `run_logs.py` is a large multi-responsibility module, making it harder to test manifest vs execution-issue vs commit paths independently.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_7: `LEGACY_TRACKING_PREFIXES` unused dead config
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `LEGACY_TRACKING_PREFIXES` in `python/config.py` is unused dead config that misleads readers about rename behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_8: `git.remotes()` unused; push hardcodes `origin`
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: `remotes()` was added in `python/git.py` but is unused; `select_push_remote` / push paths always use `origin`. Behavior may match bash today but suggests an incomplete fork-aware upstream plan or dead API surface.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_9: No-op `time.sleep(0)` in `pr.py`
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `time.sleep(0)` adds noise without behavior and confuses readers about retry timing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_10: Execution-issue NDJSON substring dedup fragility
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: Substring-based dedup for execution-issue NDJSON can duplicate or skip issues when JSON formatting differs on re-flush.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_11: Double redaction on PR body update
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: PR body update may redact twice; truncation/redaction failure modes can differ between passes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

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

### FINDING_18: UNKNOWN merge-state retry loops untested
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: UNKNOWN retry loops are untested; flapping `mergeStateStatus` could spuriously error or merge without exercising backoff.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_19: Non-ancestor flush predicate untested
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Non-ancestor flush recoverability predicate is untested; invalid flush stack might be treated as recoverable or vice versa.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_20: Post force-push CI re-check untested
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Post force-push CI re-check is untested; pending CI after recovery could merge when bash would return `ci_not_ready`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_21: `_atomic_write` not covered in tests
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: `_atomic_write` is not covered despite plan requirement; partial writes during manifest update could corrupt recovery state.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_22: Cursor sidecar normalization untested
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: Cursor sidecar normalization is untested; token scrape could silently drop fields.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_23: Shallow `step9a1` / `capture_session_transcript` test coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: `step9a1` and `capture_session_transcript` are shallowly tested; manifest `steps_ran.step9a1` and transcript batches could regress in production flush.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_24: Multi-state rename and 256-char truncation tests missing
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: Multi-state rename and 256-character truncation paths are untested; long titles can yield wrong issue titles or broken prefixes.
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

### FINDING_27: Unconstrained `state_file` path for merge/flush probes
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `state_file` path is unconstrained when reading `MERGE_RESULT` / `RUN_ID` / etc.; wrong or malicious `state_file` can skip or alter `flush_logs_pre` behavior (e.g., forged post-merge `MERGE_RESULT`).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_28: `TRANSCRIPT_PATH` from env source file not allowlisted
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Python invokes `capture-session-transcript.sh` with an env source file; bash trusts `TRANSCRIPT_PATH` from that file. Same-UID tampering could point capture at sensitive files; redaction may not remove all material.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_29: Admin-first `gh pr merge --admin` token scope
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: Admin-first merge uses `--admin` by design; compromised or over-scoped `gh` token can admin-merge despite branch protection.
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

### FINDING_34: Bash helper exit codes ignored during flush
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Exit codes from `write-final-report.sh` and `capture-session-transcript.sh` are ignored; helpers can fail while flush still commits partial log state before merge.
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

### FINDING_39: [OUT_OF_SCOPE] Branch mixes non–Phase-5 commits
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Non–Phase-5 commits (e.g., upgrade-larch/version noise) are mixed into the branch, making Phase 5 regressions harder to spot in review and CI attribution.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_40: [OUT_OF_SCOPE] `rebase.py` changes outside Phase 5 plan
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: Large `rebase.py` changes are not in the Phase 5 plan; unrelated rebump API changes ride with merge/logging port work.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_41: [OUT_OF_SCOPE] Push tests use stale argv tuples
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: Push tests use stale argv tuples; index-based runner masks refspec regressions—tests would not detect if `push_branch` changed `git` argv.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_42: [OUT_OF_SCOPE] Inline-triage test does not exercise counting
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: Inline-triage test uses a JSON accepted file so `non_security_count` stays 0; test passes without exercising inline-triage counting.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_43: [OUT_OF_SCOPE] `pr_checks_all_pass` text fallback (bash parity)
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `pr_checks_all_pass` text fallback inherited from `merge-pr.sh`; misleading `gh` checks text could contribute to merge when JSON path fails—same as bash; tighten only with coordinated `merge-pr.sh` change.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_44: [OUT_OF_SCOPE] `capture-session-transcript.sh` `TRANSCRIPT_PATH` not root-confined
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `TRANSCRIPT_PATH` is not confined to session/project roots in bash (pre-existing); arbitrary file read into transcript pipeline.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_45: [OUT_OF_SCOPE] Bash `ship-pr.sh` refresh vs Python in-merge flush contract
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: Bash merge path does not call refresh before `merge-pr.sh`; Phase 7 must define whether Python in-merge flush replaces or duplicates push-time refresh.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_46: [OUT_OF_SCOPE] Comprehensive bash merge harness vs Python parity gap
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: `scripts/test-merge-pr.sh` remains comprehensive while Python parity is the gap; Phase 7 cutover risk is Python-specific, not bash regression.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

---

**Merge notes (diagnostic, not votes):** Input items 61–63 and duplicate OOS echoes of FINDING_1–2 were subsumed into in-scope FINDING_1–2 or dropped as non-actionable positive observation (61). Dyn slots contributed substantive fix text only where quoted above; other slots uniformly said “Address the concern above.” Total: **38** normalized blocks (**32** in-scope, **6** `[OUT_OF_SCOPE]`).
