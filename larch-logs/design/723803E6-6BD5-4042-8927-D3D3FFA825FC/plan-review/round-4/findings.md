### FINDING_1:
- **Reviewer(s)**: Codex-Arch, Codex-Innovation, Codex-dyn-admission-contract
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:1482-1506
- **Concern**: Plan adds ADMISSION_READY and ADMISSION_BLOCK_REASON semantics but does not update the Step 5c result-env/stdout parser allowlist to import those keys. Scenario: After design-publish writes ADMISSION_READY=true for a successful rename followed by PUBLISH_OK=false, Step 5d cannot see the admission state it is supposed to use and may keep treating the run as an unqualified publish failure or miss scrub/rename block reasons
- **Proposed resolution**: Add the new result keys to the initialized variables and both parse case allowlists in Step 5c: SCRUB_OK, ADMISSION_READY, ADMISSION_BLOCK_REASON, RENAME_FAILED, and RENAME_NOOP, then base Step 5d wording on those parsed values

### FINDING_2:
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:1494-1514
- **Concern**: Step 5c driver parse allowlist omits admission/scrub keys. Scenario: Plan Step 5d branches on ADMISSION_READY and ADMISSION_BLOCK_REASON but the fenced result-env/stdout case only binds PLAN_WRITE_OK|PUBLISH_OK|RENAMED|…; after exit 3 or file-first parse the orchestrator cannot apply scrub-failed vs rename-failed guidance or distinguish admission-ready from publish-failed
- **Proposed resolution**: Add SCRUB_OK ADMISSION_READY ADMISSION_BLOCK_REASON RENAME_FAILED RENAME_NOOP to both parse case arms in the Step 5c Bash block and align Step 5d footer prose with those variables

### FINDING_3:
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:1481-1506
- **Concern**: Step 5c parser plan omits new admission keys. Scenario: The plan makes Step 5d branch on ADMISSION_READY and ADMISSION_BLOCK_REASON, but the existing file/stdout parse allowlists only accept PLAN_WRITE_OK, PUBLISH_OK, RENAMED, and publish metadata; without adding the new keys, the orchestrator cannot distinguish implement-ready failed-publish from scrub-failed or rename-failed states.
- **Proposed resolution**: Add ADMISSION_READY, ADMISSION_BLOCK_REASON, SCRUB_OK, RENAME_FAILED, and RENAME_NOOP to the Step 5c variable initialization plus both result-env and stdout fallback parse allowlists.

### FINDING_4:
- **Reviewer(s)**: Codex-Edge
- **Severity**: latent
- **Focus area**: code-quality
- **Location**: scripts/test-design-structure.sh:1326-1329
- **Concern**: Proposed scrub-only source grep is brittle for multiline calls. Scenario: The plan asks for a design-log-publish.sh line matching --scrub-only, but current shell style puts the script path and flags on separate lines; a correct multiline scrub-only call can fail the structural test or force unnecessary formatting churn.
- **Proposed resolution**: Derive scrub and flush positions with awk over each command block, or locate the --scrub-only flag line and associate it with the nearest design-log-publish.sh invocation instead of requiring both tokens on one line.

### FINDING_5:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/design-publish.sh:17-27
- **Concern**: Full flush not gated on scrub preflight success. Scenario: When `--scrub-only` sets `SCRUB_OK=false`, the plan still runs the full `design-log-publish.sh` block for `SESSION_ID` non-empty. A second worktree flush fails at the same scrub gate and sets `PUBLISH_OK=false`, so `failed-publish` notes can show log-recovery/PR bullets while `ADMISSION_BLOCK_REASON=scrub-failed` and the summary scrub-retry bullet disagree (edge case line 131: footers must not imply `/implement` ready).
- **Proposed resolution**: Wrap the full publish call in `SCRUB_OK=true` (or equivalent) so scrub failure skips flush; set `SUMMARY_OUTCOME`/`PUBLISH_OK` from scrub-only outcome only.

