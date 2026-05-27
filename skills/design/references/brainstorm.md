# Brainstorm panel (Step 1d.5)

**Consumer**: `/design` Step **1d.5** — runs after Step **1d** (Round 1 discussion) and before Step **1d.7** (Design Outline — Gate A re-entry only post-plan) when `brainstorm_requested` is true in `$DESIGN_TMPDIR/run-params.json` or set in Step 0 by argv, upgrade paths, or the Step 0b `Brainstorm:` title-prefix auto-enable.

**Contract**: one-shot per invocation via `$DESIGN_TMPDIR/.brainstorm-done`. Produces additive `$DESIGN_TMPDIR/brainstorm.md` (never load-bearing for downstream automation). Downstream readers: **Step 2a** (sketch `<FEATURE_DESCRIPTION>` substitution), **Step 2a.5** (dialectic `{FEATURE_DESCRIPTION}` / synthesis context), **Step 2b** (plan drafting), **Step 3** (plan-review feature context merged by `plan-review-loop.sh` when `brainstorm.md` exists).

**When to load**: only when Step **1d.5** executes — do not preload during Step 0.

---

## MANDATORY — read prompts file first

**MANDATORY — READ ENTIRE FILE**: Read `${CLAUDE_PLUGIN_ROOT}/skills/design/references/brainstorm-prompts.md` completely before assembling slot prompts. It holds `<BRAINSTORM_FRAMING_PROMPT>`, `<BRAINSTORM_SCOPE_PROMPT>`, and `<BRAINSTORM_PRAGMATIC_PROMPT>`.

---

## Style preamble expansion

Before launching each external slot (Cursor framing, Codex scope) and before composing the always-Claude pragmatic slot, read `skills/design/references/readability-style.md` once and substitute every literal `<READABILITY_STYLE>` token in the assembled prompt with the full preamble contents. The pragmatic slot is parent-session, but it receives the same substitution so all three slots see identical style guidance.

---

## Anti-halt override (Step 1d.5 only)

Step 1d.5 **overrides** the generic “never halt after Bash” anxiety **only** for the narrow case: after externals return and you print the **brainstorm synthesis digest** once, you may yield the turn so the operator can speak in the discussion loop below.

**Hard prohibition (non-negotiable)**: Do **NOT** use `ScheduleWakeup`, wall-clock `sleep` polling loops, or Monitor-driven polling to wait for brainstorm externals or operator replies. Follow Bash `<task-notification>` / blocking collector semantics per `BASH_AUTHORING.md`. Do not add summary/handoff prose that masquerades as a parent-skill terminal.

---

## Entry guard

1. Read `$DESIGN_TMPDIR/run-params.json` → boolean `brainstorm_requested` (default **false** when absent).
2. If `brainstorm_requested` is not true: print `⏩ 1d.5: brainstorm — skipped` and **skip** this entire step (go to Step **1d.7**).
3. If `$DESIGN_TMPDIR/.brainstorm-done` exists: print `⏩ 1d.5: brainstorm — skipped (already complete; .brainstorm-done present)` and **skip** this entire step (go to Step **1d.7**).
4. Print `> **🔶 /design 1d.5: brainstorm**`.

---

## Optional Round-1 context

If `$DESIGN_TMPDIR/discussion-round1.md` exists and is non-empty, read it and prepend a short quoted excerpt block into each external slot prompt assembly (bounded length; paraphrase if huge). If absent, proceed without Round-1 text.

---

## Three-slot ideation matrix

| Slot | Tool order | Output file (deterministic) | Timing kind | Prompt body token |
|------|------------|------------------------------|-------------|-------------------|
| Framing | Cursor → Codex → Claude | **`$DESIGN_TMPDIR/cursor-brainstorm-output.txt`** — canonical **framing** staging file; parent **Write**s here no matter which external actually ran (waterfall / Agent fallback). | `cursor-brainstorm` / `codex-brainstorm` | `<BRAINSTORM_FRAMING_PROMPT>` |
| Scope | Codex → Cursor → Claude | **`$DESIGN_TMPDIR/codex-brainstorm-output.txt`** — canonical **scope** staging file; parent **Write**s here no matter which external actually ran. | `codex-brainstorm` / `cursor-brainstorm` | `<BRAINSTORM_SCOPE_PROMPT>` |
| Pragmatic | Always Claude (primary) | in-session compose (no external path) | _(none)_ | `<BRAINSTORM_PRAGMATIC_PROMPT>` |

