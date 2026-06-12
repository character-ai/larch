# stall-recovery-report.sh

`stall-recovery-report.sh` is the deterministic `/implement` stall recovery helper. It classifies terminal stalls, records script-to-main-agent escalation handoffs, normalizes final outcomes, and composes exactly one public report only on terminal failure or escalation-success teardown.

## Canonical `/implement` artifacts

The `/implement` runtime uses pinned files under `$IMPLEMENT_TMPDIR`:

- canonical ledger: `stall-recovery-escalation-ledger.tsv`
- ledger fallback: `stall-recovery-escalation-fallback.tsv`
- ledger write failure marker: `stall-recovery-escalation-record-failure.env`
- terminal sentinel: `stall-recovery-terminal-report.env`
- escalation-success sentinel: `stall-recovery-escalation-success.env`
- classification state: `stall-recovery-classification.env`
- prompt-state sensitive supplement: `stall-recovery-sensitive-corpus.env`
- issue input artifact: `stall-recovery-issue-input.md`
- chat-print artifact: `stall-recovery-chat-print.md`
- operator-action record: `stall-recovery-operator-action-record.md`
- operator-action sentinel: `stall-recovery-operator-action.env`
- root-cause finding: `stall-recovery-root-cause.md`
- bounded root-cause finding: `stall-recovery-bounded-root-cause.md`
- root-caused title: `stall-recovery-title.txt`

These names are internal constants so `/design` can later parameterize the same engine without forking it. Public generic profile flags such as `--profile generic`, `--artifact-prefix`, state-file overrides, vocabulary overrides, and generic ledger overrides are deferred to #3992.

## Subcommands

- `init-attempts --implement-tmpdir <path> --attempts-file <path>` initializes retry history.
- `classify --implement-tmpdir <path> ...` emits the sanitized classification KV contract and writes `stall-recovery-classification.env`. The file includes `FAILURE_CLASS`, `FAILURE_SIGNATURE`, `RESUME_HINT`, `STALL_STEP`, `PHASE`, `STALL_TRACKING`, `BAIL_REASON`, `EXIT_CODE`, `MATCHED_CLASSIFIER_PATTERN`, and `DISPATCHER`.
- `record-attempt ...` appends retry attempt history.
- `retry-policy --class <class>` emits the retry-cap table projection. Retry caps are part of the public recovery policy.
- `record-escalation --implement-tmpdir <path> --site <token> --trigger <token> --step <token> --phase <token> [--dispatcher <token>] [--exit-code <n>] [--failure-detail-log <path>]` appends one canonical ledger row. The canonical ledger path is always `stall-recovery-escalation-ledger.tsv`. Invalid, outside-tmpdir, symlinked, non-regular, or malformed paths fail closed. Append failures write fallback evidence or the record-failure marker and add a tagged `record-escalation` Tool Failure when possible.
- `normalize-outcome --implement-tmpdir <path>` is the shared final-outcome API used by `write-final-report.sh` and Step 18a.5. It emits `IMPLEMENT_NORMALIZED_OUTCOME=<token>`, `IMPLEMENT_OUTCOME_SUCCEEDED=true|false`, stall-tracking layer diagnostics, and the state fields used in the decision.
- `compose-report --report-kind terminal-failure|escalation-success --surface issue-input|chat-print ...` is the single public report-rendering API. It writes Tier A issue input or Tier B chat-print output and emits normalized report env fields.
- `normalize-issue-env ...` persists canonical issue number and URL after `/larch:issue --input-file` returns.
- `chat-print ...` is a convenience wrapper for `compose-report --surface chat-print`.
- `is-larch-dev-clone`, `clear-stall`, `seed-terminal-state`, and `lint` keep their existing operational roles.

`bug-body`, `bug-comment`, and `issue-input-file` are no longer public report surfaces. Compatibility is gated behind `LARCH_STALL_RECOVERY_TEST_LEGACY_SURFACES=1` for older harness fixtures only.

## Outcome normalization

`normalize-outcome` preserves the final-summary precedence:

1. Any observed `STALL_TRACKING=true` in `ship-pr-state.sh`, `finalize-state.sh`, or `session-env.sh` maps to `stalled`.
2. `FORKED_TARGET=true` maps to `forked-dry-run`.
3. `DESIGN_ONLY_DONE=true` maps to `design-only`.
4. `MERGE_RESULT=merged` or `admin_merged` maps to `merged`.
5. `MERGE_RESULT=already_merged` maps to `force-merged-externally`.
6. A non-zero draft PR maps to `pr-created-draft`.
7. A non-zero non-draft PR with `MERGE=false` maps to `pr-created`.
8. Otherwise the outcome is `bailed`, except `BAIL_NEEDS_USER_INPUT=true` remaps only that fallthrough to `bailed-needs-user-input`.

Step 18a.5 treats only `merged`, `force-merged-externally`, `pr-created`, `pr-created-draft`, and `forked-dry-run` as success. Unknown, partial, failed, invented, or missing outcomes do not succeed. Every observed `STALL_TRACKING` layer must be false.

## Escalation-success evidence

