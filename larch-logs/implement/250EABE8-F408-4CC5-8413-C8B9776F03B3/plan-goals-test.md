## Goal
Implement issue #5367: [IMPLEMENTING] [OOS] implement resume + review launcher cleanup — 3 items.

## Implementation Plan
## Out-of-Scope Observations (combined)

Combined from #5361, #5356, #5354. All three are implement/review tooling cleanups surfaced by `/implement` review specialists.

### Item 1 — docs `risk=low` contract contradicts launch-review `with_effort=True`

**Source**: #5361 (surfaced by cursor-specialist-edge-cases-output.txt)
**Location**: `docs/configuration-and-permissions.md` (`LARCH_CURSOR_MODEL` section) and `python/agents.py` (`launch-review` Codex path)

The docs state "Codex review analogously omits `--with-effort` when risk is `low`." But the Codex review launch inside `launch-review` calls `resolve_model_args("codex", with_effort=True, ...)` unconditionally; `--risk` only feeds prompt rendering / outer meta and Cursor max-mode, never the Codex effort flag. Docs-only or test-only diffs classified low risk still run Codex at full configured effort, contrary to the documented `--risk low` behavior.

- **Suggested revisions (informational for voters; coder decides)**:
  - Either implement risk-gated `with_effort` in the `launch-review` Codex path (pass `with_effort=False` when coerced risk is `low`), or narrow the documented contract to state Codex effort is not risk-gated.

### Item 2 — `--emergency` removal lacks explicit argv/resume migration

**Source**: #5356 (surfaced by cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt)
**Location**: `skills/implement/SKILL.md` (Flags section), `skills/implement/scripts/step-0-bootstrap.sh` (resume force read)

The `--emergency` flag was replaced by `--force` / `-f`, but `--emergency` is not explicitly rejected, redirected, or treated as a deprecated alias. `/implement --emergency <N>` can hit a generic verbal-description rejection or run without a clear migration error. Resume handling in `step-0-bootstrap.sh` reads only `FORCE_REQUESTED` from `run-flags.sh`, with no fallback for legacy `EMERGENCY_REQUESTED` or `emergency-bypass.log`. An in-flight session started before the rename can lose force mode after a plugin upgrade, affecting external coder selection, `Force: true` metadata, and bypass-log consumption.

- **Suggested revisions (informational for voters; coder decides)**:
  - Add `--emergency` to the removed/rejected argv list with text pointing operators to `--force` / `-f`, or accept it as a deprecated alias mapped to `force_requested` / `--force`.
  - During one release cycle, treat `EMERGENCY_REQUESTED=true` as `FORCE_REQUESTED=true`.
  - Accept both `emergency-bypass.log` and `force-bypass.log` in the force bypass append/consume path.
  - Note: the cross-upgrade in-flight window has likely passed; the durable part is the clear rejection/alias for the old flag.

### Item 3 — branch-1-resume lacks dirty-tree checkpoint

**Source**: #5354 (surfaced by cursor-specialist-edge-cases-output.txt)
**Location**: `python/bootstrap.py` (`branch-1-resume` path calling `_perform_tracking_side_effects`)

Branch-1-resume calls `_perform_tracking_side_effects(st, write_sentinel=False)` without a dirty-tree checkpoint, while branch-2-adopt runs `dirty_tree.checkpoint()` and bails with `dirty-tree` before its side effects. On resume with a dirty working tree, tracking side effects (rename, run-log init) can run before `_phase_plan`'s later dirty bail.

- **Suggested revisions (informational for voters; coder decides)**:
  - Share the dirty-tree probe across branch-1-resume and branch-2-adopt, or document resume dirty-tree expectations.

---
*Combined from out-of-scope observations auto-filed by the larch `/implement` workflow.*

## Test plan
(no test plan section in plan-file)
