# skills/implement/scripts/test-implement-relevant-checks-anti-halt.sh — contract

`skills/implement/scripts/test-implement-relevant-checks-anti-halt.sh` is the offline regression harness for `/implement`'s per-site relevant-checks helper anti-halt reminders in `skills/implement/SKILL.md`. It is hermetic and runs against the checked-in skill prose; it does not invoke the helper, touch git state, or require network access.

The harness scans the three load-bearing launcher-based composite invocation lines currently present in `skills/implement/SKILL.md`. Steps 10 and 12c moved into the Python ship driver, and Step 5 self-review moved into `skills/implement/references/self-review.md`:

- Step 3 first-pass checks/commit/4.r composite through `checks-commit-route --checks-site step3 --commit-site step4 --rebase-checkpoint-4r`.
- Step 5 accepted-fix composite checks/resume handoff.
- Step 6 second-pass composite checks/commit route on the `FILES_CHANGED=true` branch.

For each matched site, the harness requires the canonical blockquote opener `> **Continue after child returns.**` within the five physical lines immediately preceding the invocation line. The same local window must invoke `Checks Failure Entry Macro`, while the macro definition itself retains the redacted-log guidance and pinned-site guidance.

The harness also asserts that exactly three invocation sites are matched, that the shared Step 5 checks block retains its checks-pass success continuation line near `checks-step5-resume`, and that legacy Skill-tool prose for invoking the relevant-checks slash command is absent. This count is deliberately load-bearing: if `skills/implement/SKILL.md` gains another helper invocation, update the skill prose with a local continuation callout and update this harness/contract in the same PR.

It is wired into `make lint` via the `test-implement-relevant-checks-anti-halt` target and one `test-harnesses-N` shard. It is excluded from agent-lint's orphaned-skill-file rule using the same Makefile-only harness pattern as the other `skills/implement/scripts/test-*.sh` harnesses.

Edit-in-sync: any rewording of the canonical opener, restructuring of the three invocation sites, or addition/removal of relevant-checks helper invocations in `skills/implement/SKILL.md` must update this harness and this contract together.
