### FINDING_1: Step 3 REPO threading misses the timing-ledger pause guard
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: The plan only threads `REPO` into the Step 3 review-driver pause guard, but `assert_thin_fence` pins the first `.pause-requested` guard in the Step 3 region, which is the timing-ledger guard. Leaving that guard unchanged can make the structure test fail after adding the new call.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add ${REPO:+--repo "$REPO"} to the timing-ledger pause-save line in the Step 3 SKILL.md block (and keep it on the driver fence); state explicitly in the plan that assert_thin_fence checks the first pause guard in the step:3..step:3.5 region

### FINDING_2: Capturing the Step 3 driver buffers the preview until after review
- **Reviewer(s)**: Codex-Arch, Cursor-Innovation, Codex-Innovation, Cursor-Pragmatic, Codex-Pragmatic
- **Severity**: important
- **Concern**: Moving the preview inside `run-step3-review.sh` while the caller captures the driver with command substitution prevents the user from seeing `## Plan Candidate for Review` before the long review loop starts. This breaks the intended pre-voting preview/show-full-plan interrupt point.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Keep the preview in a separate pre-review display fence, or change the handoff to stream display lines before review starts while still preserving the KV fallback
  - From Cursor-Innovation: Keep preview uncaptured in the same Step 3 driver fence before the capture (sentinel-gated emit-design-plan-preview call), or split a fast preview-only driver invocation; do not rely on driver-inside preview plus post-capture echo for pre-panel chat order
  - From Codex-Innovation: Keep the existing separate preview fence for this SIMPLE phase, or rework the handoff so preview/display streams live while only allowlisted KVs are captured
  - From Cursor-Pragmatic: Keep a pre-driver preview turn (minimal fence or a driver subcommand invoked before `plan-review-loop.sh`), or document and test a streaming path; do not rely on post-capture echo alone if temporal order is required
  - From Codex-Pragmatic: Keep a separate yield/fence for the summary-mode "show full plan" path, or explicitly remove that contract from SKILL.md and the preview note instead of claiming behavior is preserved

### FINDING_3: Driver-owned sentinel touch would suppress later valid previews after renderer warnings
- **Reviewer(s)**: Cursor-Edge, Cursor-dyn-caller-enumeration
- **Severity**: important
- **Concern**: The planned driver sentinel write is not scoped to successful renderer outcomes. If the renderer exits 0 for allowlist-invalid or missing/invalid tmpdir warnings without producing a real preview, an unconditional driver touch would suppress preview on later valid re-entry and could regress allowlist hardening.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Edge: Touch the sentinel only on successful preview output or the documented missing/empty-plan warning path; do not touch on allowlist-invalid or missing/invalid tmpdir warnings. Migrate the d9 no-sentinel assertion into `test-run-step3-review.sh` (driver-owned sentinel).
  - From Cursor-dyn-caller-enumeration: Only create the sentinel when preview actually rendered (e.g. captured stdout contains `## Plan Candidate for Review`) or on the intentional missing/empty `plan.txt` path; never on allowlist-failure or missing-tmpdir warnings. Add a `test-run-step3-review.sh` case mirroring the disallowed-tmpdir harness (`d9`) asserting no sentinel file is created

### FINDING_4: Preview text can be parsed as trusted Step 3 KVs
- **Reviewer(s)**: Codex-Edge, Codex-Pragmatic
- **Severity**: important
- **Concern**: The plan mixes untrusted preview text and machine-readable KVs in the same captured stdout stream. If the safe result env is missing or unsafe, allowlisted-looking lines from `plan.txt` can populate Step 3 state before the driver’s real terminal KVs, causing the wrong branch to be taken.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Edge: When no safe result env was loaded, let later stdout KVs overwrite earlier stdout values so the driver’s terminal KVs win; keep file-first precedence only when a non-symlink result env was read. Add a harness case with preview text containing an allowlisted fake KV before real KVs.
  - From Codex-Pragmatic: Keep machine stdout distinguishable from display output, for example by parsing only after an explicit KV-begin marker emitted after the preview, or by preserving a separate preview fence while leaving driver stdout KV-only

### FINDING_5: Missing or empty plan warning path lacks driver sentinel coverage
- **Reviewer(s)**: Codex-Requirements
- **Severity**: latent
- **Concern**: The plan mentions the missing/empty `plan.txt` edge case, but does not require a driver test proving that this warning-only render path creates `.step3-entry-plan-printed`. If missed, Step 3 re-entry can repeatedly warn/re-render.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Add one test-run-step3-review.sh case with missing or empty plan.txt asserting the warning is emitted, .step3-entry-plan-printed is created, and the review loop still proceeds

### FINDING_6: Drift sweep omits linting docs for moved sentinel coverage
- **Reviewer(s)**: Codex-dyn-caller-enumeration
- **Severity**: latent
- **Concern**: The plan moves Step 3 sentinel ownership from `test-emit-design-plan-preview.sh` coverage to driver coverage, but the Step 6 drift sweep omits `docs/linting.md`, which documents the old harness responsibility.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-caller-enumeration: Add docs/linting.md to the sweep/update list and revise the make test-emit-design-plan-preview row to describe step3 pure-renderer coverage plus driver-owned sentinel coverage in test-run-step3-review.sh

### FINDING_7: Drift sweep omits SECURITY.md allowlist/sentinel wording
- **Reviewer(s)**: Codex-dyn-caller-enumeration
- **Severity**: latent
- **Concern**: The plan moves Step 3 sentinel ownership to `run-step3-review.sh`, but the Step 6 drift sweep omits `SECURITY.md`, which still attributes Step 3 sentinel behavior to `emit-design-plan-preview.sh`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-caller-enumeration: Include SECURITY.md in the drift sweep and update the sentence to remove script-owned step3 sentinel wording while preserving the allowlist-warning contract for emit-design-plan-preview.sh
