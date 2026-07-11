## Final Design Plan

The plan is very large. Showing the full plan body below.

## Plan

## Goal

Prevent tests, fixtures, development probes, and reporter simulations from mutating GitHub issues on the scoped issue-filing and terminal-reporting surfaces without explicit live-run authorization.

This plan covers the binding filing choke points and their direct pre-filing mutation-capable paths:

- `python3 python/cli.py issue create-one`, including fallback create and orphan rollback close;
- `scripts/file-failure-report-cross-repo.sh`, including lookup, create, duplicate comment, and reconciliation-related paths;
- Tier-A dedup before terminal reporter filing, including `gh repo view` and the helper’s `--dedup-only` invocation;
- `/design` salvage reconciliation comment, close, and verification operations;
- OOS blocker probes, label provisioning/edits, issue filing, and failed-create cleanup;
- dev-only `audit-runs close-priors`;
- `/implement` deferred-work filing and the `/design` `/larch:issue` callers that reach `issue create-one`.

Keep dry-run and local report composition available without authorization, and make every scoped dry-run boundary fully offline with zero `gh` invocations.

This is not a claim to gate every GitHub issue mutation module in the repository. Existing independent live surfaces not named above, including tracking-issue lifecycle helpers, decomposition `close-original`, and clarification mutations, remain outside this change unless their execution reaches a scoped guarded boundary.

## Approach

1. Define one authorization contract for scoped GitHub issue operations.
   - Use config-owned wire literals for:
     - the strict live-mutation boolean key;
     - explicit invocation modes for session-backed live runs and operator-requested commands;
     - the test-only deny control;
     - the designated refusal status, reason, and distinct non-zero exit code.
   - Require explicit evidence from the invoking live driver or operator command. Do not infer authorization from the current directory, repository shape, run ID alone, TTY state, GitHub credentials, or an ambient authorization variable.
   - Validate session-backed evidence from an explicitly supplied guarded context file, including trusted session-root membership, regular-file and non-symlink requirements, strict boolean parsing, and matching run identity.
   - Make test denial override otherwise valid inherited live-session state.
   - Make refusal distinct from GitHub, redaction, validation, and network failures.

2. Persist and validate live-run authorization through guarded session writers.
   - Add the strict live-mutation authorization key to both `/implement` `session-env.sh` and `/design` `source-env.sh` allowlists and generated values.
   - Thread the key from the real `/design` Step 0 driver and `/implement` bootstrap/resume driver only.
   - Preserve a valid prior value during legitimate refresh and resume paths; reject malformed values rather than rewriting them from arbitrary caller environment.
   - Keep the key out of untrusted caller-env import paths.
   - Add a reusable authorization reader/checker for Python boundaries and a shell-compatible validation route for the reporter helper. Callers must provide the context path or explicit operator invocation mode.

3. Gate `issue create-one` before all live GitHub and temporary-file work.
   - Extend argument parsing with explicit, mutually validated authorization inputs:
     - a guarded session context file for `/design` or `/implement`;
     - an explicit config-owned operator-invoked mode for direct `/issue` and audit flows.
   - Parse and redact the title, then take an unconditional `--dry-run` return before repository resolution, label validation, body reads needed only for live filing, temporary body creation, or any `gh` subprocess.
   - Preserve the existing dry-run preview envelope using offline input values only; do not call `gh repo view`, `gh label list`, or any other `gh` command.
   - For non-dry-run calls, fail closed before repository lookup, label lookup, temporary body creation, JSON create, legacy fallback create, ID lookup, or orphan rollback close.
   - Emit stable refusal KVs and the designated distinct exit code.
   - Treat JSON fallback create and rollback close as operations covered by the original authorized invocation only; neither can bypass the initial check.

