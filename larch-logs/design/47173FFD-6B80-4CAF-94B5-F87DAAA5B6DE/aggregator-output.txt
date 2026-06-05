### FINDING_1: /design Step 0 gate lacks mechanical rehydration across Bash boundary
- **Reviewer(s)**: Cursor-Arch, Cursor-Requirements, Cursor-dyn-env-boundary
- **Severity**: important
- **Concern**: The /design Step 0 degraded-tools gate remains prose-only after the Step 0a Bash fence ends, so fresh Bash calls can lose the parsed tool-presence variables and pass empty or stale values to degraded-tools-gate.sh.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add a fenced bash block before degraded-tools-gate.sh that sources ~/.cache/larch/sessions/current-design-env-$PPID.sh (or $DESIGN_TMPDIR/source-env.sh) and passes the four flags with ${VAR:-false} defaults, mirroring the /implement durable-rehydration fence; optional follow-up: test-design-structure.sh pins
  - From Cursor-Requirements: Add a minimal fenced block that sources ~/.cache/larch/sessions/current-design-env-$PPID.sh (or reads the four keys from $DESIGN_TMPDIR/source-env.sh) immediately before the gate invocation, matching the Step 1c prelude consumer pattern
  - From Cursor-dyn-env-boundary: Minimum-change: invoke degraded-tools-gate.sh at the tail of the existing 0a bash block (same subshell as session-setup parse and write-design-current-env), or add a fenced block that sources ~/.cache/larch/sessions/current-design-env-$PPID.sh then passes "$CODEX_*"/"$CURSOR_*" — mirror the /implement mechanical fence, not prose alone

### FINDING_2: /implement gate fence omits post-Step-0 root/tmpdir rehydration prelude
- **Reviewer(s)**: Codex-Arch, Cursor-Edge, Codex-Innovation, Cursor-Pragmatic, Codex-Pragmatic, Cursor-Requirements, Codex-dyn-env-boundary
- **Severity**: important
- **Concern**: The planned /implement degraded-tools gate fence is not self-contained because it calls read-session-env-key.sh and degraded-tools-gate.sh without first rehydrating CLAUDE_PLUGIN_ROOT and, in several paths, IMPLEMENT_TMPDIR. Fresh Bash blocks after Step 0 may therefore fail before reading durable session state or may misclassify healthy tools as down.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Prepend the canonical plugin-root.env source guard to the new gate fence before the four read-session-env-key.sh reads, or explicitly state the gate fence must include the existing post-Step-0 Bash prelude
  - From Cursor-Edge: Prefix the new fence with IMPLEMENT_TMPDIR export plus the plugin-root.env / session-env.sh awk rehydration block from the dirty-tree recovery fence (skills/implement/SKILL.md:341-345); optionally pin those prelude tokens in test-implement-structure.sh alongside the planned rehydration pins
  - From Codex-Innovation: Add the canonical plugin-root.env source guard at the top of the new fenced gate block before all read-session-env-key calls, then invoke degraded-tools-gate.sh with the rehydrated values
  - From Cursor-Pragmatic: Prepend the same two-line guard used in adjacent implement fences (export IMPLEMENT_TMPDIR, source plugin-root.env or awk LARCH_CLAUDE_PLUGIN_ROOT from session-env.sh, export CLAUDE_PLUGIN_ROOT) before the four reads; optionally pin those tokens in test-implement-structure.sh
  - From Codex-Pragmatic: Add the existing minimal prelude before the four reads: export IMPLEMENT_TMPDIR, source $IMPLEMENT_TMPDIR/plugin-root.env or recover CLAUDE_PLUGIN_ROOT from session-env.sh, then call read-session-env-key and degraded-tools-gate.sh
  - From Cursor-Requirements: Include the same plugin-root.env / session-env.sh awk guard lines from the Step 0 bootstrap fence (lines 299-301) before the four read-session-env-key.sh calls in the new gate fence
  - From Codex-dyn-env-boundary: Add the canonical plugin-root source guard before the four read-session-env-key.sh calls, or state the fence must run inside a Bash block that already rehydrated CLAUDE_PLUGIN_ROOT

### FINDING_3: /implement presence defaults can mask empty durable presence values
- **Reviewer(s)**: Codex-Edge
- **Severity**: latent
- **Concern**: Presence-key reads default to false before calling degraded-tools-gate.sh, so missing or empty durable values can be converted into ordinary false values and suppress PRESENCE_INPUT_EMPTY diagnostics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Edge: For presence keys only, read raw values without --default or separately test the raw value before defaulting, then pass empty through to degraded-tools-gate.sh; keep binary-found defaults if legacy compatibility requires them.

### FINDING_4: /design refresh/resume paths may drop binary-found gate keys
- **Reviewer(s)**: Codex-dyn-env-boundary
- **Severity**: latent
- **Concern**: The /design wording assumes source-env preserves all four gate keys, but refresh and resume paths appear to recover only presence/available booleans, which can lose CODEX_BINARY_FOUND and CURSOR_BINARY_FOUND before later gate calls.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-env-boundary: Either narrow the /design gate wording to the immediate Step 0a source-env before refresh, or extend write-design-current-env docs/tests/recovery to preserve CODEX_BINARY_FOUND and CURSOR_BINARY_FOUND on refresh/resume

### FINDING_5: degraded-tools empty-presence tests may not enforce stderr/stdout contract
- **Reviewer(s)**: Cursor-dyn-gate-contract, Codex-dyn-harness-pins
- **Severity**: important
- **Concern**: The planned degraded-tools gate tests rely on substring assertions that may miss whether diagnostics are emitted on stderr, whether stdout remains machine-readable, and whether omitted empty-env paths are covered.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-gate-contract: Add an explicit Testing strategy requirement: every new empty-presence case must use the Case 8/9 pattern (bash "$GATE" … 2>&1) before assert_contains on resolved empty / flag-name stderr substrings
  - From Codex-dyn-harness-pins: For one empty case, capture stdout and stderr separately; assert PRESENCE_INPUT_EMPTY=true only on stdout, resolved-empty diagnostics only on stderr, and add one omitted-presence-flags case with empty env and no WARNING.

### FINDING_6: implement structural pins may not prove same-fence rehydrated gate invocation
- **Reviewer(s)**: Cursor-dyn-harness-pins, Codex-dyn-harness-pins
- **Severity**: important
- **Concern**: Planned grep-style structure tests can pass using existing file-wide tokens or nearby text without proving that the new gate Bash fence reads all four durable values and passes those same rehydrated variables into degraded-tools-gate.sh.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-harness-pins: Scope pins to the Degraded-tools gate region (awk between gate heading and next Step 0 subsection) or require read-session-env-key lines inside the same ```bash fence as degraded-tools-gate.sh --skill implement
  - From Codex-dyn-harness-pins: Use a small awk window over the gate fence/paragraph to require all four read-session-env-key assignments and the subsequent degraded-tools-gate invocation with the four matching "$CODEX_PRESENT"/"$CURSOR_PRESENT"/"$CODEX_BINARY_FOUND"/"$CURSOR_BINARY_FOUND" operands.

### FINDING_7: degraded-tools contract file points to wrong harness shard
- **Reviewer(s)**: Codex-dyn-harness-pins
- **Severity**: nit
- **Concern**: The planned contract-file update does not address existing shard drift: the document reportedly says test-harnesses-1 while Makefile registers test-degraded-tools-gate under test-harnesses-4.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-harness-pins: While extending the case inventory, change the wiring sentence to test-harnesses-4.
