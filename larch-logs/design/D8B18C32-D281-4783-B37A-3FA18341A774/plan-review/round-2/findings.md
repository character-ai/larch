### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/scripts/stall-recovery-report.sh:792-799
- **Concern**: safe_step_value tightening spec omits production STALL_STEP token shapes. Scenario: A literal closed enum of numeric plus N-a/N-b only rejects ship-pr tokens such as 10-detached-head 12-detached-head 10-max-retries 12-max-retries 12d 9a1 12b 12c and 10-head-changed; case 13g and ship-pr.md operator-compat notes require these; titles regress to unknown
- **Proposed resolution**: Anchor full-string allowlist to ship-pr exit_stall inventory in scripts/ship-pr.sh and scripts/ship-pr.md; reject only unmatched strings (e.g. 8ainjected) not hyphenated production suffixes

### FINDING_2:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/references/stall-recovery.md:19
- **Concern**: Dedup normalization is ambiguous and may not set top-level ISSUE_NUMBER. Scenario: /issue duplicate output uses ISSUE_1_DUPLICATE_OF_NUMBER and ISSUE_1_DUPLICATE_OF_URL, not ISSUE_1_NUMBER and ISSUE_1_URL; if step 4 only persists the duplicate keys "also", terminal bug-comment still cannot load ISSUE_NUMBER and falls back to manual filing
- **Proposed resolution**: Specify exact fallback mapping: set ISSUE_NUMBER/ISSUE_URL from ISSUE_1_NUMBER/ISSUE_1_URL when present, else from ISSUE_1_DUPLICATE_OF_NUMBER/ISSUE_1_DUPLICATE_OF_URL; optionally also persist the raw duplicate keys

### FINDING_3:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/scripts/stall-recovery-report.sh:792-799
- **Concern**: The proposed safe_step_value enum is too narrow for existing safe stall-step tokens. Scenario: Restricting to numeric and N-a/N-b shapes would turn documented/current tokens such as STALL_STEP=12d, 8b, 12c, 10-max-retries, and 12-head-changed into unknown, weakening resume routing and public diagnostics
- **Proposed resolution**: Use a full-string parser-safe pattern that preserves known step-family tokens, e.g. numeric 2/3/5/6/8-15 plus either one lowercase suffix letter or hyphenated lowercase/digit words; reject values containing other bytes like 8a<script>

### FINDING_4:
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/references/stall-recovery.md:4 (proposed)
- **Concern**: Dedup normalization omits ISSUE_NUMBER/ISSUE_URL mapping. Scenario: /issue batch dedup emits ISSUE_1_DUPLICATE=true plus ISSUE_1_DUPLICATE_OF_NUMBER/URL, not ISSUE_1_NUMBER/URL. Step 4 prose only maps ISSUE_1_NUMBER→ISSUE_NUMBER and additionally stores DUPLICATE keys; Edge cases claim bug-comment can always read ISSUE_NUMBER/ISSUE_URL. Step 8 loads ISSUE_NUMBER from stall-recovery-issue.env; empty key forces manual terminal comment instead of posting to the canonical duplicate target.
- **Proposed resolution**: In step 4 normalization prose, when ISSUE_1_DUPLICATE=true (or ISSUE_1_NUMBER absent), set ISSUE_NUMBER/ISSUE_URL from ISSUE_1_DUPLICATE_OF_NUMBER/URL; keep DUPLICATE keys as optional metadata.

### FINDING_5:
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/scripts/stall-recovery-report.sh:792-798 (proposed)
- **Concern**: safe_step_value spec may reject live stall tokens. Scenario: Plan narrows sanitizer to numeric plus <N>a/<N>b suffixes. Production STALL_STEP values include 10-max-retries, 10-detached-head, 12d, 9b, and 8b (scripts/ship-pr.md). Over-tightening would emit unknown in issue titles while classify/resume still use raw step; case13g/case7 regressions.
- **Proposed resolution**: Require anchored full-string match that rejects trailing injection (e.g. 8a<script>) but still accepts documented hyphenated/suffixed tokens from ship-pr.md; add one harness assert that 10-max-retries and 12d survive safe_step_value unchanged.

### FINDING_6:
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/scripts/stall-recovery-report.sh:792-798
- **Concern**: Plan may narrow safe_step_value to only numeric or simple letter-suffix tokens. Scenario: The existing contract and tests preserve safe symbolic steps such as 10-detached-head, 12d, and bump-branch-guard; implementing the proposed enum literally would turn them into unknown and break current regression coverage/diagnostics
- **Proposed resolution**: Anchor the sanitizer without shrinking the existing safe token set, e.g. preserve the current numeric alnum/hyphen step family plus explicit symbolic tokens while rejecting unsafe trailing bytes like 8a<script>

