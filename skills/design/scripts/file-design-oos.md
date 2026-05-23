# file-design-oos.sh

Stages accepted design-phase OOS (`$DESIGN_TMPDIR/oos-accepted-design.md`) for `/larch:issue` batch filing and annotates per-block `- **Filed URL**:` lines plus the `$DESIGN_TMPDIR/oos-issues-created.md` sentinel.

## Invocation

```text
file-design-oos.sh prepare --design-tmpdir DIR
file-design-oos.sh annotate --design-tmpdir DIR --issue-stdout-file FILE
```

- `prepare` — Idempotent guard on `oos-issues-created.md` (non-empty sentinel → `FILE_DESIGN_OOS_STATUS=skip-sentinel`). Otherwise extracts `### OOS_*` blocks lacking `Filed URL`, runs `oos-issue-cap.sh` + `oos-file-conflict-deps.sh` (graceful-degrade on deps failure), emits stdout KV lines for the orchestrator.
- `annotate` — Parses `/issue` stdout (`ISSUE_<i>_URL`, `ISSUE_<i>_DUPLICATE_OF_URL`, `ISSUES_FAILED`), updates `oos-accepted-design.md` via atomic temp + `mv`, writes `oos-issues-created.md` (sorted unique issue URLs). Exits **1** when `ISSUES_FAILED>0` (partial failure); **0** on full success.

## Primary caller

`/design` Step 5b in `skills/design/SKILL.md` (prompt-side `/larch:issue` between `prepare` and `annotate`).

## Makefile / harness

- `make test-file-design-oos` → `skills/design/scripts/test-file-design-oos.sh` (sibling `test-file-design-oos.md`).

## Edit-in-sync

Update together with `skills/design/SKILL.md` Step 5b, `skills/implement/scripts/oos-issue-cap.sh` / `oos-file-conflict-deps.sh` flag contracts, and `skills/issue/SKILL.md` stdout KV grammar.