4. Gate the cross-repository stall-report helper before every GitHub operation.
   - Add an explicit mutation-context argument and validate it before dedup lookup, repository-related work, duplicate comment, create, or any reconciliation-related helper call.
   - Keep argument and local-file validation available for `--dry-run`, but return dry-run before any `gh` operation.
   - On missing, invalid, malformed, mismatched, or test-denied context, emit the designated refusal status and fallback reason with zero `gh` calls.
   - Preserve current dry-run, dedup, validation, Tier B safety, and post-authorization fallback contracts.
   - Make the refusal status an allowed helper status in the report normalizer, normalize it to `fallback-print-required`, preserve the designated refusal reason, and prevent terminal filing from continuing or retrying through another mutation route.

5. Gate Tier-A dedup before its pre-helper GitHub resolution.
   - Name and gate `dedup_tier_a_report` itself, rather than relying only on the later create helper gate.
   - Add a required mutation-context argument to its CLI/main parser and validate it at the entry point after the existing offline dry-run decision but before:
     - `gh repo view`;
     - repository resolution;
     - construction or execution of the cross-repository helper;
     - the helper’s `--dedup-only` lookup;
     - any duplicate-comment path.
   - Thread `$DESIGN_TMPDIR/source-env.sh` through `/design` Tier-A dedup invocations and `$IMPLEMENT_TMPDIR/session-env.sh` through `/implement` Tier-A dedup invocations.
   - On refusal, emit the designated refusal status and reason in the dedup env output, allow the normalizer to produce `fallback-print-required`, and make the terminal reporter write only its local fallback artifact.
   - Do not treat refusal as `no-match`, `lookup-failed-open`, a dedup result, or permission to continue into the create helper.

6. Add reporter-level authorization checks before pre-helper GitHub resolution.
   - In `/design` terminal reporting, validate the explicit `source-env.sh` context before Tier-A dedup, repository resolution, helper invocation, or Tier A/Tier B mutation-capable paths.
   - In `/implement` stall recovery, validate the explicit `session-env.sh` context before Tier-A dedup, repository resolution, helper invocation, or Tier A/Tier B mutation-capable paths.
   - On refusal, write the existing local fallback artifact with the designated reason, do not invoke dedup or the filing helper, and do not issue `gh repo view` or retry through another public mutation route.
   - Pass the context explicitly to `dedup_tier_a_report` and `file-failure-report-cross-repo.sh` only after the reporter-level check succeeds.

7. Gate `/design` salvage reconciliation direct GitHub paths.
   - Add the same fail-closed session-backed authorization check at the start of `_reconcile_post_recovery_comment` and `_reconcile_failed_publish_tail_report`, before comment, close, view, or any other `gh` call.
   - Use `$DESIGN_TMPDIR/source-env.sh` as the explicit context and preserve the existing bounded reconcile-failed/local audit behavior on refusal.
   - Leave the report open on refusal; do not send the reconciliation comment, close the issue, or verify state through `gh`.
   - Ensure reconciliation refusal is represented as a bounded local reason consistent with Tier-A refusal handling.

8. Thread `/design` session authorization through all legitimate scoped issue-filing skill paths.
   - Extend `/larch:issue` guidance to distinguish:
     - session-backed live `/design` or `/implement` filing, which passes its guarded context file;
     - direct operator-requested filing, which passes the explicit operator invocation literal;
     - dry-run filing, which remains authorization-free and offline.
   - Update `/design` Step 0b tracking issue invocation, Step 5b OOS invocation, manual OOS recovery invocation, and decomposition partition batch invocation to pass `$DESIGN_TMPDIR/source-env.sh` where they invoke the scoped `issue create-one` boundary.
   - Ensure nested `issue create-one` command construction receives and forwards the session context rather than silently falling back to an operator or ambient environment path.
   - Preserve existing `/larch:issue` argument semantics, dedup behavior, and blocked-by sequencing.

9. Gate OOS direct GitHub paths, not only its `create-one` subprocess.
   - Require and validate the active `/implement` mutation context before OOS blocker probes, priority-label lookup/provisioning/edits, direct GitHub cleanup, and the `create-one` filing subprocess.
   - Propagate the context through the OOS filing flow and append it to every nested `issue create-one` call.
   - On authorization refusal, perform no GitHub operation, preserve the existing hard-create/audit/sentinel cleanup behavior, and record a clear tool failure rather than treating the refusal as a dedup or retryable network result.

