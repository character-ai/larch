---
paths: ["scripts/launch-codex-*.sh", "scripts/launch-cursor-*.sh", "scripts/lib-timing-kinds.sh", "scripts/lib-timing-kinds.md", "skills/design/SKILL.md", "skills/review/SKILL.md", "skills/implement/SKILL.md", "skills/research/SKILL.md", "skills/design/references/*.md", "scripts/test-design-structure.sh", "scripts/test-design-structure.md"]
---

# Timing Task Kind Allow-List

`scripts/lib-timing-kinds.sh` declares the canonical
`TIMING_TASK_KINDS_ALLOWED` Bash array consumed by
`scripts/timing-ledger.sh`. When `--timing-task-kind <kind>` is not in
the list, the ledger warns and still appends the vendor row. Unknown kinds
do not lose data; they pollute the warning stream and weaken the
typo-class drift signal the allow-list provides.

When adding or renaming a literal `--timing-task-kind <kind>` in a
launcher (`scripts/launch-*-{review,implement}.sh`) or skill SKILL.md
launch block, also append or rename it in `TIMING_TASK_KINDS_ALLOWED` in
the same change. `scripts/test-design-structure.sh` Check **16** loops
over the dialectic retry kinds and greps each slug in
`scripts/lib-timing-kinds.sh`, failing CI when a required kind is
missing from the allow-list (literal slugs only; variable-indirected
forms like `--timing-task-kind "$KIND"` slip past the regex). The
sibling `scripts/lib-timing-kinds.md` documents the same pairing.

**prevents**: typo-class drift, warning-stream noise, and
variable-indirected timing-task-kind values evading structural tests
while still being silently mis-attributed in `scripts/timing-report.sh`
aggregation.
