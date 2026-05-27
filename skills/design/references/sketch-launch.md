# Sketch Launch Choreography

**Consumer**: `/design` Step 2a.2 — external sketch launches (Cursor/Codex) and per-slot Claude fallbacks.

**Contract**: SIMPLE launches 0 sketch agents and writes sentinel artifacts. HARD launches 4 regular sketch slots: 2 Cursor + 2 Codex personality slots on the diagonal split (Cursor-Arch + Cursor-Edge + Codex-Innovation + Codex-Pragmatic), plus the spawn-order rule, `run_in_background: true` + `timeout: 1260000` requirements, and per-slot Claude fallback rules. Token bodies (`<ARCH_PROMPT>` etc.) are resolved from `references/sketch-prompts.md`, not here. Sketch-phase collection (`collect-agent-results.sh` for Step 2a.3) is NOT defined here.

**Sketch fallback divergence from plan-review waterfall**: Sketch phase Claude fallbacks use the Agent tool (Claude Code Reviewer subagent), not `dispatch-with-waterfall.sh` / `launch-claude-review.sh` subprocess.

**When to load**: at Step 2a.2 entry, AFTER `references/sketch-prompts.md` has been loaded. Do NOT load during Steps 0, 1, 2a.3, 2a.4, 2a.5, 2b, 3, 3.5, 3b, 4, or 5.

**Binding convention**: single normative source for the external-slot launch shell blocks (4 HARD slots), the SIMPLE sentinel path, the spawn-order rule, the per-slot `run_in_background: true` / `timeout: 1260000` requirements, and the per-slot Claude fallback notes. Token substitution placeholders (`<ARCH_PROMPT>`, `<EDGE_PROMPT>`, `<INNOVATION_PROMPT>`, `<PRAGMATIC_PROMPT>`) are resolved from `references/sketch-prompts.md`.

---

**Critical sequencing**: For `design_classification == HARD`, you MUST launch all external sketch Bash tool calls (with `run_in_background: true`) AND any Claude subagent fallback sketches in a single message. Issue Cursor slots first (slowest), then Codex slots, then any Claude subagent fallbacks. For `design_classification == SIMPLE`, launch nothing and do not call `collect-agent-results.sh`.

**Launch failure logging**: For every `launch-review.sh` Bash block below, capture launcher stdout/stderr to `$DESIGN_TMPDIR/<slot>-launch.failure.log`. If the Bash tool reports a non-zero exit, append that capture verbatim to `$DESIGN_TMPDIR/execution-issues.md`.

**Personality prompts**: the four personality prompts are shared across external slots (Cursor/Codex) and Claude fallbacks (Agent tool). Token bodies are defined in `references/sketch-prompts.md`.

**MANDATORY — READ ENTIRE FILE before assembling sketch prompts: `skills/design/references/readability-style.md`.**

Before launching, read `skills/design/references/readability-style.md` once and substitute every literal `<READABILITY_STYLE>` token in the assembled prompt body with the full preamble contents.

## SIMPLE Mode

Use when `design_classification == SIMPLE`. This path uses 0 sketch agents: launch no external agents and no Claude fallback agents. Write these sentinel artifacts immediately, then skip Step 2a.5 and proceed directly to Step 2b:

```bash
printf '%s\n' 'NO_SKETCHES_CLASSIFIED_SIMPLE' > "$DESIGN_TMPDIR/approach-synthesis.txt"
printf '%s\n' 'NO_CONTESTED_DECISIONS' > "$DESIGN_TMPDIR/contested-decisions.md"
: > "$DESIGN_TMPDIR/dialectic-resolutions.md"
```

Do not call `collect-agent-results.sh` on this path.

## HARD Mode

Use when `design_classification == HARD`.

**Spawn order**: all 2 Cursor slots first (slowest), then all 2 Codex slots, then any Claude subagent fallbacks. Issue all Bash and Agent tool calls in a single message.

**Cursor — Architecture/Standards** (if `cursor_available`):

```bash
${CLAUDE_PLUGIN_ROOT}/scripts/launch-review.sh --tool cursor --output "$DESIGN_TMPDIR/cursor-sketch-arch-output.txt" --timeout 1200 --timing-task-kind cursor-sketch-arch --prompt "<ARCH_PROMPT>"
```

Use `run_in_background: true` and `timeout: 1260000` on the Bash tool call.

**Cursor — Architecture/Standards fallback** (if `cursor_available` is false): Launch a Claude subagent via the Agent tool with `<ARCH_PROMPT>`.

**Cursor — Edge-cases/Failure-modes** (if `cursor_available`):

```bash
${CLAUDE_PLUGIN_ROOT}/scripts/launch-review.sh --tool cursor --output "$DESIGN_TMPDIR/cursor-sketch-edge-output.txt" --timeout 1200 --timing-task-kind cursor-sketch-edge --prompt "<EDGE_PROMPT>"
```

Use `run_in_background: true` and `timeout: 1260000` on the Bash tool call.

**Cursor — Edge-cases/Failure-modes fallback** (if `cursor_available` is false): Claude subagent with `<EDGE_PROMPT>`.

**Codex — Innovation/Exploration** (if `codex_available`):

```bash
${CLAUDE_PLUGIN_ROOT}/scripts/launch-review.sh --tool codex --output "$DESIGN_TMPDIR/codex-sketch-innovation-output.txt" --timeout 1200 --timing-task-kind codex-sketch-innovation --prompt "<INNOVATION_PROMPT>"
```

Use `run_in_background: true` and `timeout: 1260000` on the Bash tool call.

**Codex — Innovation/Exploration fallback** (if `codex_available` is false): Claude subagent with `<INNOVATION_PROMPT>`.

**Codex — Pragmatism/Safety** (if `codex_available`):

```bash
${CLAUDE_PLUGIN_ROOT}/scripts/launch-review.sh --tool codex --output "$DESIGN_TMPDIR/codex-sketch-pragmatic-output.txt" --timeout 1200 --timing-task-kind codex-sketch-pragmatic --prompt "<PRAGMATIC_PROMPT>"
```

Use `run_in_background: true` and `timeout: 1260000` on the Bash tool call.

**Codex — Pragmatism/Safety fallback** (if `codex_available` is false): Claude subagent with `<PRAGMATIC_PROMPT>`.
