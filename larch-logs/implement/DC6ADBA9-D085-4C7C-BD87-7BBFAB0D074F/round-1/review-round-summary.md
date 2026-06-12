# Review Round 1

- Mode: `diff`
- 26 accepted, 2 rejected (2 neutral)

## Accepted Findings

### FINDING_1: combine-issues no longer excludes `[LOCKED]` issues
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `combine-issues fetch` dropped the prior `[LOCKED]` title-prefix exclusion, so locked issues can be selected as combine candidates and closed during apply.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt: Address the concern above.


### FINDING_10: audit preflight omits stale local-main check
- **Reviewer(s)**: codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Audit preflight no longer blocks non-main branch audits when local `main` is behind `origin/main`, allowing stale run-log state to be audited.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_11: close-priors lacks BODY_FILE_FAILED fallback
- **Reviewer(s)**: codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `close-priors` can traceback on temp body-file setup failure instead of emitting the documented `BODY_FILE_FAILED=true` KV shape.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_12: combine apply dropped transient retry for source closes
- **Reviewer(s)**: codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `combine_issues apply` no longer retries transient `gh issue close` failures, so source issues can remain open after the combined issue is created.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_13: combine-issues fetch can write world-readable issue dumps
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `combine-issues fetch` writes issue JSON under `/tmp` with default permissions, which can expose issue bodies to local users.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_14: audit preflight can leak remote credentials
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, codex-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `preflight_main` prints raw `remote.origin.url` in failure diagnostics, so HTTPS remotes with embedded tokens can leak credentials into stdout, logs, or issue bodies.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt, codex-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_19: audit runbook contains broken or retired helper invocations
- **Reviewer(s)**: codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt, dyn-wire-contracts-output.txt
- **Severity**: important
- **Concern**: Audit skill command fences wrap Python CLI invocations in broken `bash "python3 ..."` forms or point at retired helper paths, so preflight, resolve, scan, counters, and close-priors examples can fail before producing their documented KVs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt, dyn-wire-contracts-output.txt: Address the concern above.


### FINDING_2: audit scan-run crashes on unexpected round directory names
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: `codex-round1-adherence` dereferences a missing regex match, so unexpected `round-*` directory names can crash `scan-run` with `AttributeError`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


### FINDING_20: post-tracking issue harness stubs the wrong executable path
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: The harness stubs `bash` around `python/cli.py` while callers use `python3`, and the version-read pipeline can hard-fail metadata posting instead of falling back to unknown.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_22: scan-required bail and step gating lack pytest coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `_scan_required` bail and step9a1 gating behavior was ported without targeted pytest coverage, so bailed or incomplete runs can be audited incorrectly without CI detection.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_23: version bump compare-ref behavior lacks tests
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `version_bump.py` lacks required `--head` compare-ref classification tests, so release prepare can choose the wrong bump from stale worktree state or wrong diff bases.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_24: verify-main behavior lacks direct pytest coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `verify_main.py` has no direct pytest coverage, and the finalize harness stubs bash verification, so admin-merge title suffix checks can break silently.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_25: release prepare metadata failure paths lack tests
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `release_prepare.py` lacks tests for commits-to-pulls notes, incomplete PR metadata, and origin-repo mismatch paths, allowing live release classification regressions.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_26: analyze-issues rich fixture coverage was dropped
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: The rich analyze issue fixture and shell assertions were removed without equivalent relocated pytest coverage, so category, duplicate, and reviewer regressions can pass CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_27: combine apply wire behavior is untested
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `combine_issues.apply_main` lacks tests for dry-run, create, and close wire behavior, so apply contract regressions can go undetected.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_3: audit scan-run can skip run-dir validation outside repo-root assumptions
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: The run-dir guard depends on cwd-relative `larch-logs/<skill>` existence, so cross-skill or skill-root paths may avoid the documented `run-dir-invalid` rejection.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_32: release prepare runs git commands in caller cwd
- **Reviewer(s)**: codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `release prepare` can inspect the wrong git repository when invoked from outside the plugin repo because git commands run in the caller cwd.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-testing-output.txt: Address the concern above.


### FINDING_33: resolve-prs mislabels gh list and view failures
- **Reviewer(s)**: dyn-wire-contracts-output.txt
- **Severity**: important
- **Concern**: `resolve_prs_main` treats `gh issue list` failures as no prior issue and `gh issue view` failures as malformed frontmatter, breaking documented `ERROR=` contract text for infra failures.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-wire-contracts-output.txt: Address the concern above.


### FINDING_34: promote release can emit raw stderr without ERROR prefix
- **Reviewer(s)**: dyn-wire-contracts-output.txt
- **Severity**: important
- **Concern**: `promote_release.py` can forward raw `gh` stderr without a guaranteed `ERROR=` prefix, breaking parsers that grep `^ERROR=`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-wire-contracts-output.txt: Address the concern above.


### FINDING_35: promote release can hide operator-facing errors after quiet_init
- **Reviewer(s)**: dyn-quiet-routing-output.txt
- **Severity**: important
- **Concern**: `promote_main` initializes quiet routing before validation and then prints failures to stderr, so diagnostics can go only to the quiet log instead of the operator-visible diagnostic stream.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-quiet-routing-output.txt: Address the concern above.


### FINDING_36: plugin read-version quiet-routing regression test is inadequate
- **Reviewer(s)**: dyn-quiet-routing-output.txt, dyn-cli-registry-output.txt
- **Severity**: important
- **Concern**: The `plugin read-version` test disables quiet routing or bypasses the CLI registry, so it does not cover inherited `LARCH_QUIET_ACTIVE` with command-substitution stdout capture.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-quiet-routing-output.txt, dyn-cli-registry-output.txt: Address the concern above.


### FINDING_4: close-priors misreports gh list transport failures as invalid JSON
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt, dyn-wire-contracts-output.txt
- **Severity**: important
- **Concern**: `close-priors` parses `gh issue list` output before checking return code, so auth or network failures are reported as invalid JSON instead of the documented transport failure reason.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt, dyn-wire-contracts-output.txt: Address the concern above.


### FINDING_5: analyze-issues fetch can write world-readable issue dumps
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Direct `analyze-issues fetch` no longer forces private file permissions, so raw issue JSON can be created world-readable on multi-user hosts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt: Address the concern above.


### FINDING_7: release runbook uses broken Python CLI shell quoting
- **Reviewer(s)**: codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Release skill snippets quote migrated Python CLI commands as one command word, so operators can hit command-not-found or non-executable `cli.py` failures.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_8: release finish can hide success KVs after in-process promotion
- **Reviewer(s)**: codex-specialist-correctness-output.txt, dyn-quiet-routing-output.txt, dyn-cli-registry-output.txt
- **Severity**: important
- **Concern**: `release_finish` calls `promote_main()` in-process, but promotion initializes quiet routing and redirects process stdout/stderr, so `RELEASE_ACTION`, `TARGET_OID`, `TAG`, and `VERSION` can land in the quiet log instead of caller-visible stdout.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt, dyn-quiet-routing-output.txt, dyn-cli-registry-output.txt: Address the concern above.


### FINDING_9: security focus-area regex misses `security-hardening`
- **Reviewer(s)**: codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `oos_disposition.py` uses POSIX character-class syntax inside a Python regex, so `security-hardening` can be counted as non-security and trigger false OOS silent-drop failures.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt: Address the concern above.


