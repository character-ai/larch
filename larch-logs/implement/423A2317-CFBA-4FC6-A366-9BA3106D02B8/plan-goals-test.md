## Goal
Implement issue #5610: [IMPLEMENTING] [BUG] Step 3 orchestrator probes sentinel on every empty-output spurious notification, bypassing hook defense-in-depth.

## Implementation Plan
### Files to modify/create

### UPDATED: `skills/shared/design-background-wait.md`

Strengthen both empty-output notification clauses:

- In **Immediate-background wait rule**, change the empty-output sentence to say: end the turn silently, call no tool, run no `wc`, run no sentinel check, and print no prose.
- In **Step 3 task notification boundary**, add the same explicit prohibition beside the existing `set -m` / `#5240` note.
- Keep the non-empty-output recovery probe allowance unchanged.

### UPDATED: `skills/design/SKILL.md`

Add one Anti-pattern entry in the `## Anti-patterns` list:

- State that an empty-output `<task-notification>` during a `/design` immediate-background wait means the orchestrator must emit nothing and call no tool.
- Name the forbidden actions: no Bash, no `wc`, no sentinel check, no "Still running" prose.
- Point readers to `skills/shared/design-background-wait.md` for the allowed non-empty-output recovery path.

### UPDATED: `scripts/hook-bg-poll-guard.sh`

Replace the `jq -cn ... 2>/dev/null || true` deny emitters with static `printf` JSON:

- Update `json_deny_probe()`.
- Update `json_deny()`.
- Keep the top-level `command -v jq` requirement and JSON parsing flow unchanged.
- Keep the `*tasks/*.output*` exclusion in `bash_is_terminal_sentinel_foreground_probe()` unchanged.
- Do not change CLAUDE_PID marker matching.
- Do not restructure the probe-clamp or generic deny architecture.

### UPDATED: `scripts/hook-bg-poll-guard.md`

Update the invariants to reflect the new deny behavior:

- The hook still fails open when `jq` is missing before parsing.
- Once the hook reaches a deny branch, deny JSON is emitted with `printf`, not `jq -cn`.
- Mention that this avoids silently swallowing deny output from a `jq` runtime failure.

### UPDATED: `scripts/test-hook-bg-poll-guard.sh`

Add a targeted regression test for the observed bypass shape:

- Set a live `design-step3-review` marker.
- Use a Bash command that references both `tasks/*.output` and `.completed/step-3-terminal`, for example `wc -c "$DESIGN_TMPDIR/tasks/foo.output"` plus a terminal-sentinel file test in one compound command.
- Assert denial through the generic deny path.
- Place it near existing task-output, terminal-sentinel, and appended-probe tests.

### UPDATED: `scripts/test-hook-bg-poll-guard.md`

Document the new regression coverage:

- State that compound probes combining `tasks/*.output` and a terminal sentinel deny while a live marker exists.
- Note that this covers the guard fallback path rather than the simple foreground-probe clamp.

## Approach

Implement the smallest change that closes both failures:

1. **Prompt contract fix**: make the Step 3 empty-output rule impossible to reinterpret as "run a small probe first."
2. **Hook deny hardening**: make deny JSON static and independent of `jq -cn` at the final emit point.
3. **Regression test**: pin the exact compound-probe shape so future edits do not re-open the bypass.

Keep the current division of responsibility:

- The orchestrator contract prevents the behavior first.
- The hook remains defense-in-depth.
- The broad `tasks/*.output` exclusion stays because compound probes are not simple foreground sentinel probes.
- The generic deny path owns compound command denial.

Architectural guidance applied:

- Prefer fail-closed behavior for denial once the hook has enough valid input.
- Prefer mechanical enforcement through the existing shell harness.
- Avoid adding new abstractions or moving hook logic to Python in this narrow fix.

## Edge cases

- **Empty output with newline only**: prose must treat it the same as 0-byte output.
- **Non-empty premature notification**: keep the existing one foreground terminal-sentinel probe allowance.
- **Simple terminal-sentinel probe**: keep the current clamp behavior and threshold tests.
- **Compound task-output plus sentinel probe**: deny through the generic path even though it is excluded from the simple probe classifier.
- **Missing `jq` before hook parsing**: keep existing fail-open behavior.
- **Deny branch after valid parsing**: emit valid deny JSON without relying on `jq`.

## Failure modes

1. **Invalid JSON from `printf`**
   - Warning signal: `assert_deny` fails because `jq -e` cannot parse hook output.
   - Mitigation: use a single static JSON string with double-quoted keys and values.

2. **Regression test accidentally matches the simple probe clamp**
   - Warning signal: test passes only after repeated invocations or depends on clamp counters.
   - Mitigation: include both `tasks/*.output` and the sentinel in the same compound command so it routes through the generic deny path.

3. **Prompt prose weakens the sanctioned non-empty recovery path**
   - Warning signal: docs imply all probes are forbidden.
   - Mitigation: state the no-tool rule only for empty-output notifications and preserve the non-empty-output probe wording.

## Testing strategy

Run focused checks:

- `bash scripts/test-hook-bg-poll-guard.sh`
- `shellcheck scripts/hook-bg-poll-guard.sh scripts/test-hook-bg-poll-guard.sh`
- `make test-hook-bg-poll-guard`

Also inspect the changed markdown for the exact empty-output contract:

- no Bash call
- no `wc`
- no sentinel check
- no prose output

diff_added: 35
diff_deleted: 4
mechanical_churn: false
diff_lines: 39

## Test plan
(no test plan section in plan-file)
