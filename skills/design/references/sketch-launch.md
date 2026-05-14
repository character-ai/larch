# Sketch Launch Choreography

**Consumer**: `/design` Step 2a.2 — external sketch launches (Cursor/Codex) and per-slot Claude fallbacks.

**Contract**: wrapper-based launch invocations for the external slots selected by `sketch_budget` — `0` launches no agents and writes sentinel artifacts, `4 regular` uses 2 Cursor + 2 Codex on the personality diagonal split (Cursor-Arch + Cursor-Edge + Codex-Innovation + Codex-Pragmatic), and `2 sketch agents` uses 1 Cursor-Generic + 1 Codex-Generic — plus the spawn-order rule, the `run_in_background: true` + `timeout: 1260000` requirements, and the per-slot Claude fallback rules. Token bodies (`<ARCH_PROMPT>` etc.) are resolved from the companion `references/sketch-prompts.md`, not here. Sketch-phase collection (`collect-agent-results.sh` for Step 2a.3) is NOT defined here — that invocation stays single-source in SKILL.md. Launch wrappers (`launch-review.sh --tool cursor`, `launch-review.sh --tool codex`) absorb the `$(...)` command substitution chain internally so SKILL.md Bash blocks are simple invocations.

**When to load**: at Step 2a.2 entry, AFTER `references/sketch-prompts.md` has been loaded (so the placeholder tokens are resolvable). Do NOT load during Steps 0, 1, 2a.3, 2a.4, 2a.5, 2b, 3, 3.5, 3b, 4, or 5.

**Binding convention**: single normative source for the external-slot launch shell blocks (4 regular + 2 quick), the zero-sketch sentinel path, the spawn-order rule, the per-slot `run_in_background: true` / `timeout: 1260000` requirements, and the per-slot Claude fallback notes. Token substitution placeholders (`<ARCH_PROMPT>`, `<EDGE_PROMPT>`, `<INNOVATION_PROMPT>`, `<PRAGMATIC_PROMPT>`, `<GENERIC_PROMPT>`) are resolved from `references/sketch-prompts.md`, which the caller loads first. Sketch-phase collection is NOT defined here — the `collect-agent-results.sh` invocation for Step 2a.3 remains single-source in SKILL.md.

---

**Critical sequencing**: For `sketch_budget=2` or `sketch_budget=4`, you MUST launch all external sketch Bash tool calls (with `run_in_background: true`) AND any Claude subagent fallback sketches in a single message. Issue Cursor slots first (slowest), then Codex slots, then any Claude subagent fallbacks. For `sketch_budget=0`, launch nothing and do not call `collect-agent-results.sh`.

**Launch failure logging**: For every `launch-review.sh` Bash block below, capture launcher stdout/stderr to `$DESIGN_TMPDIR/<slot>-launch.failure.log`. If the Bash tool reports a non-zero exit, append that capture verbatim to `$(dirname "$SESSION_ENV_PATH")/execution-issues.md` when `SESSION_ENV_PATH` is non-empty:

```bash
${CLAUDE_PLUGIN_ROOT}/scripts/append-tool-failure.sh \
  --log "$(dirname "$SESSION_ENV_PATH")/execution-issues.md" \
  --site "design Step 2a.2" \
  --tool "launch-review.sh <tool> <slot>" \
  --exit-code "<exit-code>" \
  --category "External Reviewer Issues" \
  --output-file "$DESIGN_TMPDIR/<slot>-launch.failure.log" \
  --redact || true
```

For Claude Agent fallback sketch failures, write the full Agent returned text to `$DESIGN_TMPDIR/<slot>-agent.failure.log` and append it with `--tool "Agent sketch <slot>" --exit-code 1`. Do not truncate either capture.

**Personality prompts**: the four personality prompts and the generic prompt are shared across external slots (Cursor/Codex) and Claude fallbacks (Agent tool). Token bodies are defined in `references/sketch-prompts.md` (loaded separately via the companion MANDATORY directive at Step 2a.2). Prompt bodies do not carry reasoning-effort prose; external launcher wrappers apply their high-effort mechanisms by default, and Claude fallback Agent-tool invocations use session-default effort.

## Zero-Sketch Mode (`sketch_budget=0`)

Use only when the Step 0 router classified `TRIVIAL_DOC_ONLY` after a codebase scan. This path uses 0 sketch agents: launch no external agents and no Claude fallback agents. Write these sentinel artifacts immediately, then skip Step 2a.5 and proceed directly to Step 2b:

