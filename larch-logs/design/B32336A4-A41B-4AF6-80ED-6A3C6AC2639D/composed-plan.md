## Plan

This is a SIMPLE-tier design. The smallest change is to add a `BOTH_DOWN` output KV to the pure detector (`degraded-tools-gate.sh`) and update the callers to branch on it.

### Files to modify/create

### UPDATED: `scripts/degraded-tools-gate.sh`

After the `DEGRADED` computation block (lines 99–102), compute `BOTH_DOWN`:

```bash
BOTH_DOWN=false
if [ "$CODEX_STATE" != "ok" ] && [ "$CURSOR_STATE" != "ok" ]; then
    BOTH_DOWN=true
fi
```

Emit `BOTH_DOWN` immediately after `CURSOR_STATE` (output order: `DEGRADED`, `CODEX_STATE`, `CURSOR_STATE`, `BOTH_DOWN`):

```bash
emit_kv BOTH_DOWN "$BOTH_DOWN"
```

Change the trailing question line in the explanation block to be conditional on `BOTH_DOWN`. In the current `if [[ "$SKILL_LABEL" == "design" ]]` branch, replace the final `emit "Continue in this degraded mode, or abort and retry once the tool is healthy?"` with:

```bash
if [[ "$BOTH_DOWN" == "true" ]]; then
    emit "Continue in this degraded mode, or abort and retry once the tool is healthy?"
else
    emit "⚠ Warning: proceeding automatically (one tool available). Retry once the unavailable tool is healthy."
fi
```

Apply the same `BOTH_DOWN`-conditioned final line to the `else` branch of the skill label check.

### UPDATED: `scripts/degraded-tools-gate.md`

In the `## Output (stdout KV)` section, add `BOTH_DOWN` to the emitted-fields list:
- `BOTH_DOWN=true|false` — `true` iff **both** `CODEX_STATE != ok` AND `CURSOR_STATE != ok`; `false` when exactly one tool is down or both are ok.

### UPDATED: `scripts/test-degraded-tools-gate.sh`

For existing Cases 2, 3 (single-tool-down): add `assert_contains "$out" "BOTH_DOWN=false"` assertion.

For existing Case 4 (both-probe-failed): add `assert_contains "$out" "BOTH_DOWN=true"` assertion.

Add two new Cases (13, 14) that verify the explanation-block last-line text differs:
- Case 13: single tool down → explanation must contain "proceeding automatically" and must NOT contain "Continue in this degraded mode".
- Case 14: both tools down → explanation must contain "Continue in this degraded mode" and must NOT contain "proceeding automatically".

### UPDATED: `skills/shared/external-reviewers.md`

In §Degraded-tools gate (Step 0), update two places:

1. In the parse step, add `BOTH_DOWN` to the parsed variables list: "Parse `DEGRADED`, `CODEX_STATE`, `CURSOR_STATE`, `BOTH_DOWN`".

2. Replace the `DEGRADED=true` Interactive-run branch with two sub-branches keyed on `BOTH_DOWN`:

- **Interactive run, `BOTH_DOWN=false`** (exactly one tool unavailable) — print the explanation block as a plain notice and proceed without prompting. Write the `.degraded-tools-gate-prompted` sentinel after printing the notice (same sentinel as the ask-path) so re-entry does not re-warn.
- **Interactive run, `BOTH_DOWN=true`** (both tools unavailable) — present the explanation block and fire `AskUserQuestion`. Keep the per-skill Continue label: `/design` and `/implement` use **Continue (reduced panel …)**; `/review` uses **Continue (degraded waterfall)**; `/research` uses **Continue (degraded)**. On Abort, print warning, clean up tmpdir, stop.

**Fail-safe polarity**: auto-proceed only when `BOTH_DOWN` is **exactly** `false`; when `BOTH_DOWN` is empty, unset, or any other value, treat as `BOTH_DOWN=true` and prompt. Callers must use `[[ "$BOTH_DOWN" == "false" ]]` (exact-string check), not `[[ "$BOTH_DOWN" != "true" ]]`, to avoid silent auto-proceed on empty parse.

### UPDATED: `skills/design/SKILL.md` Step 0a gate paragraph

