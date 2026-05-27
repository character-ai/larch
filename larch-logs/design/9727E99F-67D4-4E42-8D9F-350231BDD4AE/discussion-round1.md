## Decision 1: Implicit-waterfall warning text
- **Question**: For Cursor→Codex and Codex→Claude implicit-waterfall transitions, preserve current SKILL.md prompt-side warning text verbatim, or use simpler issue-body example phrasing?
- **Resolution**: Use issue-body example phrasing (e.g., `**⚠ Cursor unavailable — falling back to Codex implementer.**` and analogous `**⚠ Codex unavailable — falling back to Claude implementer.**`). Explicit-coder-unavailable warnings (the `/implement Step 0 (implementer waterfall): --coder=...` hard-error block) remain verbatim per the issue's "with the specific bullet's warning text" wording for the explicit path.
- **Source**: user

## Decision 2: `coder_fallback=true` semantics
- **Question**: Fire `larch-log.sh manifest --field coder_fallback=true` on any path arriving at Claude, or only on the implicit waterfall?
- **Resolution**: Implicit waterfall only. Explicit `--coder=claude` is an operator choice, not a fallback; manifest stays unset on that path.
- **Source**: user

## Decision 3: Existing pin updates in `test-implement-structure.sh`
- **Question**: Update existing pins that reference now-deleted SKILL.md headings (e.g., `### Step 0 — tracking issue adoption`), or strictly add only the new structural pin?
- **Resolution**: Update existing pins to match the collapsed SKILL.md as part of the same PR. Required to satisfy acceptance criterion "make lint passes (including test-implement-structure)".
- **Source**: user

## Decision 4: Rebase Macro 1.r retention
- **Question**: Is `### Rebase onto latest main (before implementation)` (current SKILL.md ~L780) part of the Step 0 collapse zone?
- **Resolution**: Out of scope. It is Step 1.r (Rebase Checkpoint Macro), not a Step 0 sub-section. The issue's anti-halt update wording ("after implement-bootstrap.sh exits, continue to Step 1.r") confirms 1.r is a distinct step. Leave it untouched.
- **Source**: codebase (SKILL.md anti-halt reminder + step:2 marker location)

## Decision 5: `--coder` argv handoff to bootstrap
- **Question**: How does the prompt's resolved `--coder` value reach `phase_coder_select`?
- **Resolution**: Add `--coder <claude|codex|cursor>` argv flag to `implement-bootstrap.sh main()`, paralleling the existing `--issue-number` / `--run-id` / `--forked-target` flags. SKILL.md Step 0 invocation forwards the resolved value. The slash-command argv parsing remains in the orchestrator prompt for now (it owns `coder_explicit` and validation against the available set).
- **Source**: codebase (main() argv pattern; `--caller-env` is reserved for env-file forwarding, less ergonomic for a single token)

## Decision 6: `--up-to-phase` bump in SKILL.md Step 0
- **Question**: Should the orchestrator change `--up-to-phase plan` to a phase that includes coder selection?
- **Resolution**: Yes, bump to `--up-to-phase coder` so `phase_coder_select` actually runs. `all` is reserved for future Phase 5+ expansion; `coder` is the current terminal phase.
- **Source**: codebase (case statement in `implement-bootstrap.sh main()`: only `coder` and `all` invoke `phase_coder_select`)

## Decision 7: Acceptance scope beyond explicit Files-to-modify
- **Question**: Beyond the issue's "Files to modify" list, what other surfaces need updates to satisfy "make lint passes" acceptance?
- **Resolution**:
  - `scripts/test-implement-structure.sh`: update existing pins anchored on deleted SKILL.md headings (per Decision 3).
  - `scripts/implement-bootstrap.md`: update bail-reason enum (drop `not-yet-implemented-phase-4`, add `coder-unavailable`); drop "Future Phase 4 may add …" speculative wording; extend "Behavior mapping (Step 0 SKILL.md)" with the absorbed implementer-waterfall row; ensure Edit-in-sync row covers the new surfaces.
  - `skills/implement/SKILL.md`: bump `--up-to-phase plan` → `--up-to-phase coder`; extend KV parse list (around the line referencing the parse keys) with `coder`, `coder_fallback`; remove the prompt-side implementer-waterfall section; update anti-halt continuation reminder per issue body.
  - `skills/implement/scripts/test-implement-bootstrap.sh`: add the new coder-related test case + total-count breadcrumb assertion (5 `→ step0:` lines on the happy path).
- **Source**: codebase + issue acceptance criteria

## Decision 8: Section retention list (sibling sections vs Step 0 sub-sections)
- **Question**: Confirm which SKILL.md headings between current line 281 and current line 802 stay.
- **Resolution**: STAY: `### Cross-Skill Presence Propagation` (h3, inside Step 0), `## Phantom Untracked Probe` (h2, sibling), `## Execution Issues Tracking` (h2, sibling) and all its h3 sub-sections. DELETE: `### Step 0 — tracking issue adoption`, `### Larch-log Batches and Summary Comments` (move contents into `scripts/implement-bootstrap.md` / its referenced `larch-log-batches.md`), `### Plan materialization from issue body`, `### Implementer waterfall`. Inline fenced-block boilerplate (re-derive `CLAUDE_PLUGIN_ROOT` from `IMPLEMENT_TMPDIR/session-env.sh`, etc.) inside Step 0 fences is included in the deletion sweep — the single `implement-bootstrap.sh` call replaces that boilerplate.
- **Source**: codebase + issue body

Recorded 8 scope/requirements decisions (Decisions 1–3 from user via Step 1c AskUserQuestion; Decisions 4–8 from codebase exploration).
