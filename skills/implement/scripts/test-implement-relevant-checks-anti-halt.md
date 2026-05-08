# skills/implement/scripts/test-implement-relevant-checks-anti-halt.sh — contract

`skills/implement/scripts/test-implement-relevant-checks-anti-halt.sh` is the offline regression harness for `/implement`'s per-site relevant-checks helper anti-halt reminders in `skills/implement/SKILL.md`. It is hermetic and runs against the checked-in skill prose; it does not invoke the helper, touch git state, or require network access.

The harness scans the five load-bearing `run-relevant-checks-captured.sh` invocation-site forms currently present in `/implement`:

- Step 3 first-pass checks.
- Quick-mode Step 5.7 after accepted review fixes.
- Step 6 second-pass checks on the `FILES_CHANGED=true` branch.
- Step 10 real-CI-failure fix loop.
- Step 12c real-CI-failure fix loop.

For each matched site, the harness requires the canonical blockquote opener `> **Continue after child returns.**` within the five physical lines immediately preceding the invocation line. The five-line window is intentional: Step 10 and Step 12c are inline-chain forms inside numbered list items, so the reminder must stay visually local to the chained helper token rather than relying on the top-level anti-halt rule. The same local window must mention `REDACTED_LOG_FILE` and explicitly say not to read raw `LOG_FILE`.

The harness also asserts that exactly five invocation sites are matched and that legacy executable phrases such as Invoke `/relevant-checks` via the Skill tool or `` `/relevant-checks`; commit via`` are absent. This count is deliberately load-bearing: if `skills/implement/SKILL.md` gains another helper invocation, update the skill prose with a local continuation callout and update this harness/contract in the same PR.

It is wired into `make lint` via the `test-implement-relevant-checks-anti-halt` target and one `test-harnesses-N` shard. It is excluded from agent-lint's orphaned-skill-file rule using the same Makefile-only harness pattern as the other `skills/implement/scripts/test-*.sh` harnesses.

Edit-in-sync: any rewording of the canonical opener, restructuring of the five invocation sites, or addition/removal of relevant-checks helper invocations in `skills/implement/SKILL.md` must update this harness and this contract together.
