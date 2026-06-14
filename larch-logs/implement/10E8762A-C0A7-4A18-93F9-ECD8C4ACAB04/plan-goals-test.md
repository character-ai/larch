## Goal
Implement issue #4333: [IMPLEMENTING] Delete 7 orphaned scripts/*.sh migration leftovers (+ companion docs, agent-lint allowlist, migrated-scripts ledger).

## Implementation Plan
## Summary

Delete **7 orphaned top-level bash scripts** in `scripts/` plus their **6 companion `.md`** docs. These are migration leftovers: nothing invokes them (no skill `.md`, no other bash script, no Python). Verified June 2026 by full-repo reference scan (excluding `larch-logs/` and `node_modules/`).

This is a **PATCH**: pure dead-code removal. No runtime behavior changes.

## Background / why these are orphans

Each script's only references are non-invoking: the agnix dead-script allowlist (`agent-lint.toml`), a stale `docs/` mention, or its own companion `.md`. Function-name and load-guard greps confirm zero callers.

| Script | Lines | Nature |
|---|---|---|
| `scripts/lib-dirty-tree-sidecar.sh` | 23 | sourced-only lib; `_write_dirty_tree_sidecar` has no caller (logic moved to `python/cli.py dirty-tree`) |
| `scripts/lib-validate-meta-path.sh` | 28 | sourced-only lib; `validate_meta_scalar_path` has no caller (run-external-agent is now `pytest test_agents.py`) |
| `scripts/consolidate-round-sidecars.sh` | 226 | self-described "run once after Phase 3c" one-shot sweep; already executed |
| `scripts/retro-sweep-design-logs-phase3d.sh` | 132 | operator-run one-time sweep (#3721) |
| `scripts/sweep-run-logs-phase3a.sh` | 65 | one-shot retroactive sweep; "run manually and then decommissioned" |
| `scripts/repro-claude-p-edit-permissions.sh` | 348 | opt-in bug reproducer (closes #587); no automated caller |
| `scripts/_debug-term-trap.sh` | 41 | operator-run debug reproducer; no caller |

**Caution — do NOT delete these** (they are still sourced; leave them alone): `scripts/lib-design-tmpdir.sh`, `scripts/lib-finalize-state-keys.sh`, `skills/implement/scripts/lib-resolve-implement-tmpdir.sh`.

**Note on stale docs:** `docs/python-migration.md` and `docs/linting.md` currently claim `lib-validate-meta-path.sh` is live. That is stale; its bash sourcer was removed when the harness migrated to Python. Step 4 corrects both.

## Step 1 — Delete these 13 files

```
scripts/_debug-term-trap.sh
scripts/consolidate-round-sidecars.sh
scripts/consolidate-round-sidecars.md
scripts/lib-dirty-tree-sidecar.sh
scripts/lib-dirty-tree-sidecar.md
scripts/lib-validate-meta-path.sh
scripts/lib-validate-meta-path.md
scripts/repro-claude-p-edit-permissions.sh
scripts/repro-claude-p-edit-permissions.md
scripts/retro-sweep-design-logs-phase3d.sh
scripts/retro-sweep-design-logs-phase3d.md
scripts/sweep-run-logs-phase3a.sh
scripts/sweep-run-logs-phase3a.md
```

(`_debug-term-trap.sh` has no companion `.md`. That is why this is 13 files, not 14.)

## Step 2 — Remove allowlist entries from `agent-lint.toml`

Delete each of the following verbatim blocks (comment lines **and** the quoted entries). Match by exact text, not line number; line numbers shift as you delete. Do **not** remove any neighboring entry.

Block A:
```
  # scripts/lib-dirty-tree-sidecar.sh is a sourced-only shell library (no
  # shebang, not invokable directly) carrying the retained
  # _write_dirty_tree_sidecar helper for legacy shell-side baselines. Referenced via
  # source directives only.
  "scripts/lib-dirty-tree-sidecar.sh",
```

Block B:
```
  # scripts/consolidate-round-sidecars.sh is the one-shot operator migration
  # script for Phase 3c (issue #3716): converts committed round directories
  # from individual sidecar files to round-meta.json and pools reviewer-dyn-*.md
  # archetypes. It has no Skill or hook caller — operators invoke it once from
  # the terminal after deploying the Phase 3c code changes. agent-lint's G004
  # dead-script graph cannot discover operator-terminal invocations.
  "scripts/consolidate-round-sidecars.sh",
  "scripts/consolidate-round-sidecars.md",
```

Block C:
```
  # scripts/lib-validate-meta-path.sh is a sourced-only shell library (no
  # shebang, not invokable directly). It is referenced from shell consumers via
  # source directives only, which agent-lint does not follow.
  "scripts/lib-validate-meta-path.sh",
```

Block D:
```
  # scripts/sweep-run-logs-phase3a.sh — one-shot retroactive sweep for Phase 3a;
  # run manually and then decommissioned.
  "scripts/sweep-run-logs-phase3a.sh",
  "scripts/sweep-run-logs-phase3a.md",
```

Block E:
```
  # scripts/repro-claude-p-edit-permissions.sh is the opt-in operator
  # reproducer for the `claude -p` Edit-permission stall (closes #587;
  # validates kernel fix #585 plus the settings audit derived from #566).
  # Referenced only from its sibling .md contract — no Makefile target,
  # no SKILL.md reference, no CI wiring (depends on a real authenticated
  # `claude` binary, costs API tokens, timing-sensitive). Same opt-in
  # operator-instrumentation shape as python/cli.py eval research.
  "scripts/repro-claude-p-edit-permissions.sh",
```

Block F (a single standalone line; the lines above and below it are unrelated entries — leave them):
```
  "scripts/lib-validate-meta-path.md",
```

Block G:
```
  # scripts/retro-sweep-design-logs-phase3d.sh is an operator-run one-time
  # sweep script (#3721). It is not invoked from runtime skill prose or hooks;
  # its contract lives in the sibling scripts/retro-sweep-design-logs-phase3d.md.
  "scripts/retro-sweep-design-logs-phase3d.sh",
  "scripts/retro-sweep-design-logs-phase3d.md",
  # scripts/_debug-term-trap.sh is an operator-run debug reproducer for
  # dispatch-with-waterfall TERM cleanup behavior. It is not invoked from
  # runtime skill prose or hooks.
  "scripts/_debug-term-trap.sh",
```

`lib-dirty-tree-sidecar.md` and `repro-claude-p-edit-permissions.md` have **no** `agent-lint.toml` entry; just delete the files (Step 1).

## Step 3 — Add 13 rows to `python/migrated-scripts.tsv`

Append these rows. Each is `<path><TAB>#4333` (one TAB, a real tab character; `#4333` is this issue's number). The data section is not sorted, so appending at the end is fine.

```
scripts/_debug-term-trap.sh	#4333
scripts/consolidate-round-sidecars.sh	#4333
scripts/consolidate-round-sidecars.md	#4333
scripts/lib-dirty-tree-sidecar.sh	#4333
scripts/lib-dirty-tree-sidecar.md	#4333
scripts/lib-validate-meta-path.sh	#4333
scripts/lib-validate-meta-path.md	#4333
scripts/repro-claude-p-edit-permissions.sh	#4333
scripts/repro-claude-p-edit-permissions.md	#4333
scripts/retro-sweep-design-logs-phase3d.sh	#4333
scripts/retro-sweep-design-logs-phase3d.md	#4333
scripts/sweep-run-logs-phase3a.sh	#4333
scripts/sweep-run-logs-phase3a.md	#4333
```

This mirrors the precedent retirement in PR #4327 (issue #4167), where deleting `launch-review.sh` added the same `<path>	#<issue>` rows. Once these rows exist, `make lint-retired-scripts` enforces that **no** tracked file references these paths, so Steps 2 and 4 must remove every reference.

## Step 4 — Fix 3 stale doc references

**4a. `docs/run-logs.md`** — find this sentence (it wraps across source lines):

> The pool grows monotonically; retroactive migration of pre-Phase-3c directories is handled by `scripts/consolidate-round-sidecars.sh`.

Replace with:

> The pool grows monotonically.

**4b. `docs/linting.md`** (the `make test-run-external-agent` table row) — find:

> , invalid inner-suffix rejection, and `scripts/lib-validate-meta-path.sh` sourced-library invariants.

Replace with:

> , and invalid inner-suffix rejection.

**4c. `docs/python-migration.md`** — find:

> Four sourced-only bash libraries are intentionally deferred because surviving bash still sources them: `scripts/lib-design-tmpdir.sh`, `scripts/lib-validate-meta-path.sh`, `skills/implement/scripts/lib-resolve-implement-tmpdir.sh`, and `scripts/lib-finalize-state-keys.sh`

Replace with (drop `lib-validate-meta-path.sh`; change "Four" to "Three"):

> Three sourced-only bash libraries are intentionally deferred because surviving bash still sources them: `scripts/lib-design-tmpdir.sh`, `skills/implement/scripts/lib-resolve-implement-tmpdir.sh`, and `scripts/lib-finalize-state-keys.sh`

## Step 5 — Verify

Run and confirm all pass / empty:

1. `make lint` (must be green; this runs `lint-retired-scripts` and the agnix `agent-lint` pass).
2. For each of the 13 paths, this must print nothing except the manifest line:
   `git grep -nF "scripts/lib-validate-meta-path.sh" -- ':!python/migrated-scripts.tsv'` (repeat per path; expect zero output).
3. `bash scripts/relevant-checks.sh`.

## Acceptance criteria

- [ ] 13 files deleted (Step 1).
- [ ] 11 allowlist entries (7 `.sh` + 4 `.md`) removed from `agent-lint.toml` (Step 2).
- [ ] 13 rows added to `python/migrated-scripts.tsv` (Step 3).
- [ ] 3 docs corrected (Step 4).
- [ ] `make lint` green; no remaining references outside the manifest (Step 5).
- [ ] The three "do NOT delete" libs are untouched.

## Test plan
(no test plan section in plan-file)
