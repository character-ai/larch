## Goal
Implement issue #4268: [IMPLEMENTING] [BUG] (URGENT) /implement and /design orchestrators use Monitor for one-shot completion, creating one turn per log line.

## Implementation Plan
## Plan

## Approach

Prose-only changes to documentation and structural test files. Add explicit Monitor prohibition rules where each orchestrator already has an anti-polling section. Clarify that a single re-launched immediate-background completion waiter is a narrow recovery exception after a proven premature empty `<task-notification>`, not a general polling-loop allowance. Extend the existing structural test with literals that pin both parts of the contract:

- **Monitor ban** for `/implement` and `/design`.
- **Premature-notification recovery** wording for `AGENTS.md`, `/implement`, and `/design`.

No changes to runtime scripts, shared orchestrator rules, or NEVER numbering.

## Files to modify/create

### UPDATED: `AGENTS.md`

Extend the existing Conventions bullet that starts "Don't spawn a Monitor or a Bash...". Insert this text before the trailing "See `skills/implement/SKILL.md` NEVER #9." reference:

> When a `<task-notification>` fires prematurely with empty output while the underlying process is still running, the only sanctioned exception to the Bash polling-loop ban is one re-launched immediate-background completion waiter: exactly one `Bash run_in_background` task with `until <condition>; do sleep N; done`. Do NOT fall back to Monitor.

No other changes to this bullet or neighboring lines.

### UPDATED: `skills/implement/SKILL.md`

Extend NEVER #8 in place. After the existing sentence ending with `skills/shared/orchestrator-never.md`., append:

> **NEVER use the `Monitor` tool anywhere within the `/implement` orchestrator.** Monitor remains banned for one-shot completion tracking. When a `<task-notification>` fires prematurely with empty stdout and the underlying process is still running, the only sanctioned exception to the Bash polling-loop ban is one re-launched immediate-background completion waiter: exactly one `Bash run_in_background` task with `until <completion-condition>; do sleep 60; done`. Do NOT fall back to Monitor. Do NOT spawn multiple Monitor calls watching log files or PID exits.

These anchor phrases are pinned by new test assertions:

```text
NEVER use the `Monitor` tool anywhere within the `/implement` orchestrator
only sanctioned exception to the Bash polling-loop ban is one re-launched immediate-background completion waiter
Do NOT fall back to Monitor
```

### UPDATED: `skills/design/SKILL.md`

Add Anti-pattern #4 after item 3 and before `<!-- step:0`:

```markdown
4. **NEVER use the `Monitor` tool anywhere within the `/design` orchestrator.** **Why:** Monitor fires one turn per log line; it is for event streams only. Using it to wait for a background task to complete burns tokens on spurious turns. **How to apply:** use `Bash run_in_background` with `run_in_background: true` and wait for `<task-notification>` for one-shot completion on all Step 3 and Step 5c fences. When a `<task-notification>` fires prematurely with empty output and the underlying process is still running, the only sanctioned exception to the Bash polling-loop ban is one re-launched immediate-background completion waiter: exactly one `Bash run_in_background` task with `until <completion-condition>; do sleep N; done`. Do NOT fall back to Monitor.
```

These anchor phrases are pinned by new test assertions:

```text
NEVER use the `Monitor` tool anywhere within the `/design` orchestrator
only sanctioned exception to the Bash polling-loop ban is one re-launched immediate-background completion waiter
Do NOT fall back to Monitor
```

### UPDATED: `scripts/test-implement-anti-polling-rule.sh`

Update the header comment to mention issue #4268 and the new Monitor-ban and recovery-contract surfaces. Add 7 new `check()` calls (3 for AGENTS.md/implement literal surfaces, 4 for design) after the existing assertions and before the final `echo` block:

```bash
check "$AGENTS_MD" \
    "AGENTS.md covers premature-notification recovery with narrow single-waiter guidance" \
    'only sanctioned exception to the Bash polling-loop ban is one re-launched immediate-background completion waiter'

check "$IMPL_MD" \
    "SKILL.md NEVER list explicitly bans Monitor tool in /implement orchestrator" \
    'NEVER use the `Monitor` tool anywhere within the `/implement` orchestrator'

check "$IMPL_MD" \
    "SKILL.md NEVER list pins /implement premature-notification recovery as narrow single-waiter guidance" \
    'only sanctioned exception to the Bash polling-loop ban is one re-launched immediate-background completion waiter'

check "$IMPL_MD" \
    "SKILL.md NEVER list tells /implement not to fall back to Monitor" \
    'Do NOT fall back to Monitor'

check "$DESIGN_MD" \
    "/design Anti-patterns explicitly bans Monitor tool" \
    'NEVER use the `Monitor` tool anywhere within the `/design` orchestrator'

check "$DESIGN_MD" \
    "/design Anti-patterns pins premature-notification recovery as narrow single-waiter guidance" \
    'only sanctioned exception to the Bash polling-loop ban is one re-launched immediate-background completion waiter'

check "$DESIGN_MD" \
    "/design Anti-patterns tells orchestrator not to fall back to Monitor" \
    'Do NOT fall back to Monitor'
```

### UPDATED: `scripts/test-implement-anti-polling-rule.md`

Update the Purpose section to cite issue #4268 and the new surfaces. Add 7 new invariants covering the Monitor-ban and recovery-contract literals in all three prose surfaces.

## Edge cases

- The recovery waiter is a **narrow exception** after a proven premature empty notification — it does not permit general Bash polling loops.
- The test checks literal presence, not absence of Monitor strings. The prohibition text itself contains "Monitor".
- `skills/shared/orchestrator-never.md` stays out of scope per approved non-goals (see OOS #4280).
- NEVER numbering stays unchanged. NEVER #8 stays #8.
- The stale "NEVER #9" reference in `AGENTS.md` is not touched.

## Failure modes

1. **Conflicting prose:** Use the exact "only sanctioned exception" phrasing in all three prose surfaces.
2. **Recovery contract drops:** Add separate literals for the narrow single-waiter wording and "Do NOT fall back to Monitor" in both skill files.
3. **Test literal mismatch:** Copy anchor strings directly.
4. **Markdownlint MD038:** Keep new backtick code spans compact (no inner whitespace).

## Testing strategy

- `bash scripts/test-implement-anti-polling-rule.sh` — must pass with 7 additional `PASS` lines.
- `make test-implement-anti-polling-rule` — Makefile target.
- `bash scripts/relevant-checks.sh` — repo-wide lint.

## Acceptance

The plan is accepted by the operator after a 3-round plan review panel (Cursor-Arch, Cursor-Innovation, Codex-generic) with zero accepted findings.

OOS filed: #4280 ([OOS] Add premature-notification recovery carve-out to orchestrator-never.md), blocked by #4268.

diff_lines: 46

## Test plan
(no test plan section in plan-file)
