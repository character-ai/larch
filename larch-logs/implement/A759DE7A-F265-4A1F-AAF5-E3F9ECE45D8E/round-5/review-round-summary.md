# Review Round 5

- Mode: `diff`
- 23 accepted, 7 rejected (7 exonerated)

## Accepted Findings

### FINDING_12: correctness: lifecycle marker regex omits colon
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: Lifecycle marker regex omits colon allowed by `tracking-issue-write.sh` `append_comment` with `lifecycle_marker`. `pr:opened` works in bash but raises invalid lifecycle marker in Python.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Expand `_MARKER_RE` to `[A-Za-z0-9._:-]` with leading char rule; keep `--` rejection; add colon marker test.


### FINDING_13: correctness: find_issue_comment_id_by_marker lacks BOM/CRLF normalization
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: `find_issue_comment_id_by_marker` lacks BOM and CR normalization on the first line. BOM or CRLF first line prevents marker match; `upsert_summary` posts duplicate comments instead of patching.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Port `normalize_first_line` from `tracking-issue-summary.sh` before comparing to marker.


### FINDING_14: architecture: REFRESH_SKIP_MERGE_OK defined but unused
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: `REFRESH_SKIP_MERGE_OK` is defined but never referenced. Merge cannot distinguish refresh skip reasons the constant was meant to encode.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Wire merge or Phase 7 driver to the skip set or remove until Phase 7.


### FINDING_16: risk-integration: missing UNKNOWN mergeStateStatus tests
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Missing tests for UNKNOWN/empty `mergeStateStatus` retry budgets and terminal error classification. Transient or persistent UNKNOWN probes could mis-route (premature merge, wrong literal, or unbounded retries) without failing pytest.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add RecordingRunner cases for N× UNKNOWN then success/error; assert retry counts and MERGE_RESULT_ERROR when exhausted; align with scripts/test-merge-pr.sh G3/G5/Q1 where feasible.


### FINDING_17: risk-integration: merge bash-parity K1/P1/N1/N2a Python-mocked only
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: K1/P1/N1/N2a are Python-mocked only; only BEHIND invokes `merge-pr.sh` despite plan requiring `test-merge-pr.sh` parity. Python flush-recovery can diverge from `merge-pr.sh` while CI stays green; Phase 7 routing could diverge on flush recovery while pytest still passes Python-only cases.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add subprocess stub-fixture cases (at least K1) comparing MERGE_RESULT= to bash; extend to P1/N1/N2a for negative paths.
  - From cursor-specialist-plan-fidelity-output.txt: Port test-merge-pr.sh fixture patterns: stub gh/git, run merge-pr.sh, assert MERGE_RESULT matches merge_pr for K1 and P1/N1/N2a.


### FINDING_18: risk-integration: no test that _flush_recoverable requires ancestor
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: No test that `_flush_recoverable` fails when `PR_HEAD_OID` is not an ancestor of HEAD. Invalid divergence could be treated as recoverable and trigger force-push/merge incorrectly.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add case: flush subjects and larch-logs-only paths with `is_ancestor` False → `_flush_recoverable` returns False.


### FINDING_20: risk-integration: missing step9a1 heuristic tests in flush_logs_pre
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: No positive tests for `steps_ran.step9a1` heuristic branches. Manifest may omit step9a1 signals for fork/design/OOS paths required at Phase 7.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Table-drive flush_logs_pre fixtures asserting step9a1 true/false/omitted per `_step9a1_heuristic` inputs.


### FINDING_21: risk-integration: tool-failure logging not ported
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Tool-failure logging from plan not implemented (only execution-issues). Phase 7 refresh may lose tool-failure batches present in bash `refresh-run-logs`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Port append-tool-failure behavior with tests or document deferral in python/README.md.


### FINDING_22: risk-integration: missing cursor token sidecar tests
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: Missing cursor token sidecar and `scrape_run(sidecar_paths=...)` coverage. Tool-specific sidecar shape regressions may go unnoticed until integration.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add cursor normalize_sidecar and scrape_run token path tests.


### FINDING_23: risk-integration: refresh skip reason tokens untested in flush_logs_pre
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: Refresh skip reasons `NO_LOGS_COMMIT`, `NO_RUN_ID`, `INVALID_RUN_ID` untested in `flush_logs_pre`. `_pre_push_probe` skip wiring can break without unit signal.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add state-file matrix tests asserting RefreshSkip.reason for each token.


### FINDING_24: risk-integration: non-Phase-5 changes bundled in branch
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Non-Phase-5 changes (upgrade-larch rebase, version_bump) bundled with Phase 5 Python port. `py-test` green while unrelated shell harnesses or upgrade behavior regresses in the same PR.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Run broader make lint / affected harness targets; consider splitting commits for reviewability.


