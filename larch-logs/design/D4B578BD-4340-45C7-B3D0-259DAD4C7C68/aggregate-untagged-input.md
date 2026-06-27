### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:100-101
- **Concern**: Bootstrap recovery mandatory-read stub text uses `completely.,` but structure pins expect `completely.`. Scenario: The plan’s table-row stubs at lines 100-101 spell `Read … completely., then execute`, while the proposed `require_near` literals at lines 184-186 pin `… completely.` without the extra period. An implementer copying the stub verbatim leaves pins that never match and `make test-implement-structure` fails even when relocation is otherwise correct.
- **Proposed resolution**: Fix stub prose to `… completely.` (single period) before `, then execute`, matching the `bootstrap_recovery_read` pin exactly.

### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-implement-fence-shape.sh:130-131
- **Concern**: [Prior accepted FINDING_4 still incomplete] `EXPECTED_NEW` subsection lists only fence 3 of 4 departing self-review fences. Scenario: The `### UPDATED: scripts/test-implement-fence-shape.sh` block states the `-4` rule in prose but the numbered list names only `checks-commit-route --checks-site step5-self-review`. Failure modes repeat all four; an implementer following only the fence-shape subsection can change `EXPECTED_NEW` by 1 instead of 4 and get `found new=27`.
- **Proposed resolution**: Enumerate all four departing fences in the subsection (telemetry-mark, write-pre-self-review-snapshot, checks-commit-route step5-self-review, write-self-review-tally), each on its own numbered line, before the re-run note.

### FINDING_3:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/references/self-review.md:32-38
- **Concern**: Telemetry-fold goal contradicts “preserve all four fences” and relocation needles. Scenario: The issue requires folding the standalone telemetry-mark into the first self-review verb for ~1 turn savings. The plan simultaneously says fold telemetry (line 32), lists a standalone `timing telemetry-mark` fence as mandatory (lines 34-38 item 1), and requires that launcher string in the relocation-authority loop (line 257). Implementers can satisfy harness pins while skipping the fold, missing the stated savings and leaving ambiguous authority.
- **Proposed resolution**: Pick one contract: if folded, describe in-prose best-effort marking only, drop item 1 from the four-fence list, remove the telemetry launcher from relocation needles, and note whether `EXPECTED_NEW` still drops by four; if not folded, delete the fold instruction and issue-savings claim.

### FINDING_4:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: scripts/test-implement-structure.sh:231-275
- **Concern**: Relocation-authority loop pseudo-Python omits valid `for needle in [` syntax. Scenario: The bootstrap-recovery and self-review mandatory loop blocks (lines 231-252 and 256-275) show `Path(...).read_text()` followed by bare string literals and `if needle not in …` without a `for needle in [` wrapper. Copied literally into the embedded harness, this is invalid Python and breaks `make test-implement-structure` at parse time.
- **Proposed resolution**: Mirror the existing `cleanup_ref` loop shape exactly: `for needle in [ … ]:` before each `if needle not in …` block, including the self-review negative checks against `skill_text`.

### FINDING_5:
- **Reviewer(s)**: Codex-Arch
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: plan.txt:64-79; 229-252
- **Concern**: bootstrap-recovery verification loop omits the actual dirty-recovery state transitions. Scenario: The new reference can pass the current needles while dropping `DEGRADED_PROMPT_REQUIRED=true`, `STAGE=step0-plan-materialize`, or the `RECOVERY_REQUIRED=false` clean-reset, so the one-down path and the recheck/reset contract are not enforced
- **Proposed resolution**: Add `require_text` needles for `DEGRADED_PROMPT_REQUIRED=true`, `STAGE=step0-plan-materialize`, the dirty-tree checkpoint recheck, and `RECOVERY_REQUIRED=false`

### FINDING_6:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:30-52; 254-275
- **Concern**: self-review relocation loop only pins launcher artifacts, not the moved review body. Scenario: The reference can keep the composite fence and anti-halt opener while omitting the plan read, diff capture, changed-file read, OOS policy load, review rubric, and rejected-finding rules, leaving Step 5 self-review incomplete but still green under the harness
- **Proposed resolution**: Add `require_text` needles for the preserved review steps, not just the fences and artifact paths

