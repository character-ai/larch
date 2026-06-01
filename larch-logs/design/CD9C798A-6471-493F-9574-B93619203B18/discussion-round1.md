## Decision 1: Reconcile code vs docs (FINDING_6)
- **Question**: `pre_coder_snapshot_dir()` is single-branch and never relocates, but SECURITY.md:64 and review-and-fix.md:56 document a `$PWD`-aware `${TMPDIR}/larch-pre-coder-snapshots/<hash>/` relocation. Implement the relocation, fix the docs, or both?
- **Resolution**: Implement the relocation so code matches the documented contract. The helper gains a second branch: when `round_dir` resolves under `$PWD`, relocate to `${TMPDIR:-/tmp}/larch-pre-coder-snapshots/<hash>/$(basename "$round_dir")`; otherwise keep the existing `$(dirname "$round_dir")/.pre-coder-snapshots/$(basename "$round_dir")` sibling path.
- **Source**: user

## Decision 2: Defense-in-depth chmod 0444 scope (FINDING_9, FINDING_13)
- **Question**: Which carryover artifacts get `chmod 0444`?
- **Resolution**: `chmod 0444` BOTH the relocated pre-coder snapshot files (`pre-coder-head.txt`, `pre-coder-tracked-paths.txt`, `pre-coder-path-diffs/*.patch`) AND `post-coder-head.txt`. Round cleanup uses `rm -rf` (cleanup-tmpdir.sh:70), which still removes read-only files.
- **Source**: user

## Decision 3: Step 2 grant width (FINDING_17)
- **Question**: Narrow `--add-dir "$SESSION_TMPDIR"` in launch-codex-implement.sh, or keep it wide?
- **Resolution**: Keep the grant wide (unchanged). The Step 2 coder writes `manifest.json` / `qa-pending.json` into `$SESSION_TMPDIR` (launch-codex-implement.sh:277-278, 335), so the grant is load-bearing. Add an adjacent comment + `.md` rationale explaining why it stays wide.
- **Source**: user

## Decision 4: Sandbox-confinement residual (FINDING_9 residual)
- **Question**: Add a CI sandbox-confinement check?
- **Resolution**: No CI check (flaky, disproportionate). Document the trust boundary only (relocation + `chmod 0444` are integrity hardening against a delegated fixer, not a confidentiality boundary against same-UID local processes — matches SECURITY.md:64 framing).
- **Source**: interim plan (Decision 4), confirmed by operator "replace via full flow"

## Decision 5: In-repo regression test (FINDING_11)
- **Question**: How to prove the relocation closes the in-`$PWD` gap?
- **Resolution**: Add `test-review-and-fix.sh` coverage that constructs an **in-repo** `round_dir` (under `$PWD`) and asserts the snapshot dir resolves OUTSIDE `$PWD` (not just outside `round_dir`), plus a `0444` perms assertion. Today's tests place `round_dir` outside the repo, so they never exercise the production trust boundary.
- **Source**: acceptance criteria + interim plan (Decision 5)

## Hard constraints (codebase-verified, must not break)
- **Source**: codebase
- Every carryover reader derives its path via `pre_coder_snapshot_dir "$round_dir"` (review-and-fix.sh:361,369,376,417,437,462,472,495,1321; review-implement-step5-loop.sh:340,401). Changing only the helper relocates reads AND writes consistently — minimal, self-consistent surface.
- MAV apply (`run_implement_mav_apply`, review-implement-step5-loop.sh:392-419) writes only `pre-coder-head.txt` (head-only) and must NOT call `snapshot_pre_coder_tracked_state` — doing so would widen #3272 carryover tolerance on MAV rounds.
- `post-coder-head.txt` stays in `round_dir` (written post-dispatch, no tamper window before carryover classification); telemetry reads it from `round_dir` (review-implement-step5-loop.sh:341,343).
- `chmod 0444` must target FILES only, never their containing directories — `rm -rf` needs a writable directory to unlink. Apply `chmod` AFTER the write (a `>` redirect to a pre-existing `0444` file would fail); apply once per round.
- Relocation must keep snapshots outside every Codex `--add-dir` grant: `--add-dir "$round_dir"` and `--add-dir "$PWD"` (launch-codex-implement.sh:335-336; Step 5 grants round_dir + PWD). The `$PWD` branch closes the in-repo gap.

## Non-goals
- **Source**: user + interim plan
- Do NOT narrow `--add-dir "$SESSION_TMPDIR"` (load-bearing for Step 2 manifest writes).
- No CI sandbox-confinement check.
- Do NOT change MAV head-only carryover behavior.