### FINDING_6:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/design-log-publish.sh:94-660
- **Concern**: `--scrub-only` stdout contract underspecified vs flush tail. Scenario: Plan says emit `SCRUB_OK` and exit 0 without `gh`, but existing validation/staging paths emit `PUBLISH_OK=false` and the post-scrub path continues to porcelain/git/PR (`emit_publish_result` at 632-932). `design-publish.sh` can mis-parse scrub preflight as publish success/failure or run PR side effects in scrub-only mode.
- **Proposed resolution**: After argv sets scrub mode, branch all early failures to `emit_kv SCRUB_OK false` + exit 0; on scrub success emit `SCRUB_OK=true` (+ optional `SECRET_SCRUB_VIOLATIONS=`) and return before porcelain/commit/push/PR (worktree cleanup via existing trap).

### FINDING_7:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/test-design-publish.sh:57-58
- **Concern**: `SCRUB_OK=false` harness omits flush-absence pin. Scenario: Planned case asserts rename absent and `ADMISSION_BLOCK_REASON=scrub-failed` but not that full flush is skipped. An implementation that still calls flush twice passes rename ordering tests while violating minimum-change scrub-fail semantics.
- **Proposed resolution**: Add assert: exactly one `design-log-publish` line in `CALL_LOG`/`PUBLISH_LOG`, with `--scrub-only`; no second flush invocation.

### FINDING_8:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: architecture
- **Location**: skills/design/SKILL.md:1497-1506
- **Concern**: Step 5d adds ADMISSION_READY / ADMISSION_BLOCK_REASON / SCRUB_OK operator contract but the file-first result-env allowlist is unchanged. Scenario: After design-publish.sh writes the new keys, the orchestrator never binds them; Step 5d scrub/rename/implement guidance and any footer branching on ADMISSION_* stay dead on the normal parse path
- **Proposed resolution**: Extend both case arms (file + stdout merge) and initial declarations (~1481-1486) with SCRUB_OK ADMISSION_READY ADMISSION_BLOCK_REASON RENAME_FAILED RENAME_NOOP; mirror keys in skills/design/scripts/design-publish.md Result env allowlist

### FINDING_9:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/design-publish.sh:257-314
- **Concern**: Proposed flow runs full design-log-publish.sh after scrub-only even when SCRUB_OK=false blocks rename. Scenario: Scrub preflight can fail (or exit without SCRUB_OK=true) while a second full publish still succeeds: logs land on the branch but the issue title stays [DESIGNING]; SUMMARY_OUTCOME stays approved when PUBLISH_OK=true, conflicting with the edge-case rule that footers must not imply /implement readiness
- **Proposed resolution**: Gate the full flush on SCRUB_OK=true (skip or short-circuit after scrub-only failure); keep rename gated the same way

### FINDING_10:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/design-publish.sh:257-264
- **Concern**: Scrub-only is planned before the existing stale final-summary removal. Scenario: The preflight may stage an old final-summary.md that the real full publish still removes before flushing, so a stale summary with scrub trouble can block the [DESIGNED] rename even though the actual publish payload would not include it
- **Proposed resolution**: Move rm -f "$FINAL_SUMMARY_PATH" to run before both scrub-only and full publish, or explicitly add that move to the plan

### FINDING_11:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:18-19
- **Concern**: Plan adds a SCRUB_OK admission gate before the [DESIGNED] rename, so rename is no longer right after diagram upsert or independent of design-log-publish.. Scenario: If design-log-publish.sh --scrub-only fails or omits SCRUB_OK, the issue stays [DESIGNING] and /implement is blocked, contrary to the binding requirement that log flushing failures must not affect /implement admission.
- **Proposed resolution**: Restore the minimum change: move tracking-issue-write.sh rename --state designed immediately after the upsert block with only the existing SESSION_ID non-empty gate; keep secret scrub fail-closed behavior in the later full publish path.

### FINDING_12:
- **Reviewer(s)**: Codex-dyn-admission-contract
- **Severity**: important
- **Focus area**: security
- **Location**: SECURITY.md:197-203
- **Concern**: The plan changes the security-relevant admission boundary but omits SECURITY.md, despite the repo rule to update it for security behavior changes.. Scenario: SECURITY.md would still describe the scrubber as only a pre-flush gate and would not record that DESIGNED can precede log PR merge after a scrub-only preflight.
- **Proposed resolution**: Add a short note that Step 5c runs scrub-only before DESIGNED rename, log PR merge is not an admission prerequisite, full flush repeats scrub, and implement still verifies plan body and adequacy.

