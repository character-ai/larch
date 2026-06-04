### FINDING_1: Step 5c does not parse new admission/scrub result keys
- **Reviewer(s)**: Codex-Arch, Codex-Innovation, Codex-dyn-admission-contract, Cursor-Edge, Codex-Edge, Cursor-Pragmatic, Cursor-dyn-scrub-boundary, Cursor-dyn-operator-recovery, Codex-dyn-operator-recovery
- **Severity**: important
- **Concern**: The plan adds `SCRUB_OK`, `ADMISSION_READY`, `ADMISSION_BLOCK_REASON`, `RENAME_FAILED`, and `RENAME_NOOP` semantics, but Step 5c’s result-env/stdout parser still only allowlists the old publish/rename keys. Step 5d would not reliably see the admission state it is supposed to branch on, causing scrub failures, rename failures, no-op renames, or admission-ready publish failures to be reported incorrectly.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch, Codex-Innovation, Codex-dyn-admission-contract: Add the new result keys to the initialized variables and both parse case allowlists in Step 5c: SCRUB_OK, ADMISSION_READY, ADMISSION_BLOCK_REASON, RENAME_FAILED, and RENAME_NOOP, then base Step 5d wording on those parsed values
  - From Cursor-Edge: Add SCRUB_OK ADMISSION_READY ADMISSION_BLOCK_REASON RENAME_FAILED RENAME_NOOP to both parse case arms in the Step 5c Bash block and align Step 5d footer prose with those variables
  - From Codex-Edge: Add ADMISSION_READY, ADMISSION_BLOCK_REASON, SCRUB_OK, RENAME_FAILED, and RENAME_NOOP to the Step 5c variable initialization plus both result-env and stdout fallback parse allowlists.
  - From Cursor-Pragmatic: Extend both case arms (file + stdout merge) and initial declarations (~1481-1486) with SCRUB_OK ADMISSION_READY ADMISSION_BLOCK_REASON RENAME_FAILED RENAME_NOOP; mirror keys in skills/design/scripts/design-publish.md Result env allowlist
  - From Cursor-dyn-scrub-boundary: Extend the Step 5c parse case (and stdout fallback) with SCRUB_OK|ADMISSION_READY|ADMISSION_BLOCK_REASON|RENAME_FAILED|RENAME_NOOP; update Step 5c item 6 to drop the stale rename-gated-on-PUBLISH_OK sentence.
  - From Cursor-dyn-operator-recovery: Extend both parse branches (file + stdout fallback) to bind `SCRUB_OK`, `ADMISSION_READY`, `ADMISSION_BLOCK_REASON`, `RENAME_FAILED`, and `RENAME_NOOP`; initialize them before parse like other driver keys.
  - From Codex-dyn-operator-recovery: Extend the Step 5c initialization and both file/stdout parser allowlists to include SCRUB_OK, ADMISSION_READY, ADMISSION_BLOCK_REASON, RENAME_FAILED, and RENAME_NOOP before updating the Step 5d footer/recovery branches; add a publish harness assertion that Step 5d consumes ADMISSION_READY=true with RENAMED=false.


### FINDING_3: Full publish can still run after scrub preflight failure
- **Reviewer(s)**: Cursor-Innovation, Cursor-Pragmatic
- **Severity**: important
- **Concern**: The planned flow runs the full `design-log-publish.sh` flush after `--scrub-only` even when `SCRUB_OK=false` or missing. That can produce contradictory state: admission blocked by scrub failure while publish/log-recovery output suggests a normal failed-publish or even successful publish path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Wrap the full publish call in `SCRUB_OK=true` (or equivalent) so scrub failure skips flush; set `SUMMARY_OUTCOME`/`PUBLISH_OK` from scrub-only outcome only.
  - From Cursor-Pragmatic: Gate the full flush on SCRUB_OK=true (skip or short-circuit after scrub-only failure); keep rename gated the same way


### FINDING_5: `SCRUB_OK=false` harness does not assert full flush was skipped
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: The planned test asserts no rename and `ADMISSION_BLOCK_REASON=scrub-failed`, but does not prove the full publish call was skipped. An implementation could call `design-log-publish.sh` twice and still pass the planned rename/admission assertions.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Add assert: exactly one `design-log-publish` line in `CALL_LOG`/`PUBLISH_LOG`, with `--scrub-only`; no second flush invocation.


