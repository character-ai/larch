### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: skills/implement/SKILL.md:783-787
- **Concern**: Step 5 plan leaves ambiguous whether prompt-side banner/dynamic_archetypes prose is deleted. Scenario: Orchestrator may keep prompt-side derivation alongside the new Bash fence and hit duplicate/conflicting Step 5 instructions
- **Proposed resolution**: In the SKILL.md update section explicitly remove lines 783-787 and replace with a one-line note that the Step 5 invocation fence prints the banner

### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: latent
- **Focus area**: correctness
- **Location**: skills/implement/scripts/test-implement-bootstrap-invoke.sh
- **Concern**: Item 1 test plan covers only self-derive success not failed derivation. Scenario: Wrapper regressions that skip export or accept empty CLAUDE_PLUGIN_ROOT may pass CI
- **Proposed resolution**: Add a negative sandbox case asserting non-zero exit and the existing :? guard message when derivation fails

### FINDING_3:
- **Reviewer(s)**: Codex-Arch
- **Severity**: latent
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:783-802
- **Concern**: Step 5 banner resolves dynamic_archetypes_cap from ambient env before session-env even though run-step5-review.sh forwards the session-env cap as review-and-fix --dynamic-archetypes. Scenario: If Step 0 persisted LARCH_DYNAMIC_ARCHETYPES_MAX=3 but the Step 5 shell has LARCH_DYNAMIC_ARCHETYPES_MAX=7, the proposed banner prints cap=7 while the actual review loop runs with cap=3
- **Proposed resolution**: Read $IMPLEMENT_TMPDIR/session-env.sh first or ask run-step5-review.sh for the banner value, then fall back to non-empty ambient LARCH_DYNAMIC_ARCHETYPES_MAX only when the session key is empty; keep 0..8 validation and default 6

### FINDING_4:
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/implement/SKILL.md:783-787
- **Concern**: Step 5 prose not explicitly retired alongside the new banner fence. Scenario: The plan replaces the invocation fence (plan lines 129-160) but the UPDATED SKILL.md section does not require deleting or rewriting the "### Scripted review loop" paragraph that still tells the orchestrator to compute `prior_degraded_rounds` from `$IMPLEMENT_TMPDIR/round-*/review-and-fix.env` (current lines 783-787). An agent can follow the stale prose and re-author prompt-side glob/loop bash in addition to the fenced CLI call, recreating the #3448 syntax/semantics failure mode the change targets.
- **Proposed resolution**: Replace lines 783-787 with a short contract: banner values are computed and printed only inside the Step 5 bash fence below; remove all prompt-side counting instructions for `prior_degraded_rounds` / `effective_round_cap`.

### FINDING_5:
- **Reviewer(s)**: Codex-Edge
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: skills/implement/SKILL.md:783-795
- **Concern**: Step 5 banner resolves dynamic-archetypes in a different order from the launcher. Scenario: With LARCH_DYNAMIC_ARCHETYPES_MAX=7 in the ambient shell and LARCH_DYNAMIC_ARCHETYPES_MAX=2 in $IMPLEMENT_TMPDIR/session-env.sh, run-step5-review.sh forwards --dynamic-archetypes 2 from session-env, but the proposed banner prints dynamic-archetypes cap=7. This silently misreports the actual review configuration.
- **Proposed resolution**: Mirror run-step5-review.sh precedence in the banner fence: read the session-env value first and use it when non-empty; only fall back to ambient LARCH_DYNAMIC_ARCHETYPES_MAX when session-env has no cap, then default to 6.

### FINDING_6:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: architecture
- **Location**: skills/implement/SKILL.md:125-160; scripts/run-step5-review.md:3-5
- **Concern**: [SCOPE-REDUCTION] Item 4 expands the Step 5 SKILL fence with ~25 lines of dynamic_archetypes resolution and banner math instead of keeping the call site thin. Scenario: Item 4 replaces prompt-side glob bash with a tested CLI (good) but still duplicates orchestrator-facing logic that run-step5-review.sh already centralizes: the launcher sources lib-implement-round-cap.sh, reads session-env, knows STARTING_ROUND, and its contract says the goal is to keep the SKILL call site small. The expanded fence reintroduces maintenance surface and re-implements cap precedence beside an existing launcher
- **Proposed resolution**: Have run-step5-review.sh loop mode print the Step 5 breadcrumb to stderr before dispatch (using count_prior_degraded_rounds with STARTING_ROUND and the same dynamic-archetypes precedence review-and-fix uses); keep SKILL.md as rehydrate + one launcher invocation. Optionally drop the separate CLI if the launcher becomes the sole caller

### FINDING_7:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:789-802
- **Concern**: Step 5 banner precheck gives ambient LARCH_DYNAMIC_ARCHETYPES_MAX precedence over the session value that run-step5-review.sh forwards as --dynamic-archetypes. Scenario: With $IMPLEMENT_TMPDIR/session-env.sh containing LARCH_DYNAMIC_ARCHETYPES_MAX=2 and ambient LARCH_DYNAMIC_ARCHETYPES_MAX=bogus, the proposed fence exits 2 before code review; run-step5-review.sh would otherwise pass the valid session value as CLI and review-and-fix.sh would run
- **Proposed resolution**: For the banner, read LARCH_DYNAMIC_ARCHETYPES_MAX from session-env first because the launcher converts it to CLI; only fall back to ambient env when the session key is empty, then default to 6

