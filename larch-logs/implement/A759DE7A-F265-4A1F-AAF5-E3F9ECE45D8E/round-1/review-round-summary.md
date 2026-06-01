# Review Round 1

- Mode: `diff`
- 36 accepted, 4 rejected (4 exonerated)

## Accepted Findings

### FINDING_1: Merge tests lack eight-literal table, flush recovery, skip modes, and Python–bash parity
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Merge unit tests and the bash parity harness do not exercise `merge.merge_pr` across the eight `MERGE_RESULT` literals, flush-recovery predicates (K1/P1/N1/N2a), skip modes, or admin routing. CI can stay green while Python merge classification diverges from `merge-pr.sh` and `scripts/test-merge-pr.sh`, so Phase 7 may mis-route merge outcomes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_10: Push stderr de-duplication branch is a no-op
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Stderr de-duplication on retries does not skip repeated stderr; comment implies behavior that is not implemented.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


### FINDING_11: Dead `steps_ran` assignment after `update_manifest` in flush
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: No-op assignment after `update_manifest` adds noise; `steps_ran` is not updated when flush steps run.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


### FINDING_12: State-file `RUN_ID` validated but `ctx.run_id` used for batches and commits
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: When state-file `RUN_ID` and `ctx.run_id` differ, token/timing batches, flush commits, and subject prefixes use the wrong run directory.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_13: Lifecycle HTML comment uses wrong marker prefix
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: Python writes `larch:lifecycle:` instead of `larch:lifecycle-marker:` per `tracking-issue-write.sh`, so marker search and operator tooling miss lifecycle comments.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


### FINDING_14: Merge skip modes return `MERGE_RESULT_ERROR` without dedicated semantics
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: Skip modes surface as generic merge errors. Phase 7 driver may treat intentional skips as hard failures unless skip cases are typed, documented, and tested.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_15: No tests for `git.force_push_recovery` shared by merge and pr
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Lease-arg, race-retry, dirty worktree, and explicit lease OID paths are untested. Bugs can yield perpetual `diverged_retry_failed` after log flush with no CI signal.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_16: New `gh.pr_merge` / `pr_merge_state` / `pr_edit_body` paths untested
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Phase 5 gh additions lack argv/body-file tests; `--admin` or admin-first merge regressions may fail silently.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_17: `test_run_logs.py` missing happy-path flush commit and post-merge skip matrix
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Happy-path `flush_logs_pre` commit, `step9a1`/transcript guards, and parametrized post-merge skip cases (`merged`, `admin_merged`, `already_merged`) are incomplete. `_larch_log_commit` regressions can skip git add/commit undetected.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_18: `test_tracking_issue.py` missing upsert idempotency, truncation, marker, redaction tests
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Title truncation, invalid markers, upsert marker behavior, and redaction fail-closed paths lack coverage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_19: `test_oos.py` missing disposition fail paths and markdown parity
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Fail paths (`repo_unavailable`, filed-URL, rejected-marker, `non_sec>0` without coverage) are untested; accepted OOS can pass gate in CI without exercising real markdown fixtures.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_2: `flush_logs_pre`/`post` omit major `refresh-run-logs.sh` steps
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Pre/post flush paths are stubs: execution-issues token/timing reports, transcript capture, `step9a1`, and related refresh steps are missing. Phase 7 push/merge boundaries can commit logs without execution-issue NDJSON, final-summary inputs, or real token/timing data that bash always refreshes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_20: `test_pr_body_bash_parity.py` mermaid parity is one-way and incomplete
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Only conditional one-way checks; full reason-token sets (e.g. `br-in-participant-alias`, `dollar-in-participant-alias`) are not parametrized, so Python/bash disagreements can pass CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_21: `compose_pr_body` lacks fail-closed on `[content truncated]` / PEM guard
- **Reviewer(s)**: cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `compose_pr_body` redacts but does not raise on truncation marker like `update_pr_body`. PEM-heavy bodies could publish via `ensure_pr` → `pr_create` while the update path would reject.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_22: `ensure_pr` calls `gh.pr_edit_body` directly, bypassing fail-closed `update_pr_body`
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: important
- **Concern**: Existing-OPEN-PR `Closes`-link updates can publish bodies that `update_pr_body` would reject. Route through `pr_body.update_pr_body` or a shared fail-closed helper.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


