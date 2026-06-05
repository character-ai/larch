### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: skills/design/SKILL.md:303-313
- **Concern**: /design Step 0 gate stays prose-only while the 0a session-setup fence ends at line 303; the gate paragraph still says values come from the parse above with no mechanical rehydration. Scenario: After a fresh Bash tool call, shell variables from the 0a parse are gone; orchestrators can pass empty --codex-present/--cursor-present (same class as /implement #3514), triggering false BOTH_DOWN and the new PRESENCE_INPUT_EMPTY signal on healthy sessions
- **Proposed resolution**: Add a fenced bash block before degraded-tools-gate.sh that sources ~/.cache/larch/sessions/current-design-env-$PPID.sh (or $DESIGN_TMPDIR/source-env.sh) and passes the four flags with ${VAR:-false} defaults, mirroring the /implement durable-rehydration fence; optional follow-up: test-design-structure.sh pins

### FINDING_2:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:109-113,332
- **Concern**: Proposed /implement gate fence is not self-contained because it starts with read-session-env-key.sh but omits the required post-Step-0 CLAUDE_PLUGIN_ROOT rehydration prelude. Scenario: Fresh Bash blocks after Step 0 do not inherit CLAUDE_PLUGIN_ROOT, so the durable presence reads can fail before degraded-tools-gate.sh runs, leaving the root-cause fix ineffective
- **Proposed resolution**: Prepend the canonical plugin-root.env source guard to the new gate fence before the four read-session-env-key.sh reads, or explicitly state the gate fence must include the existing post-Step-0 Bash prelude

### FINDING_3:
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:332-337
- **Concern**: Planned degraded-tools gate fence lists only read-session-env-key reads and gate invocation; it omits the IMPLEMENT_TMPDIR export and CLAUDE_PLUGIN_ROOT rehydration prelude used by every other post-Step-0 Bash fence. Scenario: A fresh Bash tool call cannot resolve ${CLAUDE_PLUGIN_ROOT}/scripts/read-session-env-key.sh (or may use a stale/wrong root); reads fail or yield empty flags and the gate still false-positives BOTH_DOWN without fixing the #3514 root cause
- **Proposed resolution**: Prefix the new fence with IMPLEMENT_TMPDIR export plus the plugin-root.env / session-env.sh awk rehydration block from the dirty-tree recovery fence (skills/implement/SKILL.md:341-345); optionally pin those prelude tokens in test-implement-structure.sh alongside the planned rehydration pins

### FINDING_4:
- **Reviewer(s)**: Codex-Edge
- **Severity**: latent
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:332; scripts/read-session-env-key.sh:18-21
- **Concern**: Proposed /implement rehydration defaults presence reads to false before calling the gate, which masks empty durable presence values.. Scenario: read-session-env-key.sh emits the default for missing OR empty values, so if session-env.sh has CODEX_PRESENT= empty or omits it, degraded-tools-gate.sh receives --codex-present false and cannot emit PRESENCE_INPUT_EMPTY=true; the run looks like a legitimate outage instead of a rehydration/session-env bug.
- **Proposed resolution**: For presence keys only, read raw values without --default or separately test the raw value before defaulting, then pass empty through to degraded-tools-gate.sh; keep binary-found defaults if legacy compatibility requires them.

### FINDING_5:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:107-110,332
- **Concern**: The proposed /implement gate fence rehydrates presence keys via ${CLAUDE_PLUGIN_ROOT}/scripts/read-session-env-key.sh but does not require the mandatory post-Step-0 CLAUDE_PLUGIN_ROOT source guard. Scenario: In a fresh Bash block after Step 0, CLAUDE_PLUGIN_ROOT is not inherited, so the read-session-env-key calls can fail before the degraded-tools gate runs; this defeats the root-cause fix and the new loud empty-presence signal
- **Proposed resolution**: Add the canonical plugin-root.env source guard at the top of the new fenced gate block before all read-session-env-key calls, then invoke degraded-tools-gate.sh with the rehydrated values

### FINDING_6:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:332-336
- **Concern**: Proposed degraded-tools gate fence omits IMPLEMENT_TMPDIR export and CLAUDE_PLUGIN_ROOT rehydration before the four read-session-env-key.sh calls. Scenario: The plan calls the fence self-contained across fresh Bash tool calls, but read-session-env-key.sh and degraded-tools-gate.sh both need CLAUDE_PLUGIN_ROOT and session-env.sh needs IMPLEMENT_TMPDIR; a literal paste of the four reads plus gate invocation fails or re-triggers PRESENCE_INPUT_EMPTY
- **Proposed resolution**: Prepend the same two-line guard used in adjacent implement fences (export IMPLEMENT_TMPDIR, source plugin-root.env or awk LARCH_CLAUDE_PLUGIN_ROOT from session-env.sh, export CLAUDE_PLUGIN_ROOT) before the four reads; optionally pin those tokens in test-implement-structure.sh

### FINDING_7:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:332-369
- **Concern**: Planned implement gate fence rehydrates presence keys but omits the standard IMPLEMENT_TMPDIR and CLAUDE_PLUGIN_ROOT rehydration needed for a fresh Bash block. Scenario: A fresh Bash tool call can have empty IMPLEMENT_TMPDIR or CLAUDE_PLUGIN_ROOT; read-session-env-key then cannot read the durable file and defaults values to false, suppressing the new empty-input signal and misclassifying the gate as a real outage
- **Proposed resolution**: Add the existing minimal prelude before the four reads: export IMPLEMENT_TMPDIR, source $IMPLEMENT_TMPDIR/plugin-root.env or recover CLAUDE_PLUGIN_ROOT from session-env.sh, then call read-session-env-key and degraded-tools-gate.sh

### FINDING_8:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:313
- **Concern**: /design gate hardening is prose-only: no prelude source or durable read in a Bash fence before degraded-tools-gate.sh. Scenario: The Step 0a session-setup fence ends before the gate paragraph; a fresh Bash call still expands empty $CODEX_PRESENT/$CURSOR_PRESENT (same cross-block bug class as /implement) despite Approach layer 1 promising prelude-sourced durable values
- **Proposed resolution**: Add a minimal fenced block that sources ~/.cache/larch/sessions/current-design-env-$PPID.sh (or reads the four keys from $DESIGN_TMPDIR/source-env.sh) immediately before the gate invocation, matching the Step 1c prelude consumer pattern

### FINDING_9:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/implement/SKILL.md:332
- **Concern**: Proposed self-contained gate fence lists only read-session-env-key.sh plus degraded-tools-gate.sh; it omits the canonical CLAUDE_PLUGIN_ROOT rehydration guards used in every other post-Step-0 /implement Bash fence. Scenario: A fresh Bash block after bootstrap may lack CLAUDE_PLUGIN_ROOT; the new reads can fail before session-env is reached, especially on resume/dirty-tree paths
- **Proposed resolution**: Include the same plugin-root.env / session-env.sh awk guard lines from the Step 0 bootstrap fence (lines 299-301) before the four read-session-env-key.sh calls in the new gate fence

### FINDING_10:
- **Reviewer(s)**: Cursor-dyn-env-boundary
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:313-313
- **Concern**: /design Step 0 gate is prose-only across a Bash boundary while 0a parse lives inside the closed 0a fence. Scenario: After 0a returns, a fresh Bash (or mental vars from session-setup parse) still passes empty --codex-present/--cursor-present; PRESENCE_INPUT_EMPTY fires or BOTH_DOWN misprompts despite healthy tools
- **Proposed resolution**: Minimum-change: invoke degraded-tools-gate.sh at the tail of the existing 0a bash block (same subshell as session-setup parse and write-design-current-env), or add a fenced block that sources ~/.cache/larch/sessions/current-design-env-$PPID.sh then passes "$CODEX_*"/"$CURSOR_*" — mirror the /implement mechanical fence, not prose alone

### FINDING_11:
- **Reviewer(s)**: Codex-dyn-env-boundary
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:105-115,332
- **Concern**: Proposed /implement gate fence omits the required plugin-root rehydration before read-session-env-key.sh. Scenario: After Step 0, fresh Bash calls do not inherit CLAUDE_PLUGIN_ROOT; the new self-contained gate block can fail before reading session-env, especially on resume/dirty-tree paths
- **Proposed resolution**: Add the canonical plugin-root source guard before the four read-session-env-key.sh calls, or state the fence must run inside a Bash block that already rehydrated CLAUDE_PLUGIN_ROOT

### FINDING_12:
- **Reviewer(s)**: Codex-dyn-env-boundary
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: scripts/write-design-current-env.sh:191-219; skills/design/scripts/design-init-runparams.sh:163-181; skills/design/scripts/design-route.sh:326-342; skills/design/SKILL.md:65-76,313
- **Concern**: The /design wording assumes prelude-sourced source-env preserves all four gate keys, but refresh paths only recover presence/available booleans. Scenario: After Step 0b or pause-resume refresh, CODEX_BINARY_FOUND/CURSOR_BINARY_FOUND can disappear from source-env; a later fresh gate block loses binary-missing precision or passes empty binary flags
- **Proposed resolution**: Either narrow the /design gate wording to the immediate Step 0a source-env before refresh, or extend write-design-current-env docs/tests/recovery to preserve CODEX_BINARY_FOUND and CURSOR_BINARY_FOUND on refresh/resume

### FINDING_13:
- **Reviewer(s)**: Cursor-dyn-gate-contract
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-degraded-tools-gate.sh:42-51
- **Concern**: Proposed harness cases assert stderr resolved-empty diagnostics but do not require 2>&1 capture. Scenario: New empty-presence cases that invoke the gate with stdout-only capture (as in current Case 5 line 92) will miss larch_err stderr lines; stderr substring assertions pass vacuously or get dropped and the ERROR-vs-WARNING contract regresses silently
- **Proposed resolution**: Add an explicit Testing strategy requirement: every new empty-presence case must use the Case 8/9 pattern (bash "$GATE" … 2>&1) before assert_contains on resolved empty / flag-name stderr substrings

### FINDING_14:
- **Reviewer(s)**: Cursor-dyn-harness-pins
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-implement-structure.sh:44-46
- **Concern**: Proposed positive pins are file-wide grep -Fq needles that already exist in skills/implement/SKILL.md today (read-session-env-key at Step 2 ~513, degraded-tools-gate.sh in gate prose ~332). Scenario: CI passes without adding the new gate Bash fence; rehydration bug at the continue-path gate call is not pinned
- **Proposed resolution**: Scope pins to the Degraded-tools gate region (awk between gate heading and next Step 0 subsection) or require read-session-env-key lines inside the same ```bash fence as degraded-tools-gate.sh --skill implement

### FINDING_15:
- **Reviewer(s)**: Codex-dyn-harness-pins
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-degraded-tools-gate.sh:42-51
- **Concern**: Planned empty-presence tests rely on contains-style assertions and do not require the diagnostic to be on stderr or cover the omitted-flag empty-env path that the plan promises.. Scenario: An implementation using emit instead of larch_err, or only checking passed-empty flags, can still satisfy merged-output substring tests while Step 0 KV parsers receive prose on stdout or omitted empty env stays silent.
- **Proposed resolution**: For one empty case, capture stdout and stderr separately; assert PRESENCE_INPUT_EMPTY=true only on stdout, resolved-empty diagnostics only on stderr, and add one omitted-presence-flags case with empty env and no WARNING.

### FINDING_16:
- **Reviewer(s)**: Codex-dyn-harness-pins
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:332
- **Concern**: Planned grep-only structural pins do not prove the rehydrated values feed the degraded-tools-gate call in the same fenced block.. Scenario: A future edit can keep --key CODEX_PRESENT --default false, --file "$IMPLEMENT_TMPDIR/session-env.sh", and degraded-tools-gate.sh somewhere nearby while the invocation still passes stale bootstrap variables or omits one flag.
- **Proposed resolution**: Use a small awk window over the gate fence/paragraph to require all four read-session-env-key assignments and the subsequent degraded-tools-gate invocation with the four matching "$CODEX_PRESENT"/"$CURSOR_PRESENT"/"$CODEX_BINARY_FOUND"/"$CURSOR_BINARY_FOUND" operands.

### FINDING_17:
- **Reviewer(s)**: Codex-dyn-harness-pins
- **Severity**: nit
- **Focus area**: risk-integration
- **Location**: scripts/test-degraded-tools-gate.md:18-19
- **Concern**: The plan updates this contract file but does not call out the existing shard drift: it says test-harnesses-1 while Makefile registers test-degraded-tools-gate under test-harnesses-4.. Scenario: After the PR, the extended case inventory can still point maintainers to the wrong shard.
- **Proposed resolution**: While extending the case inventory, change the wiring sentence to test-harnesses-4.
