### FINDING_1: Step 5 prompt-side banner derivation prose is not explicitly removed
- **Reviewer(s)**: Cursor-Arch, Cursor-Edge, Cursor-dyn-contract-drift
- **Severity**: important
- **Concern**: The plan adds a Bash-owned Step 5 banner path but does not clearly retire the existing SKILL.md prose that tells the orchestrator to compute banner values prompt-side, leaving duplicate or conflicting instructions and reintroducing the prompt-side bash failure mode.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: In the SKILL.md update section explicitly remove lines 783-787 and replace with a one-line note that the Step 5 invocation fence prints the banner
  - From Cursor-Edge: Replace lines 783-787 with a short contract: banner values are computed and printed only inside the Step 5 bash fence below; remove all prompt-side counting instructions for `prior_degraded_rounds` / `effective_round_cap`.
  - From Cursor-dyn-contract-drift: In the SKILL.md edit, delete or replace paragraphs 783-787 with a short pointer that the fenced block owns banner computation and printing; keep only the merged fence as the normative contract

### FINDING_2: Bootstrap self-derive tests lack a negative failure case
- **Reviewer(s)**: Cursor-Arch
- **Severity**: latent
- **Concern**: The proposed test coverage validates successful self-derivation only, so regressions that skip export or tolerate an empty/broken `CLAUDE_PLUGIN_ROOT` could pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add a negative sandbox case asserting non-zero exit and the existing :? guard message when derivation fails

### FINDING_3: Step 5 banner dynamic-archetypes precedence can diverge from the launcher
- **Reviewer(s)**: Codex-Arch, Codex-Edge, Codex-Innovation, Codex-dyn-contract-drift
- **Severity**: important
- **Concern**: The planned Step 5 banner resolves `LARCH_DYNAMIC_ARCHETYPES_MAX` from ambient environment before `session-env.sh`, while `run-step5-review.sh` forwards the session value as CLI when present. The banner can therefore print a different cap than the review loop actually uses, or fail on an invalid ambient value even when the persisted session value is valid.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Read $IMPLEMENT_TMPDIR/session-env.sh first or ask run-step5-review.sh for the banner value, then fall back to non-empty ambient LARCH_DYNAMIC_ARCHETYPES_MAX only when the session key is empty; keep 0..8 validation and default 6
  - From Codex-Edge: Mirror run-step5-review.sh precedence in the banner fence: read the session-env value first and use it when non-empty; only fall back to ambient LARCH_DYNAMIC_ARCHETYPES_MAX when session-env has no cap, then default to 6.
  - From Codex-Innovation: For the banner, read LARCH_DYNAMIC_ARCHETYPES_MAX from session-env first because the launcher converts it to CLI; only fall back to ambient env when the session key is empty, then default to 6
  - From Codex-dyn-contract-drift: Read LARCH_DYNAMIC_ARCHETYPES_MAX from $IMPLEMENT_TMPDIR/session-env.sh first for the banner, then fall back to non-empty process env, then 6

### FINDING_4: Wrapper self-derive does not rehydrate the parent Step 0 shell
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: If `implement-bootstrap-invoke.sh` self-derives and exports `CLAUDE_PLUGIN_ROOT` only inside the child process, the parent Step 0 Bash subprocess can still have an empty root when it later sources `parse-bootstrap-routing-envelope.sh`, causing a post-bootstrap failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Add a minimal post-invoke parent rehydration step in the Step 0 fence (extract IMPLEMENT_TMPDIR from _inv_out, source $IMPLEMENT_TMPDIR/plugin-root.env, then source parse-bootstrap-routing-envelope.sh) or have implement-bootstrap-invoke.sh emit a machine-readable CLAUDE_PLUGIN_ROOT= line the parent already consumes before parse

### FINDING_5: Plan is missing a verifiable Acceptance section
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Concern**: The plan contains a testing strategy but lacks a required `## Acceptance` section with concrete pass/fail criteria, which can fail plan-adequacy checks.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Append ## Acceptance listing concrete pass/fail checks (e.g. bootstrap invoke succeeds with CLAUDE_PLUGIN_ROOT unset; append-execution-issue usage errors emit USAGE=; Step 5 banner uses lib-implement-round-cap.sh CLI; listed make targets pass)

### FINDING_6: Merged Step 5 fence may drop step telemetry marking
- **Reviewer(s)**: Cursor-dyn-orchestrator-dx
- **Severity**: important
- **Concern**: Replacing the Step 5 entry fence without moving `step-telemetry-mark.sh` into the merged Step 5 fence would remove the Step 5 token/timing marker that other major steps still emit.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-orchestrator-dx: Explicitly delete the Step 5 entry fence and prepend step-telemetry-mark.sh (with existing IMPLEMENT_TMPDIR assign/export if timing pins require it) to the merged fence before banner math

### FINDING_7:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: architecture
- **Location**: skills/implement/SKILL.md:125-160; scripts/run-step5-review.md:3-5
- **Concern**: [SCOPE-REDUCTION] Item 4 expands the Step 5 SKILL fence with ~25 lines of dynamic_archetypes resolution and banner math instead of keeping the call site thin. Scenario: Item 4 replaces prompt-side glob bash with a tested CLI (good) but still duplicates orchestrator-facing logic that run-step5-review.sh already centralizes: the launcher sources lib-implement-round-cap.sh, reads session-env, knows STARTING_ROUND, and its contract says the goal is to keep the SKILL call site small. The expanded fence reintroduces maintenance surface and re-implements cap precedence beside an existing launcher
- **Proposed resolution**: Have run-step5-review.sh loop mode print the Step 5 breadcrumb to stderr before dispatch (using count_prior_degraded_rounds with STARTING_ROUND and the same dynamic-archetypes precedence review-and-fix uses); keep SKILL.md as rehydrate + one launcher invocation. Optionally drop the separate CLI if the launcher becomes the sole caller

### FINDING_8:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: architecture
- **Location**: skills/implement/SKILL.md:105-115
- **Concern**: [SCOPE-REDUCTION] Plan adds an Item 1 note in the Bash block prelude even though the approved SKILL.md surface is the Step 5 Scripted review loop banner paragraph only. Scenario: This touches brittle global rehydration guidance for no required behavior change; Item 1 is already covered by the wrapper self-derive plus wrapper docs/tests, expanding the SIMPLE-tier change
- **Proposed resolution**: Remove the Item 1 SKILL.md prelude update and keep SKILL.md edits limited to the Step 5 banner/run-step5-review fence

### FINDING_9:
- **Reviewer(s)**: Cursor-dyn-scope-control
- **Severity**: important
- **Focus area**: architecture
- **Location**: skills/implement/SKILL.md:105-115
- **Concern**: [SCOPE-REDUCTION] Plan adds Item 1 doc to Bash block prelude outside approved SKILL surface. Scenario: Approved outline limits SKILL edits to ### Scripted review loop only; prelude note duplicates implement-bootstrap-invoke.md contract and widens diff
- **Proposed resolution**: Drop the Bash block prelude exception note; keep wrapper self-derive documented only in scripts/implement-bootstrap-invoke.md