### FINDING_6: Stale final-summary removal occurs after scrub-only preflight
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Concern**: Scrub-only is planned before the existing stale `final-summary.md` removal. The preflight could inspect a stale summary that the real full publish would remove, blocking rename based on content that would not actually be published.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: Move rm -f "$FINAL_SUMMARY_PATH" to run before both scrub-only and full publish, or explicitly add that move to the plan


### FINDING_7: Scrub admission gate conflicts with requirement that log flushing not block implement admission
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Concern**: The plan gates `[DESIGNED]` rename on `SCRUB_OK`, making admission depend on `design-log-publish.sh --scrub-only`. This conflicts with the stated requirement that log flushing failures must not affect `/implement` admission.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Restore the minimum change: move tracking-issue-write.sh rename --state designed immediately after the upsert block with only the existing SESSION_ID non-empty gate; keep secret scrub fail-closed behavior in the later full publish path.


### FINDING_8: SECURITY.md not updated for changed admission boundary
- **Reviewer(s)**: Codex-dyn-admission-contract
- **Severity**: important
- **Concern**: The plan changes security-relevant admission behavior but omits the repository-required `SECURITY.md` update. The security docs would not describe the relationship between scrub-only preflight, `[DESIGNED]` admission, log PR merge, and implement verification.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-admission-contract: Add a short note that Step 5c runs scrub-only before DESIGNED rename, log PR merge is not an admission prerequisite, full flush repeats scrub, and implement still verifies plan body and adequacy.


### FINDING_9: Scrub-only no-side-effect test misses git push side effects
- **Reviewer(s)**: Codex-dyn-admission-contract, Codex-dyn-scrub-boundary
- **Severity**: important
- **Concern**: The planned scrub-only test checks `GH_STUB_LOG`, but `git push` is not a `gh` command. A scrub-only implementation could create a remote log branch before exiting while still passing the `gh`-only no-side-effect assertions.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-admission-contract: In the scrub-only tests, also assert no remote larch-log-design-<RUN_ID> ref exists after the run, or add a lightweight git wrapper log that specifically fails on push.
  - From Codex-dyn-scrub-boundary: Add one assertion in the new scrub-only tests that the test origin has no larch-log-design-<RUN_ID> ref and no default-branch log path after scrub-only returns


### FINDING_10: Security warning may not be operator-visible before rename
- **Reviewer(s)**: Codex-dyn-scrub-boundary
- **Severity**: important
- **Concern**: The plan says to call `add_warn` before rename, but `add_warn` only stores warnings for end-of-script emission. If full publish later hangs or fails, the issue could be renamed `[DESIGNED]` before the operator sees the scrub/redaction security diagnostic.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-scrub-boundary: Require an immediate scrub-only SECURITY diagnostic before tracking-issue-write.sh rename, while still storing exactly one WARN for the final result env and suppressing the full-publish duplicate


### FINDING_12: Step 5d footer still treats all publish failures as generic continuation
- **Reviewer(s)**: Cursor-dyn-operator-recovery
- **Severity**: important
- **Concern**: Step 5d’s machine footer remains keyed only on `PUBLISH_OK`. When admission is blocked by scrub or rename failure, the footer can still say `log publish incomplete; NEXT REQUIRED: continue`, contradicting the scrub/rename recovery path and risking `/implement` after blocked admission.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-operator-recovery: Split footer templates on `ADMISSION_READY` / `ADMISSION_BLOCK_REASON` (e.g. admission-ready + log incomplete vs scrub retry vs rename fix); do not use the generic continue footer when admission is blocked.


### FINDING_13: Scrub-failed recovery guidance misdirects operators toward exposure cleanup/rotation
- **Reviewer(s)**: Codex-dyn-operator-recovery
- **Severity**: important
- **Concern**: Planned scrub-failed guidance says to fix exposure, but `scrub-log-secrets.sh` exits nonzero when it cannot guarantee a clean tree; redacted exposures are represented by `SCRUB_OK=true` plus `SECRET_SCRUB_VIOLATIONS`. Operators may be sent toward rotation or exposure cleanup when the actual issue is the scrub/redaction gate itself.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-operator-recovery: Change scrub-failed guidance in the render note and Step 5d prose to inspect design-log-publish.failure.log/execution-issues, fix the scrub or redaction gate failure, then retry Step 5c; rotate only when the SECURITY/SECRET_SCRUB_VIOLATIONS warning appears; do not manually rename.