### FINDING_7:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/references/stall-recovery.md:41-46
- **Concern**: Dedup stdout normalization does not populate ISSUE_NUMBER/ISSUE_URL. Scenario: On dedup /issue emits ISSUE_1_DUPLICATE=true plus ISSUE_1_DUPLICATE_OF_NUMBER/URL only; mapping ISSUE_1_NUMBER leaves both empty so step 8 bug-comment cannot target the canonical issue
- **Proposed resolution**: In step 4 prose: when ISSUE_1_DUPLICATE=true or ISSUE_1_NUMBER is absent, set ISSUE_NUMBER/ISSUE_URL from ISSUE_1_DUPLICATE_OF_NUMBER/URL (still persist DUPLICATE keys if useful)

### FINDING_8:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/references/stall-recovery.md:82 (plan.txt:41-47)
- **Concern**: FINDING_1: Dedup normalization is internally ambiguous. The plan says to persist ISSUE_1_DUPLICATE_OF_NUMBER and ISSUE_1_DUPLICATE_OF_URL, but Step 8 later reads only ISSUE_NUMBER and ISSUE_URL.. Scenario: If /larch:issue deduplicates the recovery issue, stall-recovery-issue.env can lack top-level ISSUE_NUMBER, so terminal bug-comment falls back to manual filing instead of commenting on the duplicate target.
- **Proposed resolution**: Make Step 4 explicit: write ISSUE_NUMBER from ISSUE_1_NUMBER else ISSUE_1_DUPLICATE_OF_NUMBER, and ISSUE_URL from ISSUE_1_URL else ISSUE_1_DUPLICATE_OF_URL. Optionally keep duplicate-specific keys too.

### FINDING_9:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/scripts/stall-recovery-report.sh:792-799 (plan.txt:54-60)
- **Concern**: FINDING_2: The safe_step_value wording may narrow valid documented stall tokens to unknown. Existing contracts and tests preserve hyphenated tokens such as 10-detached-head and ship-pr documents 10-max-retries, 12-max-retries, and bump-branch-guard.. Scenario: If implemented as the parenthetical numeric plus letter-suffix enum, existing test-stall-recovery-report case 13g fails and public stall reports lose actionable step tokens.
- **Proposed resolution**: Revise the plan to anchor the existing allowed token family instead of narrowing it, e.g. use a full-string regex over numeric, alnum/hyphen step-family tokens, and explicit bump-branch-guard/unknown while rejecting unsafe trailing bytes.

### FINDING_10:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/scripts/stall-recovery-report.sh:792-798
- **Concern**: Proposed safe_step_value closed enum is narrower than pinned step tokens. Scenario: Literal `<N>a`/`<N>b`-only matching breaks case 13g (`10-detached-head`), case 7 (`10-max-retries`), and case 20a (`12d`) STALL_STEP preservation; issue titles degrade to `unknown`
- **Proposed resolution**: Keep existing production suffix shapes (single-letter like `12d`, hyphenated like `10-detached-head` / `10-max-retries`) in the allowlist while rejecting unconstrained trailing injection (e.g. anchored regex); or explicitly update those harness cases in the same PR

### FINDING_11:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: scripts/test-implement-structure.sh:132-180
- **Concern**: FINDING_1: Proposed wiring grep is still too broad. Scenario: It can pass if any --input-file prose line mentions stall-recovery-issue-input.md while the actual /larch:issue --input-file call still uses stall-recovery-bug-body.md
- **Proposed resolution**: Narrow the assertion to the actual /larch:issue --input-file line in Step 4 and also reject stall-recovery-bug-body.md on that line.

### FINDING_12:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:56-59
- **Concern**: skills/implement/scripts/stall-recovery-report.sh:792-798. Scenario: Plan narrows safe_step_value to numeric and <N>a/<N>b only
- **Proposed resolution**: Production STALL_STEP tokens such as 10-detached-head 10-max-retries 12d and 12-detached-head (scripts/ship-pr.md:128-129) no longer match; classify/issue titles regress to unknown and harness case 13g (skills/implement/scripts/test-stall-recovery-report.sh:335-341) breaks Keep the existing step-family allowlist (same shapes as resume_hint_for) or enumerate all ship-pr stall tokens; do not restrict to <N>a/<N>b only; add an explicit regression row for a hyphen-suffixed token if the sanitizer changes

