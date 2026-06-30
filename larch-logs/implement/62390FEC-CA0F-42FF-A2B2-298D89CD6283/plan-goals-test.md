## Goal
Implement issue #5842: [IMPLEMENTING] [CLEANUP] Stale "postbump" terminology — per-PR version bump retired.

## Implementation Plan
**Severity**: Low (misnomer, not a malfunction). Predates round IX; surfaced during the #5788 audit.

**Prior art**: #5435 (closed/DONE) fixed the user-facing `🔶 /implement 8: version bump` breadcrumb after per-PR bumping was eliminated. This issue covers the *residual* `postbump` naming that survived that cleanup (the verb, the on-disk sentinel, machine strings, and remaining docs).

**What**: Per-PR version bumping was retired (Phase 1 #3364; the `hook-post-bump-version.sh` resume path was deleted in Phase 5; `/release` now owns versions, per `conflict-resolution.md:27` and `SECURITY.md:383`). The name "postbump" survives as a misnomer even though no bump happens — the `implement-finalize postbump` verb now only runs the Step 8b rebase + force-push gate.

**Scope (three tiers, increasing blast radius)**:
- **Pure prose** (safe to reword): `skills/implement/SKILL.md:91` (also corrected by the merge-conflict bug fix); `skills/implement/scripts/test-step-7a.md` ("pre-bump flush"); `skills/implement/scripts/flush-execution-issues.md` doc comments ("bump/post-bump phase").
- **Machine strings / data contracts** (renaming changes committed values): `source="execution-issues.md pre-bump"`; status tokens `postbump-cwd-not-repo`, `postbump-state-corrupt`.
- **Code symbols + on-disk sentinel** (touches code + tests): the `implement-finalize postbump` CLI verb, the `.postbump-phase` checkpoint file, `run_rebase_rebump` (the "rebump" holdover), and `PostbumpPreflight` / `postbump_preflight` / `_postbump_checkpoint_status` in `python/larch/state/finalize.py`.

**Decide one**:
- Full rename across code + tests + data-contracts (correct but broad), or
- Lighter touch: keep the symbols, add a one-line *"no longer bumps; `/release` owns versions"* clarifier at each prose site.

**Origin**: surfaced during the umbrella #5788 audit; the underlying staleness predates round IX.

## Test plan
(no test plan section in plan-file)
