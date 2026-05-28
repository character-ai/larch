# file-design-oos.sh

Stages accepted design-phase OOS (`$DESIGN_TMPDIR/oos-accepted-design.md`) for `/larch:issue` batch filing and annotates per-block `- **Filed URL**:` lines plus the `$DESIGN_TMPDIR/oos-issues-created.md` sentinel.

Validates `$DESIGN_TMPDIR` via `larch_design_tmpdir_validate` after the required-arg check and before dispatching to `cmd_prepare` / `cmd_annotate`.

## Invocation

```text
file-design-oos.sh prepare --design-tmpdir DIR [--issue-number N] [--clear-cross-session-cache]
file-design-oos.sh annotate --design-tmpdir DIR --issue-stdout-file FILE [--issue-number N]
```

- `prepare` — Idempotent guard on `oos-issues-created.md` (non-empty sentinel → `FILE_DESIGN_OOS_STATUS=skip-sentinel`). **Precedence:** if `$DESIGN_TMPDIR/oos-issues-created.md` exists and is non-empty, `prepare` short-circuits immediately and the cross-session cache is not read. Otherwise, when `$HOME/.cache/larch/design-oos-filed/<ISSUE_NUMBER>.md` exists, is non-empty, and `ISSUE_NUMBER` is known (from the environment after sourcing the design session prelude, or from `--issue-number`), **cross-session recovery** copies that cache file into `$DESIGN_TMPDIR/oos-issues-created.md`, updates `oos-accepted-design.md` from the cached filing metadata without `/larch:issue`, then emits `skip-sentinel`. **`--clear-cross-session-cache`** (prepare only): at Phase 1 entry, before recovery, deletes `$HOME/.cache/larch/design-oos-filed/<ISSUE_NUMBER>.md` so a normal cap → deps → `/larch:issue` pipeline can re-file. Otherwise extracts `### OOS_*` blocks lacking `Filed URL`, runs `oos-issue-cap.sh` + `oos-file-conflict-deps.sh` (graceful-degrade on deps failure), emits stdout KV lines for the orchestrator.
- `annotate` — Parses `/issue` stdout (`ISSUE_<i>_URL`, `ISSUE_<i>_DUPLICATE_OF_URL`, `ISSUES_FAILED`), updates `oos-accepted-design.md` via atomic temp + `mv`, writes `oos-issues-created.md` with machine-readable `OOS_FILE_MAP\t<oosnum>\t<url>` lines (cross-session recovery pairing) plus sorted unique GitHub issue URL lines for loose disposition counting. After a successful annotate when `ISSUES_FAILED=0`, best-effort copies that sentinel to `$HOME/.cache/larch/design-oos-filed/<ISSUE_NUMBER>.md` via `mkdir -p` on the parent directory, `mktemp` in the same directory, and `mv` to the final name; failures append under **Warnings** in `$DESIGN_TMPDIR/execution-issues.md` via `append-tool-failure.sh` and do not fail the annotate step. Exits **1** when `ISSUES_FAILED>0` (partial failure); **0** on full success.

## Primary caller

`/design` Step 5b in `skills/design/SKILL.md` (prompt-side `/larch:issue` between `prepare` and `annotate`).

## Makefile / harness

- `make test-file-design-oos` → `skills/design/scripts/test-file-design-oos.sh` (sibling `test-file-design-oos.md`).

## Edit-in-sync

Update together with `skills/design/SKILL.md` Step 5b, `skills/implement/scripts/oos-issue-cap.sh` / `oos-file-conflict-deps.sh` flag contracts, and `skills/issue/SKILL.md` stdout KV grammar.