10. Gate dev-only audit mutations, including `close-priors`.
    - Extend `audit-runs close-priors` with the explicit operator-invoked authorization input and validate it before its first GitHub list, comment, or close operation.
    - Preserve refusal as a distinct status/reason and do not attempt a comment or close after refusal.
    - Update `.claude/skills/audit-runs/SKILL.md` command examples for both direct `create-one` and `close-priors` paths to pass the exact config-owned operator authorization literal.

11. Update all remaining legitimate scoped `/implement` callers.
    - Pass the active `/implement` context to `issue create-one` for accepted OOS filing and deferred-work scope disposition.
    - Treat refusal as a hard create failure through each caller’s existing audit, cleanup, or `ShipError` path.
    - Inventory the guarded CLI/helper boundaries and direct GitHub issue mutation paths within the scoped OOS and reporter flows so no caller silently degrades to an unauthorized create attempt.

12. Make the Python test environment deny scoped real issue mutations by default.
    - Install an autouse, default-deny test control in `python/conftest.py`.
    - Scrub and restore authorization-related ambient variables so a parent `/design` or `/implement` session cannot authorize tests accidentally.
    - Ensure the boundary-level context validator observes test denial even in subprocess execution.
    - Require successful filing tests to use injected runners, monkeypatches, or stubbed `gh` processes and to opt into only the narrow simulated mutation under test.
    - Do not allow fixture-authored state alone to suppress test denial.

13. Document the scoped outbound mutation boundary and refusal contract.
    - Update the reporter helper contract with required context arguments, Tier-A dedup context propagation, dry-run’s zero-`gh` rule, operator route where applicable, refusal KVs, and normalizer behavior.
    - Update `SECURITY.md` with the scoped live-mutation boundary, test default-deny behavior, refusal semantics, coverage of comments/closes/labels as well as creates within scope, and the residual limitation: this prevents accidental execution, not a malicious process that can alter code, session state, and credentials.
    - State that unrelated existing GitHub mutation surfaces are not newly covered by this change.

## Files to modify/create

### UPDATED: python/larch/core/config.py

Define the authorization key, session and operator invocation literals, test-deny key, refusal status, refusal reason, and distinct refusal exit code once. Keep Python, shell, skills, reporters, and tests from duplicating wire strings.

### UPDATED: python/larch/state/session_env.py

Add the strict live-mutation authorization key to `/design` and `/implement` writer allowlists and generated values. Add or expose the trusted guarded-context validation needed by Python callers. Preserve valid prior state during refresh, reject malformed values, enforce trusted roots and regular non-symlink files, validate matching run identity, and exclude the key from untrusted caller-env import paths.

### UPDATED: python/larch/design/design_step0.py

Thread live-driver authorization into the guarded `/design` source-env writer during real Step 0 setup and supported resume/refresh paths.

### UPDATED: python/larch/state/bootstrap.py

Thread live-driver authorization into the guarded `/implement` session-env writer during real bootstrap and resume setup.

### UPDATED: python/larch/issue/issue_create.py

Extend `create-one` argument parsing with session-context and operator-invoked authorization inputs. Return dry-run output immediately after parsing/redaction and before repo resolution, label lookup, body-file work, temporary files, or `gh`. Add the shared fail-closed non-dry-run check before GitHub access and ensure fallback create, ID lookup, and rollback close cannot bypass it.

### UPDATED: scripts/file-failure-report-cross-repo.sh

Require and validate the explicit mutation context before any GitHub lookup or mutation. Add a stable refusal status/reason, keep `--dry-run` zero-`gh`, and preserve Tier A/Tier B, dedup, create, duplicate-comment, and fallback behavior after authorization succeeds.

### UPDATED: scripts/file-failure-report-cross-repo.md

