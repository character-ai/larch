### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:1021-1025
- **Concern**: Plan threads REPO into Step 3 pause guard(s) for assert_thin_fence but does not name the timing-ledger guard assert_thin_fence actually pins. Scenario: scripts/test-design-structure.sh assert_thin_fence (lines 80-84) takes the first .pause-requested design-pause-save.sh line in the scoped region and exits before read-design-classification.sh; Step 3 has no classification in-region, so the pinned line is the timing-ledger fence (~1023), not only the run-step3-review driver fence (~1061). REPO only on the driver guard leaves assert_thin_fence Step 3 failing after the new call is added
- **Proposed resolution**: Add ${REPO:+--repo "$REPO"} to the timing-ledger pause-save line in the Step 3 SKILL.md block (and keep it on the driver fence); state explicitly in the plan that assert_thin_fence checks the first pause guard in the step:3..step:3.5 region

### FINDING_2:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:1061-1068
- **Concern**: Moving the Step 3 preview into run-step3-review.sh while the caller captures the whole driver with command substitution means the preview is withheld until the long-running review finishes. Scenario: The plan claims the user still sees ## Plan Candidate for Review before voting and can ask show full plan, but _plan_review_out=$(...) captures FD 3 output and the thin fence only echoes display lines after the driver returns
- **Proposed resolution**: Keep the preview in a separate pre-review display fence, or change the handoff to stream display lines before review starts while still preserving the KV fallback

### FINDING_3:
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/run-step3-review.sh (proposed) + skills/design/scripts/test-emit-design-plan-preview.sh:128-136
- **Concern**: Driver sentinel touch not scoped to renderer outcomes. Scenario: Plan moves `.step3-entry-plan-printed` to the driver with first-entry touch after capture, and edge cases only require touch for missing/empty `plan.txt`. It does not preserve emit-design-plan-preview.sh behavior (and test-emit-design-plan-preview.sh d9) where allowlist-invalid or missing-dir warnings exit 0 without creating the sentinel. An unconditional touch after any first-entry capture would permanently suppress preview on a later valid re-entry.
- **Proposed resolution**: Touch the sentinel only on successful preview output or the documented missing/empty-plan warning path; do not touch on allowlist-invalid or missing/invalid tmpdir warnings. Migrate the d9 no-sentinel assertion into `test-run-step3-review.sh` (driver-owned sentinel).

### FINDING_4:
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:1082-1094
- **Concern**: Preview text is added to the same stdout stream as fallback KVs, but the planned thin fence still parses allowlisted KEY=value lines before the driver’s real KVs can win.. Scenario: If .step3-review-result.env is symlinked or missing, a plan body/code block line like LOOP_STATUS=complete or STEP3_REVIEW_CAP_REACHED=false can populate state before the driver’s final KVs; because rc=0 fallback only fills missing values, the real LOOP_STATUS=cap-reached or panel-failed is ignored and Step 3 can take the wrong branch silently.
- **Proposed resolution**: When no safe result env was loaded, let later stdout KVs overwrite earlier stdout values so the driver’s terminal KVs win; keep file-first precedence only when a non-symlink result env was read. Add a harness case with preview text containing an allowlisted fake KV before real KVs.

### FINDING_5:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:1059-1096
- **Concern**: Folding step3 preview into captured run-step3-review.sh defers all emit output until the driver exits. Scenario: _plan_review_out=$(...) blocks until plan-review-loop finishes; post-capture display echo shows ## Plan Candidate for Review only after the panel completes, breaking pre-voting preview and the show-full-plan interrupt (skills/design/SKILL.md:1027)
- **Proposed resolution**: Keep preview uncaptured in the same Step 3 driver fence before the capture (sentinel-gated emit-design-plan-preview call), or split a fast preview-only driver invocation; do not rely on driver-inside preview plus post-capture echo for pre-panel chat order

### FINDING_6:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:1062-1067
- **Concern**: Folded preview is buffered by command substitution. Scenario: The driver may emit the preview before launching reviewers, but SKILL.md captures all driver stdout in _plan_review_out and only echoes it after run-step3-review.sh exits, so the user cannot see Plan Candidate for Review or request show full plan before the long review begins
- **Proposed resolution**: Keep the existing separate preview fence for this SIMPLE phase, or rework the handoff so preview/display streams live while only allowlisted KVs are captured

### FINDING_7:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:1021-1105
- **Concern**: Preview folded into driver capture cannot appear before plan-review-loop. Scenario: Removing the standalone preview fence and echoing non-KV lines only after `_plan_review_out=$(run-step3-review.sh …)` completes buffers preview on FD 3 until the driver exits; on a normal panel path the operator sees the plan only after the long review, breaking the Step 3 / issue-anchored chat-order contract and the "show full plan" interrupt before voting
- **Proposed resolution**: Keep a pre-driver preview turn (minimal fence or a driver subcommand invoked before `plan-review-loop.sh`), or document and test a streaming path; do not rely on post-capture echo alone if temporal order is required