### FINDING_8:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/implement-bootstrap-invoke.sh:32; skills/implement/SKILL.md:308-318
- **Concern**: Wrapper-only CLAUDE_PLUGIN_ROOT self-derive does not rehydrate the Step 0 parent shell after a successful invoke. Scenario: Child export of a derived CLAUDE_PLUGIN_ROOT is not visible to the parent Bash subprocess that sources parse-bootstrap-routing-envelope.sh; with parent CLAUDE_PLUGIN_ROOT still empty the post-invoke `. "${CLAUDE_PLUGIN_ROOT}/scripts/parse-bootstrap-routing-envelope.sh"` line resolves to /scripts/... and Step 0 fails after bootstrap succeeded — the same unset-root class #3448 hit, only moved one line later unless the orchestrator hand-sets the variable again
- **Proposed resolution**: Add a minimal post-invoke parent rehydration step in the Step 0 fence (extract IMPLEMENT_TMPDIR from _inv_out, source $IMPLEMENT_TMPDIR/plugin-root.env, then source parse-bootstrap-routing-envelope.sh) or have implement-bootstrap-invoke.sh emit a machine-readable CLAUDE_PLUGIN_ROOT= line the parent already consumes before parse

### FINDING_9:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: architecture
- **Location**: plan.txt
- **Concern**: Plan lacks a ## Acceptance section with verifiable criteria. Scenario: Preflight plan-adequacy audit requires ## Acceptance with measurable checks; only ### Testing strategy is present under ## Plan
- **Proposed resolution**: Append ## Acceptance listing concrete pass/fail checks (e.g. bootstrap invoke succeeds with CLAUDE_PLUGIN_ROOT unset; append-execution-issue usage errors emit USAGE=; Step 5 banner uses lib-implement-round-cap.sh CLI; listed make targets pass)

### FINDING_10:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: architecture
- **Location**: skills/implement/SKILL.md:105-115
- **Concern**: [SCOPE-REDUCTION] Plan adds an Item 1 note in the Bash block prelude even though the approved SKILL.md surface is the Step 5 Scripted review loop banner paragraph only. Scenario: This touches brittle global rehydration guidance for no required behavior change; Item 1 is already covered by the wrapper self-derive plus wrapper docs/tests, expanding the SIMPLE-tier change
- **Proposed resolution**: Remove the Item 1 SKILL.md prelude update and keep SKILL.md edits limited to the Step 5 banner/run-step5-review fence

### FINDING_11:
- **Reviewer(s)**: Cursor-dyn-scope-control
- **Severity**: important
- **Focus area**: architecture
- **Location**: skills/implement/SKILL.md:105-115
- **Concern**: [SCOPE-REDUCTION] Plan adds Item 1 doc to Bash block prelude outside approved SKILL surface. Scenario: Approved outline limits SKILL edits to ### Scripted review loop only; prelude note duplicates implement-bootstrap-invoke.md contract and widens diff
- **Proposed resolution**: Drop the Bash block prelude exception note; keep wrapper self-derive documented only in scripts/implement-bootstrap-invoke.md

### FINDING_12:
- **Reviewer(s)**: Cursor-dyn-contract-drift
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/implement/SKILL.md:783-787
- **Concern**: Step 5 SKILL update omits explicit removal of prompt-side banner derivation prose. Scenario: The plan adds a merged Bash fence with printf banner + lib-implement-round-cap CLI, but still leaves lines 783-787 instructing the orchestrator to derive dynamic_archetypes_cap/prior_degraded_rounds prompt-side and print a separate backtick template before run-step5-review.sh — the #3448 failure mode (re-authors invalid glob/bash prompt-side)
- **Proposed resolution**: In the SKILL.md edit, delete or replace paragraphs 783-787 with a short pointer that the fenced block owns banner computation and printing; keep only the merged fence as the normative contract

### FINDING_13:
- **Reviewer(s)**: Codex-dyn-contract-drift
- **Severity**: latent
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:783-795; scripts/run-step5-review.sh:169,236; skills/review-and-fix/scripts/review-and-fix.sh:1241-1244
- **Concern**: Planned Step 5 banner resolves dynamic_archetypes_cap from process env before session-env, but run-step5-review forwards the session-env value as CLI when present, and CLI wins downstream. Scenario: Banner can print one cap while review-and-fix runs with another when both LARCH_DYNAMIC_ARCHETYPES_MAX sources differ
- **Proposed resolution**: Read LARCH_DYNAMIC_ARCHETYPES_MAX from $IMPLEMENT_TMPDIR/session-env.sh first for the banner, then fall back to non-empty process env, then 6

### FINDING_14:
- **Reviewer(s)**: Cursor-dyn-orchestrator-dx
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/implement/SKILL.md:770-775 vs plan.txt:131-160
- **Concern**: Merged Step 5 fence drops step-telemetry-mark.sh. Scenario: Removing the Step 5 entry fence without moving step-telemetry-mark into the merged run-step5-review fence drops the Step 5 token/timing mark that every other major step still emits via step-telemetry-mark.sh
- **Proposed resolution**: Explicitly delete the Step 5 entry fence and prepend step-telemetry-mark.sh (with existing IMPLEMENT_TMPDIR assign/export if timing pins require it) to the merged fence before banner math