### FINDING_7:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-implement-structure.sh:229-275
- **Concern**: Relocation-authority loop pseudo-code omits valid Python `for needle in [` structure (incomplete follow-up to accepted round-4 relocation verification). Scenario: Plan lines 231-252 and 256-275 show needles and `if needle not in ...` bodies without the `for needle in [` / `]:` wrappers that `cleanup_ref` uses at lines 632-646; the self-review block also merges a second `skill_text` scan without `skill_text = Path(skill).read_text()` or its own loop. An implementer copying the plan snippet writes invalid harness Python and `make test-implement-structure` fails before the relocation can be verified.
- **Proposed resolution**: Mirror `cleanup_ref` exactly: `text = Path(...).read_text()` then `for needle in [ ... ]:` / `if needle not in text: checks.append(...)`, and add a separate `skill_text = Path(skill).read_text()` loop for the relocated-authority forbid needles.

### FINDING_9:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-implement-fence-shape.sh:130-132
- **Concern**: Fence-shape UPDATED subsection still lists only one of four departing self-review fences (prior accepted FINDING_4 remains incomplete). Scenario: The subsection says `EXPECTED_NEW` drops by four but enumerates only item 3 (`checks-commit-route --checks-site step5-self-review`); items 1-2 and 4 (`timing telemetry-mark`, `write-pre-self-review-snapshot`, `write-self-review-tally`) are absent though Failure modes line 324 names all four. An implementer following only the fence-shape subsection can lower `EXPECTED_NEW` by one and `make test-implement-fence-shape` fails (`found new=27`).
- **Proposed resolution**: Expand the numbered list under `EXPECTED_NEW` to all four departing launcher fences, matching Failure modes and the forbid/relocation needles.

### FINDING_10:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: plan.txt:71-77
- **Concern**: Dirty-tree resume contract drops stale-state reset. Scenario: The current recovery path clears `IMPLEMENT_BAIL_REASON` and reparses `BRANCH_NAME`, `BRANCH_ACTION`, and `PLAN_FILE` from the resumed `step-0-bootstrap.sh --mode resume` stdout before re-evaluating `BOOTSTRAP_NEXT`. The new bootstrap-recovery bullets only require rechecking `BOOTSTRAP_NEXT`, so the split can resume with a stale bail reason or pre-recovery branch/plan state and route incorrectly after cleanup.
- **Proposed resolution**: Add the stale-state reset and resumed-tail rebinding explicitly to `bootstrap-recovery.md`, and pin `IMPLEMENT_BAIL_REASON`, `BRANCH_NAME`, `BRANCH_ACTION`, and `PLAN_FILE` in the new relocation-authority loop.

### FINDING_11:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:107-113
- **Concern**: Self-review composite branch loses the edit-and-retry path. Scenario: The self-review split preserves the composite launcher and the fail-closed sentence, but it never says to keep the `NEXT_ACTION=main-agent-edit` re-entry branch or the exact line-anchored `NEXT_ACTION` parse. The composite can legitimately ask for a fix-up; without that branch the moved reference can treat a recoverable edit request as a terminal failure and jump to Step 18 instead of rerunning the composite.
- **Proposed resolution**: Carry over the `NEXT_ACTION=main-agent-edit` branch and the one-record `NEXT_ACTION` parse into `self-review.md`, and add a matching structure-harness pin for that path.

### FINDING_12:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: scripts/test-implement-structure.sh:229-275
- **Concern**: Relocation-authority loop pseudo-code is invalid Python (missing `for needle in [` wrappers). Scenario: The plan block at lines 231-252 and 256-275 shows orphan string literals and `if needle not in ...` bodies without a `for needle in [...]:` header, unlike the working `cleanup_ref` template at lines 632-646. An implementer can paste this literally and break the embedded harness with a syntax error, or ship loops that never run.
- **Proposed resolution**: Rewrite both mandatory relocation blocks as complete `for needle in [...]:` loops matching the `cleanup_ref` shape; put the inverse `skill_text` residual-authority checks in a separate second loop.

### FINDING_13:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-implement-fence-shape.sh:130-131
- **Concern**: [ALREADY_ADDRESSED] `EXPECTED_NEW` drop list still names only fence 3 of 4. Scenario: The subsection still lists only item 3 (`checks-commit-route --checks-site step5-self-review`) after the "lower by exactly four" rule. Prior accepted FINDING_4 remains incomplete. An implementer following only the fence-shape subsection can decrement `EXPECTED_NEW` by 1 and fail `make test-implement-fence-shape` (`found new=27`).
- **Proposed resolution**: Enumerate all four departing self-review fences: `timing telemetry-mark`, `write-pre-self-review-snapshot`, `checks-commit-route --checks-site step5-self-review`, and `write-self-review-tally`.