### FINDING_24: `plan_goals_file` read is unconstrained (`path_under_repo` unused)
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Phase 7 driver with a crafted path could read arbitrary readable files into PR summary. Validate paths under repo root before read.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


### FINDING_25: `compose_pr_body` embeds mermaid without requiring `sanitize_fragment` ok
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Rejected-fragment-class content could be embedded in public PR bodies if orchestrator passes unsanitized input.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


### FINDING_26: Inconsistent push remote between existing-PR and new-PR paths
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: Existing-PR path uses `origin` only; new-PR path uses fork-aware selector, so one run could push to different remotes depending on PR existence (after fork policy is fixed, unify selection).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


### FINDING_27: `_flush_recoverable` raises `ShipError` when `git log` fails
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-bash-python-parity-output.txt
- **Severity**: important
- **Concern**: `git.log_subjects` uses `_ensure_success` and aborts `merge_pr` on log failure; bash treats failure as non-recoverable without crashing. Invalid OID/transient errors should return `MERGE_RESULT=error`, not raise.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From dyn-bash-python-parity-output.txt: Use a non-throwing log helper (e.g. `try_log_subjects` returning an empty tuple on failure) inside `_flush_recoverable`, matching Bash fail-closed “not recoverable” semantics.


### FINDING_28: Manifest recovery picks lexicographically first `implement/` child
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Multiple run dirs in tmpdir can recover the wrong `run_id` and corrupt manifest/batch paths. Prefer `ctx.run_id`, then state `RUN_ID`, then newest mtime.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_29: Rejected OOS tag count scans full body, not rejected section only
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Prose mentioning `OOS_N` outside the rejected section can inflate counts and falsely pass the disposition gate vs bash section-boundary awk.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_3: Tracking-issue upserts append instead of marker-idempotent updates
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `upsert_summary` and `upsert_token_report` only append comments. Repeated finalize/flush runs spam duplicate final-summary and token-report comments on the tracking issue instead of replacing marker-keyed comments like `tracking-issue-summary.sh`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_30: `sanitize_fragment` with `from_md=False` skips fence extraction vs bash
- **Reviewer(s)**: dyn-bash-python-parity-output.txt
- **Severity**: important
- **Concern**: Fenced `` ```mermaid `` input with default `from_md=False` is treated as one body; diagram-type checks are skipped and unsafe inner content can return `status="ok"` while bash rejects. Mirror bash auto-detection when the first non-blank line is a mermaid fence opener.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-python-parity-output.txt: Mirror Bash auto-detection before the `from_md` branch (if first non-blank line is `` ```mermaid ``, set `from_md=True`), or default to extraction when fence markers are present; add a parity test piping fenced markdown through both implementations.


### FINDING_31: Pre-push flush does not copy tmpdir run tree into repo before commit
- **Reviewer(s)**: dyn-flush-split-invariant-output.txt
- **Severity**: important
- **Concern**: `flush_logs_pre` renders under `ctx.tmpdir/larch-logs/implement/<run_id>/` but `_larch_log_commit` `git add`s repo `larch-logs/` without publishing tmpdir artifacts, breaking parity with `larch-log.sh commit` and risking stale or unrelated log commits.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-flush-split-invariant-output.txt: Port the `larch-log.sh commit` copy/publish steps (tmpdir run dir → `larch-logs/implement/<run_id>`, scoped `git add`/`status`/`commit` on that rel path only, `no-changes` short-circuit) inside `_larch_log_commit` or a dedicated helper; only call `git.commit` when the scoped pathspec has staged changes.


### FINDING_32: Pre-push `git add` scopes entire `larch-logs/` not run-id pathspec
- **Reviewer(s)**: dyn-flush-split-invariant-output.txt
- **Severity**: important
- **Concern**: Staging top-level `larch-logs` is broader than bash `git add -- larch-logs/implement/$run_id`, so concurrent or multi-run dirty paths could be swept into a flush commit.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-flush-split-invariant-output.txt: Scope all pre-push git operations to `larch-logs/implement/{ctx.run_id}` (validate `run_id` with `validate_run_id_slug` first), matching `scripts/larch-log.sh` lines 534–545.


