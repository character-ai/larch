# Review Round 3

- Mode: `diff`
- 9 accepted, 1 rejected (1 neutral)

## Accepted Findings

### FINDING_1: Lint classifier drops relevant-checks failure evidence
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: During Step 5 stall classification, a failure-detail log that contains only `relevant-checks failed` is classified as `unrecoverable/none` instead of `lint-failure/step5-review` because the port lost the bash `relevant-checks.*fail` (and related lint-failed) evidence regex before the transient-infra fallback.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Restore relevant-checks.*fail (and lint.*failed) regex before transient fallback; add pytest


### FINDING_10: Global flags before subcommand no longer supported
- **Reviewer(s)**: codex-generic-output.txt
- **Severity**: important
- **Concern**: The retired helper and `python/stall-recovery-report.md` allow global flags before the subcommand, but `main()` treats `argv[0]` as the subcommand unconditionally. Documented calls like `python3 python/cli.py stall-recovery --profile generic --artifact-prefix design-failure compose-report ...` fail as an unknown subcommand.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-generic-output.txt: Pre-parse supported global flags before selecting the subcommand, or otherwise preserve the retired helper's global-flag ordering contract.


### FINDING_11: validate_token bail routing inconsistent with validate_terminal_state
- **Reviewer(s)**: dyn-parity-output.txt
- **Severity**: important
- **Concern**: `validate_token()` routes `--token-kind bail` through `_safe_token("bail", …)`, which only accepts `_GENERIC_BAILS` when `generic=True` and rejects non-empty implement bails when `generic=False`. Bash `cmd_validate_token` used `safe_bail_reason_value()`, and `validate_terminal_state()` still uses `_safe_bail_reason_value()` for `BAIL_REASON`. Tokens such as `ci-local-unfixable:lint_1,test-2` or `dirty-tree` can pass terminal-state validation but fail `validate-token`, so `design-stage-terminal-state.sh` can reject a bail at line 61 that would pass `validate-terminal-state` at line 124.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-parity-output.txt: In `validate_token()`, branch `kind == "bail"` to `_safe_bail_reason_value(token, generic=generic)` (and mirror bash `reject_rawish_value()`), instead of `_safe_token("bail", …)`.


### FINDING_12: Generic classify routing requires --primary-state-file
- **Reviewer(s)**: dyn-parity-output.txt
- **Severity**: important
- **Concern**: Generic classify routing requires both `profile == "generic"` and a non-empty `--primary-state-file`. Retired bash always entered `cmd_classify_generic_from_terminal_state` for generic profile and defaulted missing state to the prefixed terminal-state env file. Python falls through to the implement `ship-pr-state.sh` merge path when `--profile generic` is set without `--primary-state-file`, producing implement-style signatures, `DISPATCHER` from `CODER_TOOL` instead of `SOURCE_SCRIPT`, and no terminal-state validation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-parity-output.txt: Route all `profile == "generic"` classify calls to `_classify_generic_from_terminal_state()`, and inside that helper default the state file the same way `validate_terminal_state()` does (`primary_state_file` or prefixed `design-failure-terminal-state.env`).


### FINDING_16: record_escalation uses non-atomic in-place ledger rewrite
- **Reviewer(s)**: dyn-cutover-output.txt
- **Severity**: important
- **Concern**: `record_escalation()` appends to the canonical ledger with in-place `read_text()` + `write_text()`, while sibling writers use temp-file + atomic replace. A crash or partial `OSError` during ledger rewrite can truncate `*-escalation-ledger.tsv`, yet the function can still return `0` on the fallback-degraded path while callers such as `plan_review.py` and `review-design-step3-loop.sh` treat `rc==0` as success and write idempotency sentinels.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-cutover-output.txt: Rewrite canonical-ledger append through the same tmp+`replace()` pattern used by `record_attempt()` and `_rewrite_state_keys()`, and only emit `ESCALATION_RECORDED=true` after read-back verification of the appended row.

---

**Merge notes (for voters):**
- Input FINDING_4 + FINDING_8 → **FINDING_4** (same wrapper, distinct test gaps, one latent risk).
- Input FINDING_6 + FINDING_20 → **FINDING_6** (same OOS collateral).
- Input FINDING_18 and FINDING_19 omitted (positive attestation only; no actionable concern).


### FINDING_2: Broad protected-path substring beats transient classification
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: Evidence containing a network timeout plus unrelated `protected-path` text can match the broad protected-path heuristic and yield `protected-path/step2-impl` instead of `transient-infra/step8-shippr`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Require exact protected-path-edit-required-out-of-scope token for evidence-based protected-path match


### FINDING_7: normalize_issue_env lacks bash stdout filter and strict validation pipeline
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `/issue` stdout with exit 0 but missing `ISSUES_FAILED=0`, truthy `ISSUE_1_FAILED`, or non-digit `ISSUE_1_NUMBER` can still emit `NORMALIZED=true` and write `stall-recovery-issue.env`, so Step 18a may treat a partial or spoofed filing as success. The deleted bash allowlist filter and dedup-precedence checks were not fully ported.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Port the bash allowlist filter, type ISSUES_FAILED=0 / ISSUE_1_FAILED truthy / digit-only ISSUE_NUMBER checks, and dedup precedence into normalize_issue_env; restore retired harness cases as pytest


### FINDING_8: --artifact-prefix no longer validated before path construction
- **Reviewer(s)**: codex-generic-output.txt
- **Severity**: important
- **Concern**: Unlike the retired shell helper, `--artifact-prefix` is not validated before `_artifact_path()` builds output paths. A prefix such as `../leak` can make `classify` write `../leak-classification.env` outside `$IMPLEMENT_TMPDIR`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-generic-output.txt: Restore the old simple dash-token validation for `--artifact-prefix` before any path construction, and reject slashes, dots, underscores, empty-leading-dash, and other non `[A-Za-z0-9-]` characters.


### FINDING_9: chat-print subcommand is a non-functional stub
- **Reviewer(s)**: codex-generic-output.txt
- **Severity**: important
- **Concern**: Documented `chat-print` should wrap `compose-report --surface chat-print`, but the Python port only prints `--input-file` when present and otherwise exits 0. Callers get no report artifact, no filing status, and no failure signal.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-generic-output.txt: Parse the same arguments as `compose-report` for `chat-print`, force `surface="chat-print"`, and call `compose_report()`.