### FINDING_15:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:96-101,197-210
- **Concern**: Rebase Checkpoint Macro still uses a path-only bootstrap-recovery anchor. Scenario: The SKILL edit and the structure-harness pin can both be satisfied by a bare `bootstrap-recovery.md` mention. That leaves the absorbed `1.r` degraded carve-out unverifiable and lets the mandatory-read contract regress to a filename-only stub.
- **Proposed resolution**: Use the full `**MANDATORY — READ ENTIRE FILE**: Read \`${CLAUDE_PLUGIN_ROOT}/skills/implement/references/bootstrap-recovery.md\` completely.` literal in both the SKILL update and the harness needle.

### FINDING_16:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: plan.txt:254-263
- **Concern**: Self-review relocation authority does not pin the telemetry-mark best-effort guard. Scenario: The moved `python/cli.py timing telemetry-mark` fence can lose its `|| true` best-effort wrapper and become fatal on a transient telemetry failure. That would abort Step 5 before review on a non-critical helper blip.
- **Proposed resolution**: Pin the exact telemetry line with `|| true` in `self-review.md` and add the same exact string to the relocation-authority loop.

### FINDING_18:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-implement-fence-shape.sh:130-132
- **Concern**: Fence-shape subsection still enumerates only one of four departing self-review fences. Scenario: Prior accepted FINDING_4 flagged this; the plan still lists only item 3 (`checks-commit-route`) under the four-fence `EXPECTED_NEW` drop rule while failure modes repeat the -4 rule. An implementer following only the fence-shape subsection can lower `EXPECTED_NEW` by 1 instead of 4 and fail `make test-implement-fence-shape` (`found new=27`) despite correct relocation.
- **Proposed resolution**: Complete the numbered list with all four departing fences: `timing telemetry-mark`, `write-pre-self-review-snapshot`, `checks-commit-route --checks-site step5-self-review`, and `write-self-review-tally`.

### FINDING_19:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/references/self-review.md:575
- **Concern**: [ALREADY_ADDRESSED] Self-review relocation needles omit `NEXT_ACTION=main-agent-edit` re-entry. Scenario: The plan mandates relocation-authority verification (lines 254-270) but its needle list omits the composite re-entry contract (`On NEXT_ACTION=main-agent-edit ... re-run this same composite launcher with identical argv`) currently at `SKILL.md:575`. An implementer can relocate the body yet drop that branch; the harness passes while self-review stalls or misroutes after composite `main-agent-edit`.
- **Proposed resolution**: Add `main-agent-edit` and the re-run composite launcher sentence to the mandatory `self_review_text` relocation needles.

### FINDING_20:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: architecture
- **Location**: plan.txt:96-121
- **Concern**: Mandatory-read literal shapes differ across bootstrap-recovery touchpoints. Scenario: The plan uses at least three incompatible literals: Rebase Macro edit (line 96) uses `...bootstrap-recovery.md` for degraded-prompt handling; table stubs (100-101) use `Read ... completely.`; `rebase_ref` needles (199-204) redefine `bootstrap_recovery_read` without `Read`/`completely.`; `rebase-checkpoint-routing.md` update (119-121) matches the macro form. Harness `require_near` pins (184-187) expect the stub form only. Partial edits can pass some pins while runtime macros and references disagree.
- **Proposed resolution**: Normalize one canonical mandatory-read literal per surface (stub, SKILL macro line 158, `rebase-checkpoint-routing.md`, and `rebase_ref` needles) and align every harness pin to that exact string.

### FINDING_21:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: code-quality
- **Location**: scripts/test-implement-structure.sh:229-275
- **Concern**: Relocation-authority loop pseudo-code omits `for needle in [` scaffolding. Scenario: The plan’s bootstrap-recovery and self-review relocation blocks (231-252, 256-275) show `Path(...).read_text()` followed by bare string literals and `if needle not in` without the `for needle in [` / `]:` wrapper used by the real `cleanup_ref` loop (632-646). An implementer copying the fragment literally produces invalid harness Python.
- **Proposed resolution**: Mirror the full `cleanup_ref` loop shape: `for needle in [ ... ]:` before each needle list, plus the self-review SKILL residual check loop header.
