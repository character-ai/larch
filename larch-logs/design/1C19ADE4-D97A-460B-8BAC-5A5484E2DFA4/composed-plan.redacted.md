## Plan

Extract the repeated per-step ledger telemetry preamble in `skills/implement/SKILL.md` into a new
`scripts/step-telemetry-mark.sh` helper, and collapse the eligible step-ENTRY sites to one helper call.
Telemetry behavior stays byte-for-byte identical; this is a context-cost win. `#3292` (plugin-root awk
fence → `plugin-root.env`) already landed, so the preamble sweep is unblocked.

### Files to modify/create

- **NEW** `scripts/step-telemetry-mark.sh` — helper `step-telemetry-mark.sh --implement-tmpdir DIR --label "Step N — name"`.
  - `set -uo pipefail`; intentionally **omit `-e`** (documented comment) — pure telemetry, never fatal.
  - Initialize `IMPLEMENT_TMPDIR=""` and `LABEL=""` **before** the arg-parse loop; reference `"${IMPLEMENT_TMPDIR:-}"` so an omitted `--implement-tmpdir` cannot trip `set -u`.
  - Resolve `SCRIPT_DIR` from `${BASH_SOURCE[0]}` and call siblings directly (no `CLAUDE_PLUGIN_ROOT` needed): `read-session-env-key.sh`, `token-ledger.sh`, `timing-ledger.sh`.
  - Read `LARCH_TOKEN_SESSION_ID`, `LARCH_CLAUDE_SOURCE_FILE`, `LARCH_TIMING_LEDGER` from `$IMPLEMENT_TMPDIR/session-env.sh` via `read-session-env-key.sh --file ... --key ... --default ""`.
  - `export IMPLEMENT_TMPDIR LARCH_TOKEN_SESSION_ID LARCH_CLAUDE_SOURCE_FILE LARCH_TIMING_LEDGER` (export `IMPLEMENT_TMPDIR` too so the ledger fallback chain matches the old inline fence).
  - Run `token-ledger.sh mark "$LABEL" || true` then `timing-ledger.sh mark "$LABEL" || true`; end with explicit `exit 0`.
  - **Commit the file executable (mode `0755`)** — SKILL.md call sites run it directly; a `0644` file returns 126 and `|| true` would silently drop the marks.
- **NEW** `scripts/step-telemetry-mark.md` — sibling contract: interface, never-fatal/always-`exit 0` invariant, executable-bit requirement, the three env keys, the `/implement` callers, the out-of-scope sites, Makefile wiring, harness pointer.
- **NEW** `scripts/test-step-telemetry-mark.sh` — offline unit harness (`set -euo pipefail`): assert `[ -x "$HELPER" ]` and invoke `"$HELPER"` **directly by path** (not `bash "$HELPER"`); happy path writes both ledger rows; never-fatal on bad `--implement-tmpdir`, on **omitted** `--implement-tmpdir` (exit 0), and on missing `--label`.
- **NEW** `scripts/test-step-telemetry-mark.md` — harness stub pointing at `scripts/step-telemetry-mark.md`.
- **UPDATED** `skills/implement/SKILL.md` — convert exactly the 4 clean step-ENTRY sites (Step 5, Step 16, Step 17, Step 18-cleanup): replace the trio (3 `read-session-env-key.sh` reads + three-key `export`) + both `mark` lines + the two trailing `# token-mark`/`# timing-mark` comment anchors with one `"${CLAUDE_PLUGIN_ROOT}/scripts/step-telemetry-mark.sh" --implement-tmpdir "$IMPLEMENT_TMPDIR" --label "Step N — name" || true` call. Keep the `IMPLEMENT_TMPDIR="$IMPLEMENT_TMPDIR"` / `export IMPLEMENT_TMPDIR` / `plugin-root.env` source lines and the `|| true`. **Do NOT convert** Step 2 (conditional token-mark in the coder `case`) or the Step 18 closing `Step 18 — done` cap (must stay orchestrator-emitted after the `--since-last-mark --terse` reports). The 7 trio-only rehydrate-for-children sites emit no marks and are out of scope.
- **UPDATED** `scripts/test-implement-timing-rehydration.sh` — add `step_telemetry_mark_count` (count of the helper-call line) and change the two count-coupling assertions to `tmpdir_assign_count == token_read_count + step_telemetry_mark_count` and `tmpdir_export_count == token_read_count + step_telemetry_mark_count`. Invariants A/B/C and `plugin_root_source_count == 41` stay (converted fences keep `plugin-root.env` and no longer call `timing-ledger.sh` directly). Update the header comment + `PASS:` line.
- **UPDATED** `scripts/test-implement-timing-rehydration.md` — document the new helper-aware `tmpdir == token + helper` invariant.
- **UPDATED** `agent-lint.toml` — add `scripts/test-step-telemetry-mark.sh` (`.sh` exclude region) and `scripts/test-step-telemetry-mark.md` (`.md` exclude region) to the dead-script `exclude` list with a Makefile-only comment mirroring `scripts/test-implement-timing-rehydration.sh`/`.md`. Keep the runtime helper + its `.md` **off** exclude (reachable via SKILL.md fences, like `scripts/read-session-env-key.sh`/`.md`).
- **UPDATED** `Makefile` — register `test-step-telemetry-mark` (`.PHONY` list, one `test-harnesses-N` shard, and a target stanza mirroring `test-implement-timing-rehydration`).