### FINDING_25: risk-integration: unclosed-frontmatter missing from bash parity matrix
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: `unclosed-frontmatter` not in bash parity matrix. Python sanitizer could diverge from `sanitize-mermaid-fragment.sh` on frontmatter failures.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add parametrized bash vs Python case for MERMAID_REASON_UNCLOSED_FRONTMATTER.


### FINDING_27: security: compose_pr_body does not sanitize full assembled body
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: important
- **Concern**: `compose_pr_body` sanitizes only the mermaid parameter, not the assembled PR body. A tracking-issue plan goal (or summary) containing ```mermaid blocks with unsafe constructs is published on PR create because redact does not replace `sanitize_fragment`; `update_pr_body` would reject the same content.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Run sanitize_fragment on the full composed body (from_md=True) inside compose_pr_body before redact, matching update_pr_body.


### FINDING_28: security: compose_summary_bullets skips repo-root containment when cwd is None
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: important
- **Concern**: `compose_summary_bullets` skips repo-root containment when `cwd` is None. A misconfigured driver passes `cwd=None` and `plan_goals_file=../../../sensitive`; file content becomes PR summary bullets and can leak to GitHub after partial redaction.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Require cwd for reads or always resolve plan_goals_file under repo root with path_under_repo before read_text.


### FINDING_29: correctness: post-merge redaction failure returns RefreshSkip not merge error
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Post-merge redaction failures return `RefreshSkip` instead of failing merge. Redaction fails during `flush_logs_post`; `merge_pr` still returns merged/admin_merged and manifest stays partial with no post-merge batches.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Raise ShipError or map redaction-failed RefreshSkip to MergeResult error in _post_flush.


### FINDING_3: correctness: tracking_issue.rename return vs GitHub title
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: `rename()` returns an unredacted `new_title` but publishes a separately truncated/redacted title to `gh`. Callers assuming the return value equals the GitHub title can mis-report state after redaction/truncation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Return the exact title sent to `issue_edit` or expose both in a small result type.


### FINDING_30: correctness: destructive rmtree before copy in _publish_run_tree_to_repo
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Destructive `rmtree` before copy in `_publish_run_tree_to_repo`. Copy fails after `shutil.rmtree(dest)`; repo loses existing `larch-logs/implement/<run_id>` content.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Atomic copy-then-rename publish pattern.


### FINDING_31: architecture: manifest recovery picks newest mtime when run_id empty
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Manifest recovery picks newest mtime run dir when `run_id` empty. Wrong run_id bound if tmpdir has multiple implement run dirs; flush writes to alien manifest.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Fail closed without validated run_id instead of mtime fallback.


### FINDING_33: code-quality: empty {} refresh JSON files materialized
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: Empty `{}` refresh JSON files materialized when no ledger data. Empty `token-report-refresh.json`/`timing-report-refresh.json` copied into run batches.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Skip writing refresh copies when no source data exists.


### FINDING_4: correctness: _merge_noop_if_pr_closed guesses admin_merged without state
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: When `MERGE_RESULT` is missing from state and `no_admin_fallback` is false, `_merge_noop_if_pr_closed` defaults to `admin_merged`. Idempotent re-run after a plain squash merge (lost/empty state file) can classify as `admin_merged` instead of `merged`, skewing post-merge flush/finalize vs the Phase 7 `already_merged` contract and telemetry/routing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Use ground truth or a single documented noop until driver remaps MERGED PRs.
  - From cursor-specialist-correctness-output.txt: Default to merged when state unknown; use state file or gh evidence before admin_merged.
  - From cursor-specialist-edge-cases-output.txt: Default to merged when state unknown or require explicit MERGE_RESULT.


### FINDING_5: risk-integration: push retries skip backoff on identical stderr
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: Identical stderr on consecutive push failures skips backoff between retries (`continue`). Transient remote errors may exhaust three attempts back-to-back, unlike `git-push.sh` jittered spacing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Keep backoff between attempts; dedupe stderr only when emitting final failure.
  - From cursor-specialist-correctness-output.txt: Always apply backoff between attempts; dedupe stderr only in final diagnostics.


### FINDING_7: code-quality: git.remotes() unused dead API
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `git.remotes()` is unused; push always selects `origin`. Dead API surface from the plan; future fork-remote work may assume `remotes()` is wired.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Remove until needed or wire `select_push_remote` through it with tests.


### FINDING_9: code-quality: duplicate KEY=value file parsers in run_logs.py
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Four duplicate KEY=value file parsers; fixing KV parsing bugs requires four coordinated edits.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Replace with one `_read_kv_file` helper.