Change the gate prose from a single branch to two. Current: "If `DEGRADED=true` on an **interactive** run, present … fire `AskUserQuestion` with **Continue** / **Abort**; on **Abort**, run `cleanup-tmpdir.sh` and stop."

Replace with: "If `DEGRADED=true` on an **interactive** run: when `BOTH_DOWN` is **exactly** `false` (one tool unavailable), print the explanation block as a notice, write the `.degraded-tools-gate-prompted` sentinel, and proceed; when `BOTH_DOWN` is `true` or empty/unset (both tools unavailable or parse failed), present the explanation block and fire `AskUserQuestion` with **Continue (reduced panel — unavailable tools dropped, no cross-tool or Claude padding)** / **Abort**; on **Abort**, run `cleanup-tmpdir.sh --dir "$DESIGN_TMPDIR"` and stop."

### UPDATED: `skills/implement/SKILL.md` gate paragraph

Same two-branch prose change. When `BOTH_DOWN` is exactly `false`: print notice + write sentinel + proceed. When `BOTH_DOWN` is `true` or empty/unset: fire `AskUserQuestion` (**Continue (reduced panel …)** / **Abort**); on **Abort**, set `STALL_TRACKING=true` and skip to Step 18 cleanup.

### UPDATED: `skills/research/SKILL.md` gate paragraph

Same two-branch prose change. When `BOTH_DOWN` is exactly `false`: print notice + write sentinel + proceed. When `BOTH_DOWN` is `true` or empty/unset: fire `AskUserQuestion` with **Continue (degraded)** / **Abort**; on **Abort**, run `cleanup-tmpdir.sh --dir "$RESEARCH_TMPDIR"` and stop.

### UPDATED: `skills/review/SKILL.md` gate paragraph

Same two-branch prose change. When `BOTH_DOWN` is exactly `false`: print notice + write sentinel + proceed. When `BOTH_DOWN` is `true` or empty/unset: fire `AskUserQuestion` with **Continue (degraded waterfall)** / **Abort**; on **Abort**, run `cleanup-tmpdir.sh --dir "$REVIEW_TMPDIR"` and stop.

### Approach

Introduce a `BOTH_DOWN` sentinel in the pure detector so callers share one conditional. The explanation-block last line is adapted by the detector (`BOTH_DOWN=true` → question text; `BOTH_DOWN=false` → auto-proceed notice). Callers check `BOTH_DOWN == "false"` (exact string) so empty/unset falls through safely to the prompt path.

### Edge cases

- Empty/unset `BOTH_DOWN` (partial deploy, parse failure) → callers prompt. Safe default.
- `BOTH_DOWN=false` path writes the `.degraded-tools-gate-prompted` sentinel so resume-path re-entry skips the gate block entirely (same as the ask-path).
- `DEGRADED=false` → `BOTH_DOWN=false` trivially; callers only consult `BOTH_DOWN` when `DEGRADED=true`.
- Non-interactive / autonomous runs: unchanged. `BOTH_DOWN` is irrelevant on that path.
- Per-skill Continue labels preserved: each SKILL.md caller keeps its own label in the `BOTH_DOWN=true` branch.

### Failure modes

- Partial deploy (detector updated, callers not): callers ignore `BOTH_DOWN` and ask as before. Safe.
- Misparse (`BOTH_DOWN` empty): callers prompt. Safe via exact-string check.

### Testing strategy

Run: `bash scripts/test-degraded-tools-gate.sh`

Add to existing cases: `BOTH_DOWN=false` assertions in Cases 2, 3; `BOTH_DOWN=true` assertion in Case 4.

Add new Cases 13–14: verify explanation last-line text diverges between single-tool-down (auto-proceed notice) and both-down (Continue-or-abort question).

No new integration test needed: `make lint` already wires `test-degraded-tools-gate` into the pre-commit check.

## Acceptance

The plan is accepted when:
- `test-degraded-tools-gate.sh` passes with new `BOTH_DOWN` assertions and Cases 13–14.
- All four SKILL.md callers use exact-string `BOTH_DOWN == "false"` check.
- `skills/shared/external-reviewers.md` names the per-skill Continue labels in the `BOTH_DOWN=true` sub-branch.
- `.degraded-tools-gate-prompted` sentinel is written on both sub-branches.

diff_lines: 108
