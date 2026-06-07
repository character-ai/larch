## Goal
Implement issue #3710: [IMPLEMENTING] logs-size-reduction: run-log tree committed under python/larch-logs (log-root resolution bug)\n\n## Defect.

## Implementation Plan
## Defect

A complete `/implement` run-log tree is committed at `python/larch-logs/implement/0CF88C8D-727A-4F0D-A26C-F57DF6A9076C/` — **320 tracked files, ~3.2 MB** — instead of (or in addition to) the canonical repo-root `larch-logs/implement/` location.

- Landed in PR **#3572** ("Fixes #3550", merged 2026-06-05), so the bug is recent and may still be live.
- The stray tree contains artifacts the normal commit path excludes or renames (`codex-impl-transcript-meta.txt.meta` at top level, `session-transcript-refresh.txt`, raw sidecars), which suggests a **raw tmpdir run-tree copy** rather than the batch-table publisher — i.e., a log-root resolved relative to the process CWD (likely `python/`) instead of the repo root.

## Where to look

- `python/run_logs.py` — run-tree copy into the repo (`run_logs.py` "Copy tmpdir run tree into repo larch-logs (larch-log.sh commit parity)" and the `larch-logs/implement/<run-id>` path joins around `_IMPLEMENT_RUN_REL_PARTS`): check what `repo_root` resolves to when the driver's CWD is `python/` (or any subdirectory) at flush time.
- `scripts/larch-log.sh` log-root resolution as the bash-parity reference.
- The run in question (`0CF88C8D…`) also has a canonical `larch-logs/implement/0CF88C8D…/` twin at repo root — diff the two trees to see which flush produced the stray copy.

## Suggested fix

1. Resolve the log root from `git rev-parse --show-toplevel` (or the already-known repo root in `ctx`), never from CWD-relative joins.
2. Add a cheap guard at commit time: refuse (loudly) to stage any `larch-logs/` path whose parent is not the repo root — turning a future recurrence into a visible failure instead of silent pollution.
3. Regression: a harness case running the flush with CWD set to a repo subdirectory.

## Cleanup

Deletion of the stray tree itself is handled by the Phase 2 retroactive cleanup issue (logs-size-reduction series); this issue is the root-cause fix so it cannot recur.

## Test plan
(no test plan section in plan-file)