Document the required live-run context, Tier-A dedup context propagation, the zero-`gh` dry-run contract, refusal KVs, reporter normalization/fallback behavior, and any explicit operator route supported by the helper.

### UPDATED: python/larch/state/_normalize.py

Allow the helper and Tier-A dedup designated refusal status, map it to `fallback-print-required`, preserve the refusal reason in normalized output, and prevent unknown/refusal outcomes from being treated as filed, deduped, or eligible for continued terminal publication.

### UPDATED: python/larch/state/_report.py

Extend `dedup_tier_a_report` with an explicit mutation-context input. Preserve its offline dry-run path, then fail closed before its `gh repo view`, helper construction, helper `--dedup-only` call, or duplicate-comment path. Emit the designated refusal status/reason for the normalizer and terminal reporter.

### UPDATED: python/larch/state/stall_recovery.py

Expose and parse the Tier-A dedup mutation-context argument in `dedup_tier_a_report_main`, forwarding it unchanged to `_report.dedup_tier_a_report` without creating an ambient or operator-mode fallback.

### UPDATED: python/larch/design/design_terminal.py

Add reporter-level authorization before Tier-A dedup, repository resolution, or helper invocation. Pass `$DESIGN_TMPDIR/source-env.sh` to Tier-A dedup and Tier A/Tier B helper calls. Gate `_reconcile_post_recovery_comment` and `_reconcile_failed_publish_tail_report` before all direct `gh` comment, close, and view operations; on refusal preserve bounded local fallback/reconcile-failed behavior and leave report issues open.


Add `/implement` reporter-level authorization before Tier-A dedup, repository resolution, or helper invocation. Pass `$IMPLEMENT_TMPDIR/session-env.sh` to Tier-A dedup and Tier A/Tier B helper calls. Preserve refusal as the designated local fallback reason rather than a generic helper failure, retry, or fail-open dedup result.

### UPDATED: python/larch/issue/oos_filer.py

Require the active `/implement` mutation context before direct blocker probes, priority-label lookup/provisioning/edits, issue filing, and cleanup. Thread the context into `issue create-one`, surface refusal as a hard create failure with existing audit/sentinel behavior, and make unauthorized OOS execution perform zero GitHub calls.

### UPDATED: python/larch/implement/scope_disposition.py

Pass the active `/implement` mutation context when creating a deferred-work follow-up issue. Surface refusal through the existing `ShipError` path.

### UPDATED: python/larch/issue/audit_runs.py

Extend `close-priors` with explicit operator authorization, fail closed before the first GitHub list/comment/close operation, and emit a distinct refusal result without mutations.

### UPDATED: skills/issue/SKILL.md

Document and emit the exact authorization argument for direct operator-requested `issue create-one` commands. Add a session-backed branch that accepts a `/design` or `/implement` context file and forwards it through nested create-one invocations. Keep dry-run commands authorization-free and explicitly zero-`gh`.

### UPDATED: skills/design/SKILL.md

Pass `$DESIGN_TMPDIR/source-env.sh` to the Step 0b `/larch:issue` tracking-issue invocation where it reaches `issue create-one`, and document that scoped live `/design` issue filing uses the guarded session-backed route rather than operator mode.

### UPDATED: skills/design/references/finalize-step5.md

Pass `$DESIGN_TMPDIR/source-env.sh` to Step 5b and manual-recovery `/larch:issue` OOS filing commands, including nested create-one forwarding where the skill constructs arguments.

### UPDATED: skills/design/references/decompose-panel.md

Pass `$DESIGN_TMPDIR/source-env.sh` to decomposition partition `/larch:issue` batch filing where it reaches `issue create-one`, and preserve current idempotency, annotate, blocked-by, and partial-filing behavior.

### UPDATED: .claude/skills/audit-runs/SKILL.md

Add the exact explicit operator authorization to direct `issue create-one` and `audit-runs close-priors` commands. Document distinct refusal handling and dry-run behavior where applicable.

### UPDATED: python/conftest.py