Spawn slowest-first when two externals are queued in one wave: **Cursor**, then **Codex**, then Claude Agent text generation if used as fallback.

### Agent-returns-text + parent-writes-file (mandatory)

External review **Agent** fallbacks return **text only** to the parent session. The parent MUST **Write** that returned text to the canonical staging file for that ideation slot (`cursor-brainstorm-output.txt` for framing, `codex-brainstorm-output.txt` for scope) **before** synthesis — never instruct a subagent to write these files directly.

---

## External launches (representative)

Use `run_in_background: true` + `timeout: 1260000` on Bash tool calls for externals (same family as sketch launches). Capture failures under `$DESIGN_TMPDIR/*-brainstorm-launch.failure.log` and append via `append-tool-failure.sh` like Step 2a.

**Cursor framing** (when `cursor_available`):

```bash
${CLAUDE_PLUGIN_ROOT}/scripts/launch-review.sh --tool cursor --output "$DESIGN_TMPDIR/cursor-brainstorm-output.txt" --timeout 1200 --timing-task-kind cursor-brainstorm --prompt "<CURSOR_BRAINSTORM_ASSEMBLED_PROMPT>"
```

**Codex scope** (when `codex_available`):

```bash
${CLAUDE_PLUGIN_ROOT}/scripts/launch-review.sh --tool codex --output "$DESIGN_TMPDIR/codex-brainstorm-output.txt" --timeout 1200 --timing-task-kind codex-brainstorm --prompt "<CODEX_BRAINSTORM_ASSEMBLED_PROMPT>"
```

**Always-Claude pragmatic**: run in the parent session (Agent or inline) using `<BRAINSTORM_PRAGMATIC_PROMPT>` embedded in `<CLAUDE_BRAINSTORM_ASSEMBLED_PROMPT>`; merge result into synthesis input (no `collect-agent-results.sh` row required for a purely in-session path).

---

## Collection (`collect-agent-results.sh`) — externals only

**Do not copy-paste a fence verbatim.** The argv below is illustrative only: list **only** the canonical staging paths (`cursor-brainstorm-output.txt` / `codex-brainstorm-output.txt`) for slots you **actually launched as externals** this wave (parent-only / Agent-text fallbacks are **not** launches). Match Step 2a.3-style dynamic argv — one path when a single external ran, two when both ran. Set `run_in_background: true` and `timeout: 1260000` on the `collect-agent-results.sh` Bash tool call, and pair with a foreground `breadcrumb-monitor.sh` invocation in the **same Bash message** so completion is coupled to a streaming surface (see BASH_AUTHORING.md §4 and `${CLAUDE_PLUGIN_ROOT}/scripts/breadcrumb-monitor.md`).

**Example — one external** (e.g. Cursor framing ran; Codex scope was parent-written in-session):

**⚠ Background required — must be paired with breadcrumb-monitor.sh.**