```bash
printf '%s\n' 'NO_SKETCHES_CLASSIFIED_TRIVIAL' > "$DESIGN_TMPDIR/approach-synthesis.txt"
printf '%s\n' 'NO_CONTESTED_DECISIONS' > "$DESIGN_TMPDIR/contested-decisions.md"
: > "$DESIGN_TMPDIR/dialectic-resolutions.md"
```

Do not call `collect-agent-results.sh` on this path.

## Regular Mode (`sketch_budget=4`)

**Spawn order**: all 2 Cursor slots first (slowest), then all 2 Codex slots, then any Claude subagent fallbacks. Issue all Bash and Agent tool calls in a single message.

**Cursor — Architecture/Standards** (if `cursor_available`):

```bash
${CLAUDE_PLUGIN_ROOT}/scripts/launch-review.sh --tool cursor --output "$DESIGN_TMPDIR/cursor-sketch-arch-output.txt" --timeout 1200 --timing-task-kind cursor-sketch-arch --prompt "<ARCH_PROMPT>"
```

Use `run_in_background: true` and `timeout: 1260000` on the Bash tool call.

**Cursor — Architecture/Standards fallback** (if `cursor_available` is false): Launch a Claude subagent via the Agent tool with `<ARCH_PROMPT>` (Claude uses session-default effort).

**Cursor — Edge-cases/Failure-modes** (if `cursor_available`):

```bash
${CLAUDE_PLUGIN_ROOT}/scripts/launch-review.sh --tool cursor --output "$DESIGN_TMPDIR/cursor-sketch-edge-output.txt" --timeout 1200 --timing-task-kind cursor-sketch-edge --prompt "<EDGE_PROMPT>"
```

Use `run_in_background: true` and `timeout: 1260000` on the Bash tool call.

**Cursor — Edge-cases/Failure-modes fallback** (if `cursor_available` is false): Claude subagent with `<EDGE_PROMPT>` (Claude uses session-default effort).

**Codex — Innovation/Exploration** (if `codex_available`):

```bash
${CLAUDE_PLUGIN_ROOT}/scripts/launch-review.sh --tool codex --output "$DESIGN_TMPDIR/codex-sketch-innovation-output.txt" --timeout 1200 --timing-task-kind codex-sketch-innovation --prompt "<INNOVATION_PROMPT>"
```

Use `run_in_background: true` and `timeout: 1260000` on the Bash tool call.

**Codex — Innovation/Exploration fallback** (if `codex_available` is false): Claude subagent with `<INNOVATION_PROMPT>` (Claude uses session-default effort).

**Codex — Pragmatism/Safety** (if `codex_available`):

```bash
${CLAUDE_PLUGIN_ROOT}/scripts/launch-review.sh --tool codex --output "$DESIGN_TMPDIR/codex-sketch-pragmatic-output.txt" --timeout 1200 --timing-task-kind codex-sketch-pragmatic --prompt "<PRAGMATIC_PROMPT>"
```

Use `run_in_background: true` and `timeout: 1260000` on the Bash tool call.

**Codex — Pragmatism/Safety fallback** (if `codex_available` is false): Claude subagent with `<PRAGMATIC_PROMPT>` (Claude uses session-default effort).

## Quick Mode (`sketch_budget=2`)

**Spawn order**: Cursor-Generic first (slowest), then Codex-Generic, then any Claude subagent fallbacks. Issue all Bash and Agent tool calls in a single message.

**Cursor — Generic** (if `cursor_available`):

```bash
${CLAUDE_PLUGIN_ROOT}/scripts/launch-review.sh --tool cursor --output "$DESIGN_TMPDIR/cursor-sketch-generic-output.txt" --timeout 1200 --timing-task-kind cursor-sketch-generic --prompt "<GENERIC_PROMPT>"
```

Use `run_in_background: true` and `timeout: 1260000` on the Bash tool call.

**Cursor — Generic fallback** (if `cursor_available` is false): Claude subagent with `<GENERIC_PROMPT>` (Claude uses session-default effort).

**Codex — Generic** (if `codex_available`):

```bash
${CLAUDE_PLUGIN_ROOT}/scripts/launch-review.sh --tool codex --output "$DESIGN_TMPDIR/codex-sketch-generic-output.txt" --timeout 1200 --timing-task-kind codex-sketch-generic --prompt "<GENERIC_PROMPT>"
```

Use `run_in_background: true` and `timeout: 1260000` on the Bash tool call.

**Codex — Generic fallback** (if `codex_available` is false): Claude subagent with `<GENERIC_PROMPT>` (Claude uses session-default effort).