### FINDING_33: `merge_pr` ignores most `flush_logs_pre` skip reasons
- **Reviewer(s)**: dyn-flush-split-invariant-output.txt
- **Severity**: important
- **Concern**: Only `commit-failed` aborts merge; other skips (`state-file-missing-fail-closed`, `post-merge`, `no-run-id`, etc.) are ignored and merge proceeds, weakening bash fail-closed boundaries.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-flush-split-invariant-output.txt: Either require a successful non-skipped `flush_logs_pre` before merge (return `MERGE_RESULT_ERROR` on any `skip.skipped`), or explicitly whitelist skip reasons that are safe to continue past (document each in `config.py`) and fail closed on the rest—including missing `state_file` when `merge` is true.


### FINDING_34: Manifest I/O path split between `ctx.tmpdir/manifest.json` and run-scoped log tree
- **Reviewer(s)**: dyn-flush-split-invariant-output.txt
- **Severity**: important
- **Concern**: `RunContext.manifest_path` is unused; top-level manifest vs `larch-logs/implement/<run_id>/manifest.json` mismatch can silently re-init and drop `steps_ran` only present in run-scoped manifests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-flush-split-invariant-output.txt: Single canonical manifest path under `larch-logs/implement/<run_id>/manifest.json` (derive from `ctx.run_id` + slug guard), align recovery to read that path first, and drop or wire `manifest_path` on `RunContext` to the same location.


### FINDING_36: `rebase_and_rebump` validates base remote/ref only after fetch/rebase
- **Reviewer(s)**: dyn-rebase-parity-inputs-output.txt
- **Severity**: important
- **Concern**: `git.validate_base_remote_ref` runs only inside `apply_bump` when `has_bump=True`, after fetch/rebase. Invalid labels are not rejected at the Python boundary before network/git work, unlike `rebase-push.sh` ordering.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-rebase-parity-inputs-output.txt: At the top of `rebase_and_rebump` (before the first `git.fetch`), call `git.validate_base_remote_ref(base_remote, base_ref)` and raise `Stalled` with a redacted message on failure, matching `rebase-push.sh` ordering.


### FINDING_37: `test_pr_body.py` missing `update_pr_body` and extra mermaid rejection coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `update_pr_body` success/fail-closed redaction paths and additional mermaid rejection cases are untested; unredacted PR bodies could ship.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_4: Existing-PR `Closes #N` body update gated on `ctx.pr_number`
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `ensure_pr` reuses an open PR but skips `pr_edit_body` when `ctx.pr_number` is unset even though `existing.number` is known. Bodies can lack `Closes #N`, so tracking issues may not auto-close on merge.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_40: `path_under_repo` helper untested
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: Traversal-guard regressions in `run_logs.path_under_repo` lack unit tests per plan.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

---


### FINDING_5: Fork mode pushes to `upstream` instead of `origin`
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt
- **Severity**: important
- **Concern**: Forked implement runs select `upstream` for branch push when that remote exists, while `create-pr.sh` / `git-push.sh` push `origin`. Pushes may target the parent repo or fail on typical fork clones, diverging from live ship-pr behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-security-output.txt: Address the concern above.


### FINDING_6: OOS non-security count uses JSON heuristics, not markdown `### OOS_*` blocks
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-bash-python-parity-output.txt
- **Severity**: important
- **Concern**: `_count_non_security` does not port `oos-non-security-block-count.awk`. Production accepted-OOS paths are markdown; JSON substring heuristics leave `non_sec=0`, so `disposition_ok` can pass while `oos-disposition-gate.sh` would exit 1 on undischarged blocks. `test_oos.py` JSON fixtures do not catch this.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From dyn-bash-python-parity-output.txt: Port the awk logic (block headers, per-block `focus-area` security routing, prose-vs-field discrimination) or shell out to the existing awk helper; add parity tests using the same markdown fixtures as `test-oos-disposition-gate.sh`.


### FINDING_7: `pr_checks_all_pass` lacks bash text fallback when JSON checks fail
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: When `gh pr checks --json` is missing or unparseable, Python returns not-ready without the text-output fallback `merge-pr.sh` uses via `refresh_ci_state`. Transient JSON failures can block merge as `ci_not_ready` while bash would proceed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.


### FINDING_8: No timing aggregation / `scrape_run` coverage per plan
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `tokens.py` lacks timing records and scrape coverage planned for Phase 7. Timing-report batches and Cursor sidecar aggregation may stay empty or untested when only token paths are wired.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_9: `test_pr.py` missing plan-mandated create/conflict and push-escalation scenarios
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Tests omit draft create-conflict recovery, `force_push_recovery` escalation, and existing-OPEN-PR push-failure paths. Regressions in create vs existing flows may ship until live runs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.