```bash
[ -f ~/.cache/larch/sessions/current-design-env-$PPID.sh ] && source ~/.cache/larch/sessions/current-design-env-$PPID.sh

mkdir -p "$DESIGN_TMPDIR/breadcrumbs"
_launch_id="collect-agent-results.$$"
export LARCH_BREADCRUMB_STREAM="$DESIGN_TMPDIR/breadcrumbs/collect-agent-results.${_launch_id}.ndjson"
: > "$LARCH_BREADCRUMB_STREAM"
export LARCH_DONE_SENTINEL="$(mktemp "$DESIGN_TMPDIR/breadcrumbs/collect-agent-results.${_launch_id}.done.XXXXXX")"
export LARCH_STATUS_FILE="$(mktemp "$DESIGN_TMPDIR/breadcrumbs/collect-agent-results.${_launch_id}.status.XXXXXX")"
export LARCH_QUIET_LOG_FILE="$(mktemp "$DESIGN_TMPDIR/breadcrumbs/collect-agent-results.${_launch_id}.quiet.XXXXXX")"
export LARCH_BREADCRUMBS_SURFACED_FILE="$(mktemp "$DESIGN_TMPDIR/breadcrumbs/collect-agent-results.${_launch_id}.surfaced.XXXXXX")"
export LARCH_PAIRED_PID_FILE="$(mktemp "$DESIGN_TMPDIR/breadcrumbs/collect-agent-results.${_launch_id}.pid.XXXXXX")"
touch "$LARCH_DONE_SENTINEL" "$LARCH_BREADCRUMBS_SURFACED_FILE"
# Tool JSON: run_in_background: true
# Background pair required: see BASH_AUTHORING.md §4
${CLAUDE_PLUGIN_ROOT}/scripts/collect-agent-results.sh --timeout 1260 \
  "$DESIGN_TMPDIR/cursor-brainstorm-output.txt" &
COLLECTOR_PID=$!

monitor_rc=0
"${CLAUDE_PLUGIN_ROOT}/scripts/breadcrumb-monitor.sh" \
  --stream "$LARCH_BREADCRUMB_STREAM" \
  --done-sentinel "$LARCH_DONE_SENTINEL" \
  --status-file "$LARCH_STATUS_FILE" \
  --quiet-log "$LARCH_QUIET_LOG_FILE" \
  --surfaced-sentinel "$LARCH_BREADCRUMBS_SURFACED_FILE" \
  --paired-pid-file "$LARCH_PAIRED_PID_FILE" \
  || monitor_rc=$?

if [ "$monitor_rc" -eq 0 ]; then
  writer_rc=0
  wait "$COLLECTOR_PID" || writer_rc=$?
  exit "$writer_rc"
else
  wait "$COLLECTOR_PID" 2>/dev/null || true
  exit "$monitor_rc"
fi
```

**Example — two externals** (both Cursor framing and Codex scope launched as externals):

**⚠ Background required — must be paired with breadcrumb-monitor.sh.**

```bash
[ -f ~/.cache/larch/sessions/current-design-env-$PPID.sh ] && source ~/.cache/larch/sessions/current-design-env-$PPID.sh

mkdir -p "$DESIGN_TMPDIR/breadcrumbs"
_launch_id="collect-agent-results.$$"
export LARCH_BREADCRUMB_STREAM="$DESIGN_TMPDIR/breadcrumbs/collect-agent-results.${_launch_id}.ndjson"
: > "$LARCH_BREADCRUMB_STREAM"
export LARCH_DONE_SENTINEL="$(mktemp "$DESIGN_TMPDIR/breadcrumbs/collect-agent-results.${_launch_id}.done.XXXXXX")"
export LARCH_STATUS_FILE="$(mktemp "$DESIGN_TMPDIR/breadcrumbs/collect-agent-results.${_launch_id}.status.XXXXXX")"
export LARCH_QUIET_LOG_FILE="$(mktemp "$DESIGN_TMPDIR/breadcrumbs/collect-agent-results.${_launch_id}.quiet.XXXXXX")"
export LARCH_BREADCRUMBS_SURFACED_FILE="$(mktemp "$DESIGN_TMPDIR/breadcrumbs/collect-agent-results.${_launch_id}.surfaced.XXXXXX")"
export LARCH_PAIRED_PID_FILE="$(mktemp "$DESIGN_TMPDIR/breadcrumbs/collect-agent-results.${_launch_id}.pid.XXXXXX")"
touch "$LARCH_DONE_SENTINEL" "$LARCH_BREADCRUMBS_SURFACED_FILE"
# Tool JSON: run_in_background: true
# Background pair required: see BASH_AUTHORING.md §4
${CLAUDE_PLUGIN_ROOT}/scripts/collect-agent-results.sh --timeout 1260 \
  "$DESIGN_TMPDIR/cursor-brainstorm-output.txt" \
  "$DESIGN_TMPDIR/codex-brainstorm-output.txt" &
COLLECTOR_PID=$!

monitor_rc=0
"${CLAUDE_PLUGIN_ROOT}/scripts/breadcrumb-monitor.sh" \
  --stream "$LARCH_BREADCRUMB_STREAM" \
  --done-sentinel "$LARCH_DONE_SENTINEL" \
  --status-file "$LARCH_STATUS_FILE" \
  --quiet-log "$LARCH_QUIET_LOG_FILE" \
  --surfaced-sentinel "$LARCH_BREADCRUMBS_SURFACED_FILE" \
  --paired-pid-file "$LARCH_PAIRED_PID_FILE" \
  || monitor_rc=$?

if [ "$monitor_rc" -eq 0 ]; then
  writer_rc=0
  wait "$COLLECTOR_PID" || writer_rc=$?
  exit "$writer_rc"
else
  wait "$COLLECTOR_PID" 2>/dev/null || true
  exit "$monitor_rc"
fi
```