### FINDING_13:
- **Reviewer(s)**: Codex-dyn-admission-contract
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: scripts/design-log-publish.sh:691-720; scripts/test-design-log-publish.sh:21-249
- **Concern**: The proposed scrub-only test checks GH_STUB_LOG for push, but git push is not a gh command and would not appear there.. Scenario: A scrub-only implementation could accidentally reach git push before exiting; the test could still pass while creating a remote log branch before admission.
- **Proposed resolution**: In the scrub-only tests, also assert no remote larch-log-design-<RUN_ID> ref exists after the run, or add a lightweight git wrapper log that specifically fails on push.

### FINDING_14:
- **Reviewer(s)**: Cursor-dyn-scrub-boundary
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:1497-1506
- **Concern**: Step 5c orchestrator parse omits SCRUB_OK and ADMISSION_* keys from .design-publish-result.env. Scenario: The plan adds ADMISSION_READY / ADMISSION_BLOCK_REASON in design-publish.sh and Step 5d prose, but the Step 5c file-first parse case still only binds PLAN_WRITE_OK|PUBLISH_OK|RENAMED|... Step 5d cannot branch on ADMISSION_READY; operators still infer admission from PUBLISH_OK or RENAMED alone after scrub-failed or rename no-op runs.
- **Proposed resolution**: Extend the Step 5c parse case (and stdout fallback) with SCRUB_OK|ADMISSION_READY|ADMISSION_BLOCK_REASON|RENAME_FAILED|RENAME_NOOP; update Step 5c item 6 to drop the stale rename-gated-on-PUBLISH_OK sentence.

### FINDING_15:
- **Reviewer(s)**: Codex-dyn-scrub-boundary
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/design-log-publish.sh:691-720; scripts/test-design-log-publish.sh:21-28
- **Concern**: --scrub-only no-side-effect coverage watches the gh stub, but git push is a separate side effect. Scenario: An implementation that falls through far enough to run git push before exiting, but exits before gh pr create, would pass the planned GH_STUB_LOG checks while still publishing larch-log-design-<RUN_ID> before rename
- **Proposed resolution**: Add one assertion in the new scrub-only tests that the test origin has no larch-log-design-<RUN_ID> ref and no default-branch log path after scrub-only returns

### FINDING_16:
- **Reviewer(s)**: Codex-dyn-scrub-boundary
- **Severity**: important
- **Focus area**: security
- **Location**: skills/design/scripts/design-publish.sh:139-188; skills/design/scripts/design-publish.sh:257-347
- **Concern**: The plan says to emit the SECURITY add_warn before rename, but add_warn only records WARN lines for end-of-script emission. Scenario: A scrub-only redaction can be detected, then the issue can be renamed [DESIGNED] before any operator-visible rotate warning appears if full publish later hangs or fails
- **Proposed resolution**: Require an immediate scrub-only SECURITY diagnostic before tracking-issue-write.sh rename, while still storing exactly one WARN for the final result env and suppressing the full-publish duplicate

### FINDING_17:
- **Reviewer(s)**: Codex-dyn-scrub-boundary
- **Severity**: latent
- **Focus area**: correctness
- **Location**: skills/design/scripts/test-design-publish.sh:78-90; skills/design/scripts/test-design-publish.sh:352-396
- **Concern**: The planned tests cover SCRUB_OK=false but not scrub-only nonzero exit or exit 0 without SCRUB_OK=. Scenario: A malformed scrub-only result could be reported as publish failure or rename failure, or leave ADMISSION_BLOCK_REASON unset, while existing malformed-output tests only exercise the full publish path
- **Proposed resolution**: Add one minimal scrub-only malformed-output case that asserts no rename, ADMISSION_READY=false, ADMISSION_BLOCK_REASON=scrub-failed, and no publish/rename-failure guidance