### FINDING_8:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/design/SKILL.md:1027-1067
- **Concern**: Folding the preview into the same foreground driver call removes the promised before-voting interrupt point for large plans. Scenario: A large plan prints only the summary, but run-step3-review.sh immediately launches plan-review-loop.sh in the same Bash call, so the user cannot request "show full plan" before reviewers start
- **Proposed resolution**: Keep a separate yield/fence for the summary-mode "show full plan" path, or explicitly remove that contract from SKILL.md and the preview note instead of claiming behavior is preserved

### FINDING_9:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: security
- **Location**: skills/design/SKILL.md:1063-1096; skills/design/scripts/run-step3-review.sh:74-92
- **Concern**: The plan mixes untrusted preview text with machine KVs in the same captured stdout stream and then parses allowlisted KEY=value lines from it. Scenario: If plan.txt contains a line such as STEP3_REVIEW_CAP_REACHED=true or VOTING_TALLY_FILE=/tmp/x, the stdout fallback path can consume preview text before the real driver KVs and corrupt Step 3 state, especially when .step3-review-result.env is symlinked or missing
- **Proposed resolution**: Keep machine stdout distinguishable from display output, for example by parsing only after an explicit KV-begin marker emitted after the preview, or by preserving a separate preview fence while leaving driver stdout KV-only

### FINDING_10:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: latent
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:200-201,231-237
- **Concern**: Plan states the missing or empty plan.txt edge case but the testing strategy does not require validating it after sentinel ownership moves to run-step3-review.sh. Scenario: If the driver forgets to touch .step3-entry-plan-printed on the warning-only render path, Step 3 re-entry can repeatedly warn/re-render despite the stated sentinel contract
- **Proposed resolution**: Add one test-run-step3-review.sh case with missing or empty plan.txt asserting the warning is emitted, .step3-entry-plan-printed is created, and the review loop still proceeds

### FINDING_11:
- **Reviewer(s)**: Cursor-dyn-caller-enumeration
- **Severity**: important
- **Focus area**: security
- **Location**: skills/design/scripts/run-step3-review.sh:41-54 (planned preview block)
- **Concern**: Driver plan unconditionally touches `.step3-entry-plan-printed` after every first-entry renderer call. Scenario: When `--design-tmpdir` fails allowlist validation the pure `step3` renderer prints `**⚠ 3: DESIGN_TMPDIR not under allowlist**` and exits 0 without writing the sentinel (`skills/design/scripts/emit-design-plan-preview.sh:99-101`; harness `skills/design/scripts/test-emit-design-plan-preview.sh:128-133`). The driver would still `: > .step3-entry-plan-printed`, writing under a disallowed path and suppressing later preview attempts on re-entry — regressing the allowlist hardening documented in `SECURITY.md:121`
- **Proposed resolution**: Only create the sentinel when preview actually rendered (e.g. captured stdout contains `## Plan Candidate for Review`) or on the intentional missing/empty `plan.txt` path; never on allowlist-failure or missing-tmpdir warnings. Add a `test-run-step3-review.sh` case mirroring the disallowed-tmpdir harness (`d9`) asserting no sentinel file is created

### FINDING_12:
- **Reviewer(s)**: Codex-dyn-caller-enumeration
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: docs/linting.md:224
- **Concern**: Step 6 drift sweep omits docs/linting.md even though it documents test-emit-design-plan-preview coverage for step3 sentinel idempotency. Scenario: The PR removes sentinel ownership from test-emit-design-plan-preview.sh, but the linting docs would still tell maintainers that this harness covers old script-owned sentinel idempotency
- **Proposed resolution**: Add docs/linting.md to the sweep/update list and revise the make test-emit-design-plan-preview row to describe step3 pure-renderer coverage plus driver-owned sentinel coverage in test-run-step3-review.sh

### FINDING_13:
- **Reviewer(s)**: Codex-dyn-caller-enumeration
- **Severity**: latent
- **Focus area**: security
- **Location**: SECURITY.md:121
- **Concern**: Step 6 drift sweep omits SECURITY.md even though it says emit-design-plan-preview.sh validates before its step3/gatec sentinel early exits. Scenario: After sentinel ownership moves to run-step3-review.sh, the security note would still attribute a step3 sentinel write to emit-design-plan-preview.sh
- **Proposed resolution**: Include SECURITY.md in the drift sweep and update the sentence to remove script-owned step3 sentinel wording while preserving the allowlist-warning contract for emit-design-plan-preview.sh