Install an autouse default-deny control for scoped real GitHub issue operations. Scrub and restore related authorization variables so inherited live sessions cannot authorize tests accidentally, including subprocess-oriented test setup.

### UPDATED: python/tests/core/test_config.py

Pin config-owned authorization literals, invocation modes, refusal status/reason, test-deny key, and distinct refusal exit code.

### UPDATED: python/tests/state/test_session_env.py

Cover both session writers, strict boolean validation, trusted-root/non-symlink/regular-file validation, run-identity matching, refresh preservation, malformed-state rejection, and omission from untrusted caller-env import paths.

### UPDATED: python/tests/issue/test_issue_create.py

Add focused tests proving:

- non-dry-run `create-one` refuses without authorization;
- refusal emits the designated KVs and distinct exit code;
- no repository, label, create, lookup, fallback, or rollback `gh` command runs;
- dry-run returns before repository resolution, label validation, body-file work, temporary-file creation, and any `gh` call;
- valid operator and session-backed contexts reach only injected or stubbed `gh`;
- malformed, missing, symlinked, out-of-root, mismatched-run, ambient-only, and test-denied contexts fail closed;
- inherited live-session state does not override test denial.

Update existing success tests to opt into the narrow simulated mutation while retaining stubbed runners.

### UPDATED: python/tests/design/test_design_lifecycle.py

Cover:

- authorized live reporter filing with explicit `source-env.sh`;
- Tier-A dedup context propagation into `dedup_tier_a_report` and its helper;
- reporter-level unauthorized refusal before Tier-A dedup, repository resolution, helper invocation, or `gh`;
- an unauthorized dedup-branch fixture that proves neither `gh repo view` nor the helper’s `--dedup-only` lookup runs;
- fallback status/reason propagation through normalizer and terminal output;
- realistic terminal-failure fixture data that invokes neither the cross-repository helper nor `gh` without authorization;
- salvage reconciliation without monkeypatching `_reconcile_post_recovery_comment`, proving unauthorized comment, close, and view paths make zero `gh` calls and leave the report open;
- valid session-backed reconciliation through injected/stubbed GitHub operations.

### UPDATED: python/tests/state/test_stall_recovery.py

Cover `/implement` Tier A and Tier B reporter authorization before Tier-A dedup, pre-helper repository resolution, or helper invocation; explicit session-context propagation into dedup and filing; refusal normalization to local fallback; an unauthorized Tier-A dedup path with zero `gh` calls; and inherited live-session plus test-deny precedence.

### UPDATED: python/tests/issue/test_oos_filer.py

Cover unauthorized OOS blocker probes, label operations, create-one filing, and cleanup with zero GitHub calls; cover valid context propagation only through injected/stubbed GitHub paths; pin refusal handling as hard-create/audit behavior rather than dedup or retry.

### UPDATED: python/tests/issue/test_audit_runs.py

Cover unauthorized `close-priors` subprocess execution with zero `gh` calls, distinct refusal output, and authorized operator-mode behavior through stubbed GitHub commands.

### UPDATED: python/tests/implement/test_scope_disposition.py

Cover forwarding the active `/implement` context to `issue create-one` and refusal propagation through the existing `ShipError` path.

### UPDATED: scripts/test-file-failure-report-cross-repo.sh

Add missing, invalid, malformed, ambient-only, and test-denied context cases that assert zero `gh` calls. Pin dry-run as authorization-free and zero-`gh`. Update successful create, dedup-only lookup, and duplicate-comment fixtures to pass valid explicit authorization, and cover refusal normalization inputs where the harness exercises helper output.

### UPDATED: SECURITY.md

Document the scoped live mutation authorization boundary, coverage of scoped create/comment/close/label paths, test default-deny behavior, session versus operator routes, zero-`gh` dry-run behavior, refusal semantics, and the residual threat-model limitation. State that unrelated existing GitHub mutation surfaces are outside this change.

## Edge cases

