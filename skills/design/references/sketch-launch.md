# Sketch Launch Choreography

**Consumer**: `/design` Step 2a.2 — external sketch launches (Cursor/Codex) and per-slot Claude fallbacks.

**Contract**: wrapper-based launch invocations for the external slots — the regular-mode launch blocks below (2 Cursor + 2 Codex, one per personality on a diagonal split: Cursor-Arch + Cursor-Edge + Codex-Innovation + Codex-Pragmatic) or the quick-mode launch blocks (1 Cursor-Generic + 1 Codex-Generic) — the spawn-order rule, the `run_in_background: true` + `timeout: 1260000` requirements, and the per-slot Claude fallback rules. Token bodies (`<ARCH_PROMPT>` etc.) are resolved from the companion `references/sketch-prompts.md`, not here. Sketch-phase collection (`collect-agent-results.sh` for Step 2a.3) is NOT defined here — that invocation stays single-source in SKILL.md. Launch wrappers (`launch-cursor-review.sh`, `launch-codex-review.sh`) absorb the `$(...)` command substitution chain internally so SKILL.md Bash blocks are simple invocations.

**When to load**: at Step 2a.2 entry, AFTER `references/sketch-prompts.md` has been loaded (so the placeholder tokens are resolvable). Do NOT load during Steps 0, 1, 2a.3, 2a.4, 2a.5, 2b, 3, 3.5, 3b, 4, or 5.

**Binding convention**: single normative source for the external-slot launch shell blocks (4 regular + 2 quick), the spawn-order rule, the per-slot `run_in_background: true` / `timeout: 1260000` requirements, and the per-slot Claude fallback notes. Token substitution placeholders (`<ARCH_PROMPT>`, `<EDGE_PROMPT>`, `<INNOVATION_PROMPT>`, `<PRAGMATIC_PROMPT>`, `<GENERIC_PROMPT>`) are resolved from `references/sketch-prompts.md`, which the caller loads first. Sketch-phase collection is NOT defined here — the `collect-agent-results.sh` invocation for Step 2a.3 remains single-source in SKILL.md.

---

**Critical sequencing**: You MUST launch all external sketch Bash tool calls (with `run_in_background: true`) AND any Claude subagent fallback sketches in a single message. Issue Cursor slots first (slowest), then Codex slots, then any Claude subagent fallbacks.

**Personality prompts**: the four personality prompts and the generic prompt are shared across external slots (Cursor/Codex) and Claude fallbacks (Agent tool). Token bodies are defined in `references/sketch-prompts.md` (loaded separately via the companion MANDATORY directive at Step 2a.2). For Claude fallback Agent-tool invocations, drop the "Work at your maximum reasoning effort level" trailing suffix — Claude uses session-default effort.

## Regular Mode (`quick_mode=false`)

**Spawn order**: all 2 Cursor slots first (slowest), then all 2 Codex slots, then any Claude subagent fallbacks. Issue all Bash and Agent tool calls in a single message.

**Cursor — Architecture/Standards** (if `cursor_available`):

```bash
${CLAUDE_PLUGIN_ROOT}/scripts/launch-cursor-review.sh --output "$DESIGN_TMPDIR/cursor-sketch-arch-output.txt" --timeout 1200 --timing-task-kind cursor-sketch-arch --prompt "<ARCH_PROMPT>"
```

Use `run_in_background: true` and `timeout: 1260000` on the Bash tool call.

**Cursor — Architecture/Standards fallback** (if `cursor_available` is false): Launch a Claude subagent via the Agent tool with `<ARCH_PROMPT>` (drop the "Work at your maximum reasoning effort level" suffix — Claude uses session-default effort).

**Cursor — Edge-cases/Failure-modes** (if `cursor_available`):

```bash
${CLAUDE_PLUGIN_ROOT}/scripts/launch-cursor-review.sh --output "$DESIGN_TMPDIR/cursor-sketch-edge-output.txt" --timeout 1200 --timing-task-kind cursor-sketch-edge --prompt "<EDGE_PROMPT>"
```

Use `run_in_background: true` and `timeout: 1260000` on the Bash tool call.

**Cursor — Edge-cases/Failure-modes fallback** (if `cursor_available` is false): Claude subagent with `<EDGE_PROMPT>` (effort suffix dropped).

**Codex — Innovation/Exploration** (if `codex_available`):

```bash
${CLAUDE_PLUGIN_ROOT}/scripts/launch-codex-review.sh --output "$DESIGN_TMPDIR/codex-sketch-innovation-output.txt" --timeout 1200 --timing-task-kind codex-sketch-innovation --prompt "<INNOVATION_PROMPT>"
```

Use `run_in_background: true` and `timeout: 1260000` on the Bash tool call.

**Codex — Innovation/Exploration fallback** (if `codex_available` is false): Claude subagent with `<INNOVATION_PROMPT>` (effort suffix dropped).

**Codex — Pragmatism/Safety** (if `codex_available`):

```bash
${CLAUDE_PLUGIN_ROOT}/scripts/launch-codex-review.sh --output "$DESIGN_TMPDIR/codex-sketch-pragmatic-output.txt" --timeout 1200 --timing-task-kind codex-sketch-pragmatic --prompt "<PRAGMATIC_PROMPT>"
```

Use `run_in_background: true` and `timeout: 1260000` on the Bash tool call.

**Codex — Pragmatism/Safety fallback** (if `codex_available` is false): Claude subagent with `<PRAGMATIC_PROMPT>` (effort suffix dropped).

## Quick Mode (`quick_mode=true`)

**Spawn order**: Cursor-Generic first (slowest), then Codex-Generic, then any Claude subagent fallbacks. Issue all Bash and Agent tool calls in a single message.

**Cursor — Generic** (if `cursor_available`):

```bash
${CLAUDE_PLUGIN_ROOT}/scripts/launch-cursor-review.sh --output "$DESIGN_TMPDIR/cursor-sketch-generic-output.txt" --timeout 1200 --timing-task-kind cursor-sketch-generic --prompt "<GENERIC_PROMPT>"
```

Use `run_in_background: true` and `timeout: 1260000` on the Bash tool call.

**Cursor — Generic fallback** (if `cursor_available` is false): Claude subagent with `<GENERIC_PROMPT>` (effort suffix dropped).

**Codex — Generic** (if `codex_available`):

```bash
${CLAUDE_PLUGIN_ROOT}/scripts/launch-codex-review.sh --output "$DESIGN_TMPDIR/codex-sketch-generic-output.txt" --timeout 1200 --timing-task-kind codex-sketch-generic --prompt "<GENERIC_PROMPT>"
```

Use `run_in_background: true` and `timeout: 1260000` on the Bash tool call.

**Codex — Generic fallback** (if `codex_available` is false): Claude subagent with `<GENERIC_PROMPT>` (effort suffix dropped).
