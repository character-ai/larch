# Bump Verification STATUS Handling — Digest

**Consumer**: `/implement` Step 8 post-check (Block α + Block γ) and Rebase + Re-bump Sub-procedure step 4 post-check (Block β). Common-case reference; load full `bump-verification.md` when `STATUS != ok`, `VERIFIED=false`, or when step12/10/8b caller-family failure handling is needed.

**Contract**: Condensed STATUS-handling guide covering the `STATUS=ok VERIFIED=true` happy path and the reasoning-file sentinel (Block γ) advisory check. Full `bump-verification.md` carries the caller-family failure matrices (step12 hard-bail, step10 graceful-degrade, step8b stall-route) for non-ok and VERIFIED=false branches.

**When to load**: at Step 8 step 3 post-verification (Block α + Block γ) or sub-procedure step 4 post-verification (Block β + Block γ). Load this digest for the common `STATUS=ok VERIFIED=true` path. Load full `bump-verification.md` when `STATUS != ok` or `VERIFIED=false` or when executing Block β. Do NOT load when `HAS_BUMP=false`.

---

## Block α — Step 8 post-check (common path)

Pre-check `STATUS` non-`ok` → skip numeric comparison, log warning (`Step 12 will re-verify under strict semantics`), continue to Step 8a.

Pre-check `STATUS=ok` → parse `VERIFIED`, `COMMITS_AFTER`, `EXPECTED`, `STATUS`:
- `STATUS=git_error` or `STATUS=missing_main_ref`: log warning and continue (non-hard-fail at Step 8).
- `STATUS=ok` AND `VERIFIED=true`: proceed to Step 8a. ← **common path**
- `STATUS=ok` AND `VERIFIED=false`: print `**⚠ /bump-version did not create exactly one commit. Expected $EXPECTED, got $COMMITS_AFTER.**`

For non-ok STATUS branches and Block β caller-family handling, load full `bump-verification.md`.

## Block γ — Reasoning-file sentinel (advisory, runs after Block α or β)

Guard on non-empty `$BUMP_REASONING_FILE`:
- Empty path: print warning, log to Warnings, skip helper.
- Non-empty: invoke `${CLAUDE_PLUGIN_ROOT}/scripts/verify-skill-called.sh --sentinel-file "$BUMP_REASONING_FILE"`. On `VERIFIED=false`: log advisory warning and continue — commit-delta check is the hard gate.