### FINDING_18:
- **Reviewer(s)**: Cursor-dyn-operator-recovery
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:1497-1506
- **Concern**: Step 5c `.design-publish-result.env` parse omits admission keys. Scenario: Plan Step 5d tells the orchestrator to branch on `ADMISSION_READY` / `ADMISSION_BLOCK_REASON`, but the Step 5c parse `case` still binds only `PLAN_WRITE_OK|PUBLISH_OK|RENAMED|…`. Driver-emitted `ADMISSION_READY` / `SCRUB_OK` / `RENAME_NOOP` never reach Step 5d, so footer and replay prose can still treat `PUBLISH_OK=false` like log-only recovery or infer admission from `RENAMED` alone.
- **Proposed resolution**: Extend both parse branches (file + stdout fallback) to bind `SCRUB_OK`, `ADMISSION_READY`, `ADMISSION_BLOCK_REASON`, `RENAME_FAILED`, and `RENAME_NOOP`; initialize them before parse like other driver keys.

### FINDING_19:
- **Reviewer(s)**: Cursor-dyn-operator-recovery
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:1546-1552
- **Concern**: Step 5d machine footer still keyed only on `PUBLISH_OK`. Scenario: After publish failure the footer is always `log publish incomplete; NEXT REQUIRED: continue` whenever `SESSION_ID` is set and `PUBLISH_OK=false`. That reads as “proceed” even when `ADMISSION_BLOCK_REASON=scrub-failed` or `rename-failed` (`ADMISSION_READY=false`), contradicting Step 5d scrub/rename recovery prose and risking `/implement` after a blocked admission path.
- **Proposed resolution**: Split footer templates on `ADMISSION_READY` / `ADMISSION_BLOCK_REASON` (e.g. admission-ready + log incomplete vs scrub retry vs rename fix); do not use the generic continue footer when admission is blocked.

### FINDING_20:
- **Reviewer(s)**: Codex-dyn-operator-recovery
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:1481-1506
- **Concern**: Step 5d is planned to branch on ADMISSION_READY and ADMISSION_BLOCK_REASON, but the existing Step 5c result parser allowlist only imports PLAN_WRITE_OK/PUBLISH_OK/RENAMED and related publish keys, and the plan does not explicitly add the new admission keys to that parser.. Scenario: After a failed full publish with a successful no-op rename, design-publish can persist ADMISSION_READY=true and RENAMED=false, but SKILL.md would leave ADMISSION_READY unset and Step 5d could still treat RENAMED=false as not ready or omit the implement-may-proceed guidance.
- **Proposed resolution**: Extend the Step 5c initialization and both file/stdout parser allowlists to include SCRUB_OK, ADMISSION_READY, ADMISSION_BLOCK_REASON, RENAME_FAILED, and RENAME_NOOP before updating the Step 5d footer/recovery branches; add a publish harness assertion that Step 5d consumes ADMISSION_READY=true with RENAMED=false.

### FINDING_21:
- **Reviewer(s)**: Codex-dyn-operator-recovery
- **Severity**: important
- **Focus area**: security
- **Location**: skills/design/scripts/render-final-summary.sh:300-315; skills/design/SKILL.md:1529-1554; scripts/scrub-log-secrets.sh:41-45
- **Concern**: Planned scrub-failed recovery says to fix exposure even though scrub-log-secrets exits non-zero only when it cannot guarantee a clean tree; redacted exposures are the SCRUB_OK=true/SECRET_SCRUB_VIOLATIONS path.. Scenario: If the scrub helper is missing or a detected token survives scrubbing, ADMISSION_BLOCK_REASON=scrub-failed would send the operator toward exposure cleanup or rotation instead of the scrub gate diagnostic, while the title correctly remains [DESIGNING].
- **Proposed resolution**: Change scrub-failed guidance in the render note and Step 5d prose to inspect design-log-publish.failure.log/execution-issues, fix the scrub or redaction gate failure, then retry Step 5c; rotate only when the SECURITY/SECRET_SCRUB_VIOLATIONS warning appears; do not manually rename.
