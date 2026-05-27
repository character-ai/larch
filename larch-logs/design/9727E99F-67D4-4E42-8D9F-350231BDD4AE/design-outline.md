## Proposed Design Outline

### Goals
- Land Phase 4 of umbrella #2732 by implementing `phase_coder_select` in `scripts/implement-bootstrap.sh` so `/implement` Step 0 owns coder selection end-to-end.
- Collapse `skills/implement/SKILL.md` Step 0 to ~80 lines (±20%) by deleting the four named sub-sections and the inline rehydration boilerplate.
- Add a structural pin in `scripts/test-implement-structure.sh` so future edits cannot drift back to the pre-collapse Step 0 shape.

### Non-goals
- No changes to the Step 2 coder dispatcher or any downstream consumer of `coder` / `coder_fallback`.
- No new bail-reason enum values beyond replacing `not-yet-implemented-phase-4` with `coder-unavailable`.
- No changes to slash-command `--coder` argv parsing in the orchestrator prompt (the prompt continues to resolve `coder_explicit` and validate the input set).

### Approach sketch
- Add `--coder <claude|codex|cursor>` argv to `implement-bootstrap.sh main()` and forward it from SKILL.md Step 0 together with bumping `--up-to-phase plan` → `--up-to-phase coder`.
- Implement `phase_coder_select`: read `CODEX_PRESENT` / `CURSOR_PRESENT` / `CODEX_BINARY_FOUND` / `CURSOR_BINARY_FOUND` via `read-session-env-key.sh`; on explicit `--coder`, verify availability and on mismatch emit the verbatim three-variant warning text (binary-missing / undeterminable / runtime-failed) + `STALL_TRACKING=true` + `IMPLEMENT_BAIL_REASON=coder-unavailable`; on implicit path walk Cursor → Codex → Claude with the simpler `**⚠ X unavailable — falling back to Y implementer.**` text; on implicit-→-claude only, best-effort `larch-log.sh manifest --field coder_fallback=true` and emit `coder_fallback=true` in KV; emit final breadcrumb `→ step0: coder=<coder>`.
- SKILL.md Step 0 aggressive collapse: delete `### Step 0 — tracking issue adoption`, `### Larch-log Batches and Summary Comments`, `### Plan materialization from issue body`, `### Implementer waterfall`, and inline `CLAUDE_PLUGIN_ROOT` rehydration boilerplate inside Step 0 fenced blocks. Keep `### Cross-Skill Presence Propagation`, `## Phantom Untracked Probe`, `## Execution Issues Tracking`, and `### Rebase onto latest main (before implementation)` (Step 1.r). Update the L14 anti-halt reminder per issue body.
- `scripts/test-implement-structure.sh`: add new Step 0 structural pins (fenced bash blocks ≤ 1 inside Step 0, single `implement-bootstrap.sh` invocation inside the Step 0 fence, foreground banner + per-anchor comment present); update or drop existing pins that anchor on deleted SKILL.md headings.
- `skills/implement/scripts/test-implement-bootstrap.sh`: add coder-related test cases (explicit `--coder=cursor` with cursor unavailable → `coder-unavailable` + STALL; implicit waterfall to claude → `coder_fallback=true`; happy-path 5-breadcrumb total-count assertion).

### Surfaces in scope
- `scripts/implement-bootstrap.sh` + `scripts/implement-bootstrap.md`
- `skills/implement/SKILL.md`
- `skills/implement/scripts/test-implement-bootstrap.sh` + sibling `.md`
- `scripts/test-implement-structure.sh` + sibling `.md`

### Open questions
- None. Round 1 resolved the three operator-facing ambiguities; Step 2a sketches will explore architectural alternatives inside `phase_coder_select` (e.g., shared helper for warning emission vs. inline `case` blocks).