### Approach
1. Write the helper (executable, vars initialized before the loop) + its `.md`.
2. Write the unit harness (`[ -x ]` + direct-path invoke + omitted-flag exit-0) + `.md`; register in `Makefile`; add `agent-lint.toml` exclusions.
3. Audit all 8 token-mark / 6 timing-mark sites; convert only the 4 clean adjacent step-ENTRY pairs.
4. Update `test-implement-timing-rehydration.sh` + `.md` for the helper-aware counts.
5. Run `make test-step-telemetry-mark`, `make test-implement-timing-rehydration`, `make test-implement-structure`, `make agent-lint`, `bash scripts/relevant-checks.sh`.

### Edge cases & failure modes
- Omitted/empty `--implement-tmpdir` → pre-init vars avoid `set -u` abort → unreadable session-env → empty keys → marks still run → `exit 0`.
- Helper committed non-executable → 126 at call sites; harness `[ -x ]` + direct-path invoke catches it; `|| true` keeps the live step non-fatal.
- `LARCH_TIMING_LEDGER` empty → `timing-ledger.sh` uses its `IMPLEMENT_TMPDIR` fallback (helper exports it), identical to the old fence.
- Silent telemetry loss → `step_telemetry_mark_count` arithmetic fails if a helper call is dropped; harness fails if the exec bit is lost.

### Testing
- `scripts/test-step-telemetry-mark.sh` (new, Makefile-wired); `scripts/test-implement-timing-rehydration.sh` stays green with helper-aware counts; `test-implement-structure.sh` unaffected (it pins marks in child scripts, not SKILL.md preambles); `make agent-lint` + `bash scripts/relevant-checks.sh` green.

## Acceptance

- `scripts/step-telemetry-mark.sh` exists, is committed executable (`0755`), exits 0 on the happy path and on all never-fatal paths (bad tmpdir, omitted `--implement-tmpdir`, missing label), and emits both ledger marks when keys are present.
- The 4 step-ENTRY sites (Step 5, 16, 17, 18-cleanup) in `skills/implement/SKILL.md` each call `step-telemetry-mark.sh` once; Step 2 and the Step 18 closing `Step 18 — done` cap remain inline and unchanged.
- `scripts/test-step-telemetry-mark.sh` (+ `.md`) added and registered in the `Makefile`; `agent-lint.toml` excludes the new harness `.sh` + `.md`.
- `make test-step-telemetry-mark`, `make test-implement-timing-rehydration`, `make test-implement-structure`, `make agent-lint`, and `bash scripts/relevant-checks.sh` all pass.
- Telemetry behavior is unchanged: token/timing ledger rows for Steps 5/16/17/18-cleanup are still emitted with the same labels.

diff_lines: 290
