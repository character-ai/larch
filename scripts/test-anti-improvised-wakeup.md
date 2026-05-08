# scripts/test-anti-improvised-wakeup.sh — contract

`scripts/test-anti-improvised-wakeup.sh` is a freestanding regression harness that pins the project-wide guard against improvised `ScheduleWakeup` calls outside skill-script direction. It asserts the shared project token in `AGENTS.md`, `skills/fix-issue/SKILL.md`, and `skills/research/SKILL.md`, and also asserts the stricter legacy `/implement` NEVER #9 token in `skills/implement/SKILL.md`.

Primary callers are the `test-anti-improvised-wakeup` Makefile target and `make lint` via `test-harnesses-1`. The harness is intentionally literal-only: it uses `grep -Fq` against repository files and does not execute or parse skill content.

When changing the rule's wording in any anchor file, update the literals in `scripts/test-anti-improvised-wakeup.sh` in the same PR. Keep this sibling contract in sync with the Makefile target name, anchor list, and edit-in-sync rule.
