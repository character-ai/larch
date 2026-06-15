## Goal
Implement issue #4409: [IMPLEMENTING] [OOS] External-tool launch CWD & trust-config resolution gaps in python/agents.py — 3 items.

## Implementation Plan
Combined from #4370, #4361 by `/combine-issues --oos`. Remaining `Path.cwd()`-under-plugin-root-override gaps in the Codex/Cursor launch and probe paths in `python/agents.py`. The review-Codex path already uses `_resolve_review_codex_workdir`; these sibling call sites do not, so under the `run_legacy_script` CWD override they resolve to the plugin cache instead of the consumer repo.

### Item 1 — Cursor review and Codex implement launch paths use raw Path.cwd()
- **Location**: `python/agents.py` (`_review_launch_cursor` `--workspace`; `launch_codex_implement_main` `-C`)
- **Source**: #4370
- **Severity**: latent / architecture
- **Description**: Two launch paths share the plugin-root CWD override class as the already-fixed review-Codex bug. `_review_launch_cursor` still passes `--workspace str(Path.cwd())` for Cursor review slots; under `run_legacy_script` CWD override this resolves to the plugin cache rather than the consumer repo, yielding wrong-tree Cursor review results. `launch-codex-implement` still passes `Path.cwd()` to `codex exec -C`; under the same override, Codex implement dispatch launches against the plugin root. Both are pre-existing plan non-goals deferred from the original fix. Fix: apply `_resolve_review_codex_workdir` (or a parallel resolver) to these remaining call sites.

### Item 2 — Tier 3 reads DESIGN_TMPDIR / SESSION_TMPDIR but not IMPLEMENT_TMPDIR
- **Location**: `python/agents.py` (Tier-3 workdir resolution)
- **Source**: #4361 (OOS_2, capped per-run rollup)
- **Severity**: latent
- **Description**: Tier 3 reads `DESIGN_TMPDIR` / `SESSION_TMPDIR` but not `IMPLEMENT_TMPDIR`. Scenario: `/implement` Step 5 also launches Codex via `_review_launch_codex`; implement sessions write the session tmpdir under `IMPLEMENT_TMPDIR`, which the Tier-3 resolver does not consult. (Original item text was truncated by the per-run OOS rollup cap; confirm the Tier-3 resolver covers `IMPLEMENT_TMPDIR`.)

### Item 3 — Codex reviewer probe uses str(Path.cwd()) for -C and _trust_config_arg
- **Location**: `python/agents.py:812-816`
- **Source**: #4361 (OOS_3, capped per-run rollup)
- **Severity**: latent
- **Description**: Codex reviewer probe still uses `str(Path.cwd())` for `-C` and `_trust_config_arg`. Scenario: health-check / probe launches from the plugin-cache cwd can hit the same trust-check failure as the fixed review path. Fix: resolve the probe workdir the same way as the review path.

---
*Combined by the larch `/combine-issues --oos` workflow. Sources: #4370, #4361.*

## Test plan
(no test plan section in plan-file)