Guard this call exactly like Step 2a.3: **omit paths** for slots that were not launched as externals (tool unavailable with parent-written Agent fallback is **not** an external launch). **Never** invoke `collect-agent-results.sh` with zero paths.

## Post-collection dirty-tree checkpoint

After the collector returns for whichever externals actually ran, consult `${OUTPUT}.dirty-tree` sidecars, then run:

```bash
${CLAUDE_PLUGIN_ROOT}/scripts/check-mid-run-dirty-tree.sh --mode checkpoint
```

If dirty/unknown: write `$DESIGN_TMPDIR/dirty-tree-detected.env` with `STAGE=brainstorm-collection` and `RECOVERY_REQUIRED=true`, prompt once per boundary using `$DESIGN_TMPDIR/.dirty-tree-prompted-brainstorm-collection` as the idempotency sentinel (same semantics as sketch collection).

---

**MANDATORY — READ ENTIRE FILE before composing the synthesis and any free-form discussion-loop response: `skills/design/references/readability-style.md`.**

## Synthesis → `brainstorm.md`

1. Read slot outputs (externals from disk; Claude slot from session result).
2. Deduplicate near-identical bullets; **order** ideas: framing → scope → pragmatic clusters.
3. **Write** `$DESIGN_TMPDIR/brainstorm.md` using this schema:

```markdown
## Brainstorm Synthesis

### <Idea short title>
**Source:** cursor-brainstorm | codex-brainstorm | claude-brainstorm
<1–3 sentences>

### <Next idea>
**Source:** …
…
```

`## Brainstorm Synthesis` is required once; each idea uses `###` heading + literal `**Source:**` line exactly as shown (pipe-separated tool tags for traceability).

---

## Free-form discussion loop (after synthesis)

### Branch order — classify-message-first

1. **Terminal / ready** — If the operator message is **standalone primary-intent** (“done”, “ready for gate”, “let’s move on”) **and** it is **not** negated, conditional, or carrying an embedded refinement (“don’t X yet, but …”), then: write `$DESIGN_TMPDIR/.brainstorm-done`, print a one-line acknowledgment, and **continue to Step 1d.7 in the same turn** without re-printing the full synthesis document.
2. **Refinement** — If they want edits (add idea, merge, reorder): **mutate** `brainstorm.md`, print an `## Updated Brainstorm Digest` with changed bullets only, then **end the turn**.
3. **Ambiguous** — If intent is unclear, `AskUserQuestion` with exactly two clarified options (no secrets in option text).

**Termination vocabulary disambiguation**: Treat “done / ready / proceed” as terminal **only** when it is the **standalone primary intent** of the message. Messages that negate, defer, or bundle refinements (“not yet”, “also change …”, “done but fix …”) → **refinement** path, not terminal.

When the loop ends via terminal path, ensure `.brainstorm-done` exists before entering Step **1d.7**.

---

## Downstream consumer contract (additive)

- **Step 2a**: When substituting `<FEATURE_DESCRIPTION>` into sketch prompts, if `brainstorm.md` exists and is non-empty, **prepend** a concise digest under a `## Brainstorm context` header to the feature text **inside the substitution string** (do not replace the issue body file).
- **Step 2a.5**: `{FEATURE_DESCRIPTION}` / synthesis MAY incorporate the same additive digest when non-empty.
- **Step 2b**: Read `brainstorm.md` when present; fold ideas only when they do not conflict with voted dialectic resolutions.
- **Step 3**: `plan-review-loop.sh` merges non-empty `brainstorm.md` into the feature context file passed to `dispatch-plan-review-panel.sh` — reviewers see plan + merged context.