Step 18a.5 counts only these evidence sources:

- non-empty canonical ledger
- non-empty fallback ledger
- non-empty record-failure marker
- uniquely tagged `record-escalation` Tool Failure entries

Generic Tool Failures do not trigger escalation-success reporting. Terminal failure absorbs ledger, fallback, and marker evidence into the terminal report. A run publishes at most one report.

## Root-cause artifacts

Main Claude must investigate before composing. The root-cause file schema is:

```text
verdict=larch-defect|environment|operator-action
confidence=low|medium|high
summary=<single-line safe summary>

<finding prose with durable evidence citations>
```

`operator-action` writes the local non-filing record and sentinel, then skips public filing or printing. This also applies after successful merge so cleanup has a durable non-filing record.

## Tier behavior

Tier A is a larch dev clone with `FORKED_TARGET=false`. Tier A uses `issue-input`, bypasses TSV field allowlists, and redacts secrets from the complete public heading and body. It may include run linkage, branch, PR URL, validated logs, run-log pointer, full attempts, escalation ledger, root-cause finding, and verbatim bail reason after secret redaction.

Tier B covers consumer repos and forked runs. Tier B writes `chat-print` only. It renders allowlisted machine fields plus validated bounded root-cause prose. `compose-report` requires `stall-recovery-sensitive-corpus.env` for Tier B and rejects bounded prose, titles, and chat-print output that contain excluded client-bearing values or raw evidence text. Allowlisted larch operational enums and machine fields are exempt, including step tokens, phase tokens, site tokens, trigger tokens, bail tokens, dispatcher names, `lint-fix-loop`, `ship-pr`, and `main-agent-required`.

Tier B sensitive-token sources include plan text, feature description, execution issues, validated failure-detail logs, raw attempt values, canonical ledger, fallback evidence, record-failure marker text, run-log pointer text, `finalize-state.sh`, `ship-pr-state.sh`, `session-env.sh`, prompt-state supplement values, repo names, branch names, PR URLs, issue text, plan text, and client paths.

## Titles

Terminal reports use:

```text
[Bug] /implement terminal: <safe-root-cause-summary> (<class> at <step>)
```

Escalation-success reports use:

```text
[Bug] /implement escalation: <safe-root-cause-summary> (<site>:<trigger>)
```

Explicit title text comes from `stall-recovery-title.txt`. If it is unsafe, composition falls back to the validated root-cause summary. If neither is safe, composition fails closed and requires a rewrite. The full heading and body are redacted after composition.

## Surface Allowlists

Lint parity covers Tier B only. The committed TSV, helper code, and this table must remain byte-equivalent at the `surface + field_key + source + transform` level.

<!-- stall-recovery-allowlist:begin -->
| surface | field_key | source | transform |
|---|---|---|---|
| chat-print | report_kind | REPORT_KIND | enum |
| chat-print | failing_step | STALL_STEP | enum |
| chat-print | failing_phase | PHASE | enum |
| chat-print | failure_class | FAILURE_CLASS | enum |
| chat-print | bail_reason | BAIL_REASON | expanded-bail-token-union |
| chat-print | exit_code | EXIT_CODE | integer-or-unknown |
| chat-print | dispatcher | DISPATCHER | enum |
| chat-print | matched_classifier_pattern | MATCHED_CLASSIFIER_PATTERN | enum |
| chat-print | larch_version | larch-version | token |
| chat-print | run_id | RUN_ID | token-or-unknown |
| chat-print | attempt_table | attempts-file | allowlisted-attempt-fields |
| chat-print | escalation_site | escalation-ledger | enum |
| chat-print | escalation_trigger | escalation-ledger | enum |
| chat-print | fallback_escalation_marker | escalation-fallback | present-marker |
| chat-print | record_failure_marker | record-failure-marker | present-marker |
| chat-print | record_escalation_tool_failure | execution-issues | present-marker |
| chat-print | bounded_root_cause | bounded-root-cause-file | validated-larch-internal-prose |
<!-- stall-recovery-allowlist:end -->

## Retry Caps

| failure_class | attempts | delay |
|---|---:|---|
| transient-infra | 4 | `sleep-seconds.sh 5` |
| test-failure | 8 | none |
| lint-failure | 8 | none |
| dispatch-failure | 3 | none |
| protected-path | 1 | none |
| ci-fix-exhausted | 8 | none |
| same-cause-repeat | 2 | none |
| contract-failure | 0 | none |
| unrecoverable | 0 | none |

For `same-cause-repeat`, the orchestrator uses the alternate strategy immediately. For `transient-infra`, the emitted retry delay means `sleep-seconds.sh 5` between attempts. `protected-path` means Codex hit a permanent protected-path sandbox policy; Main Claude resumes Step 2 inline; for `protected-path-edit-required-out-of-scope`, the operator warning names `.claude-plugin/plugin.json`.

## Dry run

`LARCH_STALL_RECOVERY_DRY_RUN=1` makes report composition write local artifacts and emit `DRY_RUN_DECISION=true`. Callers must skip `/larch:issue` when dry-run is true.