### FINDING_13:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-implement-structure.sh (plan.txt:70-74)
- **Concern**: Finding 1: Planned grep can pass while `/larch:issue` still uses the raw bug body. Scenario: The assertion only checks that some `--input-file` line contains `stall-recovery-issue-input.md`; a wrong command like `/larch:issue --input-file ...stall-recovery-bug-body.md # not stall-recovery-issue-input.md` would still pass and restore the zero-item filing bug.
- **Proposed resolution**: Match the actual Step 4 `/larch:issue --input-file` command and reject the raw body path, e.g. require `/larch:issue --input-file .*stall-recovery-issue-input.md` and fail on `--input-file .*stall-recovery-bug-body.md`.

### FINDING_14:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/references/stall-recovery.md (plan.txt:41-47,142-145)
- **Concern**: Finding 2: Dedup normalization is ambiguous for the top-level keys Step 8 reads. Scenario: `/issue` duplicate output uses `ISSUE_1_DUPLICATE_OF_NUMBER` / `ISSUE_1_DUPLICATE_OF_URL`, not `ISSUE_1_NUMBER` / `ISSUE_1_URL`; the plan says to “also persist” duplicate keys but does not clearly require `ISSUE_NUMBER` / `ISSUE_URL` aliases for dedup, so terminal comments can miss the recovery issue.
- **Proposed resolution**: Revise Step 4 to explicitly set `ISSUE_NUMBER` / `ISSUE_URL` from `ISSUE_1_NUMBER` / `ISSUE_1_URL`, or from `ISSUE_1_DUPLICATE_OF_NUMBER` / `ISSUE_1_DUPLICATE_OF_URL` on dedup.

### FINDING_15:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: latent
- **Focus area**: security
- **Location**: skills/implement/scripts/test-stall-recovery-report.sh (plan.txt:55-60,86-90)
- **Concern**: Finding 3: Unsafe-step regression allows a result the sanitizer contract forbids. Scenario: The code requirement says non-matching values must become `unknown`, but the planned test accepts `8a` for `8a<script>`; a truncating sanitizer would pass the test while violating the stated full-string match contract.
- **Proposed resolution**: Assert the exact emitted step is `unknown` for `8a<script>` and also assert the trailing injected bytes are absent.

### FINDING_16:
- **Reviewer(s)**: Cursor-dyn-script-contract
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-implement-structure.sh:70-74 (proposed); skills/implement/references/stall-recovery.md:38-40 (proposed)
- **Concern**: Wiring grep requires filename on same line as --input-file but plan prose wraps them. Scenario: Structure harness fails after stall-recovery.md rewrite, or prose is contorted onto one line
- **Proposed resolution**: Put `/larch:issue --input-file $IMPLEMENT_TMPDIR/stall-recovery-issue-input.md` on one line in step 4, or grep the step-4 section for both tokens without same-line constraint

### FINDING_17:
- **Reviewer(s)**: Cursor-dyn-script-contract
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/scripts/stall-recovery-report.sh:792-799; skills/implement/scripts/test-stall-recovery-report.sh:335-341
- **Concern**: Plan narrows safe_step_value to numeric and N+a/N+b only. Scenario: Existing tokens like 12d and 10-detached-head become unknown in public issue titles; case 13g/20a regress
- **Proposed resolution**: Specify full-string match (reject 8a<script> trailing junk) while preserving known suffix shapes already in harnesses; add explicit regression note for 12d and hyphenated step tokens

### FINDING_18:
- **Reviewer(s)**: Cursor-dyn-key-chain-integrity
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/references/stall-recovery.md:41-47
- **Concern**: Dedup normalization keeps indexed DUPLICATE_OF keys instead of mapping to ISSUE_NUMBER/ISSUE_URL. Scenario: Batch /issue dedup emits ISSUE_1_DUPLICATE_OF_NUMBER/URL only (skills/issue/SKILL.md:332-337); no ISSUE_1_NUMBER. Step 4 prose says also persist DUPLICATE_OF keys; step 8 reads ISSUE_NUMBER only (stall-recovery.md:32). Terminal bug-comment posts to wrong issue or manual path.
- **Proposed resolution**: Rewrite step 4: when ISSUE_1_DUPLICATE=true, map ISSUE_1_DUPLICATE_OF_NUMBER→ISSUE_NUMBER and ISSUE_1_DUPLICATE_OF_URL→ISSUE_URL (mirror oos-pipeline.md:48-49). Else map ISSUE_1_NUMBER/URL. Align Edge cases with Files section.