- A valid `LARCH_RUN_ID` without the authorization key must refuse.
- An authorization key inherited through ambient environment without the explicit context argument or explicit operator route must refuse.
- A context file outside the expected session root, a symlink, a non-regular file, a malformed boolean, or a mismatched run identity must refuse.
- Test denial must override a valid parent session context and fixture-authored state.
- `issue create-one --dry-run` must return before repo resolution, label lookup, body-file work, temporary-file creation, and every `gh` invocation.
- Reporter and Tier-A dedup dry-runs must remain authorization-free and make no `gh` calls.
- Tier-A dedup must validate context before `gh repo view`, helper execution, `--dedup-only` lookup, or duplicate comment.
- Reporter-level refusal must occur before Tier-A dedup, `gh repo view`, helper execution, or reconciliation setup that performs GitHub work.
- Dedup matches must not post comments without authorization.
- Salvage reconciliation must not comment, close, or view a prior report without authorization.
- OOS blocker checks, label creation/edits, cleanup, and filing must not call GitHub without authorization.
- `audit-runs close-priors` must not list, comment on, or close issues without explicit operator authorization.
- Create success followed by ID lookup failure may run rollback close only because the original invocation was already authorized.
- Resume and environment refresh must retain authorization only through the trusted writer path.
- `/design` tracking, OOS, and decomposition calls that reach `issue create-one` must pass the session context rather than be mistaken for operator requests.
- Operator-invoked authorization must be explicit in direct skill commands, not inferred from TTY state or credentials.

## Failure modes

- If a legitimate caller omits authorization, fail before scoped GitHub access and emit the designated refusal fields.
- If session evidence cannot be read or validated, treat it as unauthorized.
- If Tier-A dedup refuses, normalize it to a local fallback and do not resolve the repository, invoke the helper, or continue to create filing.
- If a reporter refuses before helper execution, write the local fallback artifact with the designated reason and do not retry through another mutation route.
- If the helper returns the refusal status, normalize it to `fallback-print-required` while preserving the refusal reason.
- If salvage reconciliation authorization fails, preserve bounded reconcile-failed audit behavior and leave the report open.
- If OOS authorization fails, preserve hard-create/audit cleanup behavior without direct GitHub fallback.
- If the test isolation fixture is absent from a subprocess, the boundary-level authorization check must still refuse absent explicit valid authorization.
- Do not convert refusal into a fail-open dedup result, generic helper failure, or generic create retry.
- Do not let fixture-authored state alone suppress the test default-deny guard.

## Testing strategy

Run only focused changed-file tests and harnesses:

- `python3 -m pytest python/tests/core/test_config.py`
- `python3 -m pytest python/tests/state/test_session_env.py`
- `python3 -m pytest python/tests/issue/test_issue_create.py`
- `python3 -m pytest python/tests/design/test_design_lifecycle.py`
- `python3 -m pytest python/tests/state/test_stall_recovery.py`
- `python3 -m pytest python/tests/issue/test_oos_filer.py`
- `python3 -m pytest python/tests/issue/test_audit_runs.py`
- `python3 -m pytest python/tests/implement/test_scope_disposition.py`
- `bash scripts/test-file-failure-report-cross-repo.sh`

Also run changed-file lint and type checks through the documented focused Python lint path. Verify the shell helper with the Bash 3.2 and shell lint targets applicable to that file.

The key regression assertions are process-level:

- invoke each scoped filing or direct mutation boundary without authorization while a real-looking repository and inherited live session are present, then prove the stub log contains no `gh` invocation;
- invoke Tier-A dedup without authorization, then prove the stub log contains neither `gh repo view` nor a helper `--dedup-only` invocation;
- invoke `issue create-one --dry-run` with realistic repo and labels, then prove the stub log contains no `gh` invocation;
- invoke `/design` salvage reconciliation, OOS filing, and `audit-runs close-priors` without authorization, then prove the stub log contains no GitHub list, view, comment, close, label, create, or API invocation.

difficulty: HARD
diff_added: 790
diff_deleted: 110
mechanical_churn: false
oversize_override: operator
diff_lines: 900
