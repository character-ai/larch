## Plan

# Implementation Plan — #3247: extract Step 2b post-plan emit driver (`design-postplan-emit`)

Part of umbrella #3133. Fuse the three inline Step 2b post-plan fences into one phase-driver
script and reuse it at the three prompt-side re-emit sites. SIMPLE tier; full review panel.

## Scope (locked in Round 1)

- IN: initial Step 2b (full: EMIT_PLAN + HARD snapshot + validator) plus the three prompt-side
  re-emit sites — Gate A re-entry, Gate B "Shared post-apply pipeline", discussion-round2 — with
  the HARD snapshot suppressed there.
- OUT: loop-internal EMIT_PLAN sites (`plan-review-loop.sh`, `revise-plan-with-waterfall.sh`).
  They keep bespoke `plan_backup`/`LOOP_STATUS` rollback and take no snapshot.
- No behavior change. Preserve the machine-output contract, the control boundary, cooperative
  pause checkpoints (session-env prelude + inter-step `.pause-requested` handling), and exit codes.
- **discussion-round2 validator parity (FINDING_7):** Today `discussion-rounds.md` runs
  `invoke-plan-validator.sh` unconditionally (no `review_budget=quick` guard). Gate B and Gate A
  re-emit prose gate on `review_budget=full`. The driver defaults to the Step 2b / Gate B rule
  (`VALIDATE_STATUS=skipped-quick` when `review_budget=quick`). The discussion-round2 call site
  passes `--force-validate` so quick runs still validate there — preserving current behavior at that
  site only.

## Approach

Build `design-postplan-emit.sh` on `lib-phase-driver.sh`, mirroring the sibling drivers
(`design-publish.sh`, `design-init-runparams.sh`). It runs the post-plan sequence and emits one
combined status via a result-env file plus stdout KV lines. Call sites shrink to one driver call
plus a KV parse; the orchestrator keeps only the gating it cannot delegate (the `defects-found`
AskUserQuestion, the `missing-diff-lines` repair path, and Step 2b.5).

The driver reads `run-params.json` itself for `review_budget` and `workflow_path`, so the
per-site `jq`/`sed` `workflow_path` read and the `review_budget` read are removed from all four
call sites (the "no duplication" win). A single `--snapshot-original` flag gates the HARD
snapshot: the initial Step 2b call passes it; re-emit sites omit it. A single `--force-validate`
flag opts out of the `review_budget=quick` skip; only the discussion-round2 re-emit passes it.

**`set -e` child-call safety (FINDING_1).** The driver uses `set -euo pipefail` globally, but
each wrapped helper (`design-driver.sh`, `snapshot-plan-round.sh`, `invoke-plan-validator.sh`) may
exit non-zero. Without local `set +e` capture, `set -e` aborts before
`.design-postplan-emit-result.env` and stdout KVs are written — breaking harness case #10 and
orchestrator file-first parse. Mirror `design-driver.sh` `process_line` and `design-publish.sh`:

1. Add `_postplan_write_result_and_emit()` — central flush: populate the KV matrix, call
   `phase_driver_write_result_env` on `.design-postplan-emit-result.env`, mirror mandatory keys
   via `emit_kv` (same keys as the matrix). Callable on every exit path.
2. Wrap **each** internal child in `set +e` … `rc=$?` … `set -e` (never rely on bare `$?` after
   `set -e` re-enable without capture):
   - EMIT: `_emit_out=$(printf 'ACTION=EMIT_PLAN\n' | "$PLUGIN_ROOT/skills/design/scripts/design-driver.sh" --design-tmpdir "$DESIGN_TMPDIR" 2>&1); _emit_rc=$?`
   - Snapshot: `_snap_rc` from `snapshot-plan-round.sh write-original …`
   - Validator: `_val_out=$(invoke-plan-validator.sh …); _val_rc=$?`
3. After each step sets failure status (`POSTPLAN_EMIT_STATUS`, step-specific keys), call
   `_postplan_write_result_and_emit` then `exit 1` (or `exit 0` on success / `defects-found` /
   `skipped-quick`). **Never** `exit 1` from a failure branch without flushing first.
4. Parse child stdout only after `set -e` is restored; treat empty/missing parsed keys as
   contract failures only when the step actually ran.

**Orchestrator handoff — file-first + stdout fallback (accepted FINDING_1).** Every orchestrator
fence that invokes `design-postplan-emit.sh` (Step 2b in `SKILL.md`; Gate A optional-trailer guard;
`approval-gates.md` shared post-apply; `discussion-rounds.md` round-2 revision) MUST parse driver
output the same way as Step 0b `design-route.sh` and Step 5c `design-publish.sh`:

1. `set +e` capture → `_postplan_out=…`; `_postplan_rc=$?`; `set -e`.
2. Exit-code gates unchanged (`2` abort; `1` hard failure branches; `0` → `defects-found` or Step 2b.5).
3. Initialize allowlisted shell variables to empty before parse:
   `POSTPLAN_EMIT_STATUS`, `EMIT_PLAN_STATUS`, `DIFF_LINES`, `SNAPSHOT_STATUS`, `VALIDATE_STATUS`,
   `VALIDATE_DEFECT_COUNT`, `VALIDATE_SKIPPED_COUNT`, `VALIDATE_UNSAFE_TOKEN_COUNT`,
   `VALIDATE_LOG_FILE`; track `_postplan_parse_ok=false`.
4. **File-first:** when `$DESIGN_TMPDIR/.design-postplan-emit-result.env` exists and is **not** a
   symlink, read it line-by-line; for each allowlisted key, `printf -v` from the file; set
   `_postplan_parse_ok=true`. On symlink: print refusal warning (same wording family as Step 5c);
   do not source.
5. **Stdout fallback:** loop `_postplan_out` with the same allowlisted `case` keys; for routing keys
   use `[[ -n "${!_key:-}" ]] || printf -v "$_key" '%s' "$_value"` so file-first values win and
   stdout fills only still-unset keys. Replay `WARN=` lines from stdout only when file parse did not
   succeed (mirror Step 5c WARN dedup semantics).
6. When `_postplan_rc` ∈ `{0,1}` and, after merge, `POSTPLAN_EMIT_STATUS` or `VALIDATE_STATUS` remain
   unset, abort `/design` with explicit “result env missing/unreadable and stdout did not populate
   mandatory keys” prose — do not fall through to wrong hard-failure vs `defects-found` routing.

Step 2b SKILL.md fence carries the full inline Bash for steps 1–6; re-emit reference files state
“prelude + driver + **same file-first/stdout parse** as Step 2b” and may cite the Step 2b block by
anchor rather than duplicating every line.

**Pause preservation (no behavior change).** Today Step 2b uses three Bash fences, each with the
canonical two-line orchestrator prelude (`current-design-env-$PPID.sh` source plus
`.pause-requested` → `design-pause-save.sh` exec). Consolidation MUST NOT drop cooperative pause:

1. **Orchestrator fences** — Every Bash fence that invokes `design-postplan-emit.sh` (initial Step
   2b post-`plan.txt` write; Gate A optional-trailer re-emit fence) MUST still prepend the same
   two-line prelude before the driver call. Prose-only re-emit sites (`approval-gates.md`,
   `discussion-rounds.md`) direct the executor to run that prelude + driver inside a `set +e`
   capture fence (same pattern as Step 5c `design-publish.sh`).
2. **Driver-internal checkpoints** — Add `_postplan_pause_checkpoint()` in
   `design-postplan-emit.sh`, called immediately **before** each internal step (EMIT, snapshot,
   validator). When `$DESIGN_TMPDIR/.pause-requested` exists, resolve the issue via
   `_postplan_resolve_issue()` (below) and `exec`
   `"$CLAUDE_PLUGIN_ROOT/scripts/design-pause-save.sh" --design-tmpdir "$DESIGN_TMPDIR" --issue
   "$_issue"` (fail closed with exit 2 if pause is requested but issue cannot be resolved). This
   restores the three inter-step pause opportunities that today sit between the three inline fences.

**Issue resolution for pause checkpoints (accepted FINDING_1 scope item).** `write-design-current-env.sh` /
`source-env.sh` emit `export ISSUE_NUMBER=...`; `phase_driver_session_get` only matches bare
`KEY=` lines and MUST NOT be the sole lookup. Add `_postplan_resolve_issue()`:

1. Use `${ISSUE_NUMBER:-}` when already set (orchestrator prelude sourced
   `current-design-env-$PPID.sh`).
2. Else, when `$DESIGN_TMPDIR/source-env.sh` exists, `source` it in the current shell (same
   round-trip as other design Bash blocks).
3. Else, awk-read `export ISSUE_NUMBER=` from `source-env.sh` without sourcing.
4. If still empty after pause was requested → exit 2 (config error).

Harness case #11 MUST build `source-env.sh` with `export ISSUE_NUMBER=...` (via
`write-design-current-env.sh` shim or hand-written export line), not bare `ISSUE_NUMBER=`.

Driver internal sequence (each step calls an existing helper — no logic duplication; each child
call uses `set +e` capture per FINDING_1):
1. EMIT_PLAN — `set +e`; pipe `ACTION=EMIT_PLAN` to `design-driver.sh --design-tmpdir DIR`;
   capture output + `_emit_rc`; `set -e`. Parse `EMIT_PLAN_STATUS` and KVs from output. On
   `_emit_rc != 0` OR `EMIT_PLAN_STATUS=missing-diff-lines`: set `POSTPLAN_EMIT_STATUS` to
   `missing-diff-lines` or `emit-failed`; `_postplan_write_result_and_emit`; exit 1 (do NOT run
   snapshot/validator).
2. Snapshot — only when `--snapshot-original` is set AND `workflow_path == HARD`:
   `set +e`; `snapshot-plan-round.sh write-original --design-tmpdir DIR`; `_snap_rc=$?`; `set -e`.
   On failure: `SNAPSHOT_STATUS=failed`, `POSTPLAN_EMIT_STATUS=snapshot-failed`,
   `_postplan_write_result_and_emit`; exit 1. Otherwise emit precise `SNAPSHOT_STATUS`
   (`taken` | `preserved` | `skipped-not-hard` | `skipped-suppressed`).
3. Validator — skip when `review_budget == quick` AND `--force-validate` is absent (set
   `VALIDATE_STATUS=skipped-quick`; no child call). Otherwise `set +e`; export `DESIGN_TMPDIR` +
   `CLAUDE_PLUGIN_ROOT`; run `invoke-plan-validator.sh "$DESIGN_TMPDIR/plan.txt"`; capture output +
   `_val_rc`; `set -e`. Parse validator KVs. `defects-found` is NOT a failure — set statuses and
   proceed to success flush. Validator INFRA failure (`_val_rc != 0` without `defects-found`):
   `POSTPLAN_EMIT_STATUS=validate-driver-failed`; flush; exit 1.

On success (including `defects-found` and `skipped-quick`): set `POSTPLAN_EMIT_STATUS=ok`; flush; exit 0.

**KV default/status matrix (FINDING_9).** Before step 1, initialize every listed key to explicit
defaults; never leave mandatory keys unset on any exit path. `_postplan_write_result_and_emit` runs
on all 0/1 paths before exit (FINDING_1).

| Key | Initial default | After EMIT ok | After EMIT fail | Snapshot skipped | Validator skipped | Exit 0 success |
|-----|-----------------|---------------|-----------------|------------------|-------------------|----------------|
| `POSTPLAN_EMIT_STATUS` | `pending` | `pending` | `missing-diff-lines` or `emit-failed` | (unchanged) | (unchanged) | `ok` (incl. `defects-found`, `skipped-quick`) |
| `EMIT_PLAN_STATUS` | `not-run` | parsed value | parsed value | (set) | (set) | (set) |
| `DIFF_LINES` | `""` | from EMIT KVs | `""` if not emitted | (set) | (set) | (set) |
| `SNAPSHOT_STATUS` | `not-run` | `not-run` | `not-run` | `skipped-not-hard` / `skipped-suppressed` / `taken` / `preserved` / `failed` | (set) | (set) |
| `VALIDATE_STATUS` | `not-run` | `not-run` | `not-run` | `not-run` | `skipped-quick` | parsed / `skipped-quick` |
| `VALIDATE_DEFECT_COUNT` etc. | `0` / `""` | `0` / `""` | `0` / `""` | `0` / `""` | `0` / `""` | parsed |

Exit codes (match sibling drivers): 2 = config/usage error; 1 = operation failure
(`missing-diff-lines` / `emit-failed` / `snapshot-failed` / `validate-driver-failed`); 0 = success,
including `defects-found` and `skipped-quick`. The driver always calls `_postplan_write_result_and_emit`
before exiting on the 0/1 paths.

Orchestrator gating after the driver (unchanged semantics, fewer lines):
- exit 2 → config error; abort `/design`.
- exit 1 → hard Step 2b failure. Read `POSTPLAN_EMIT_STATUS` (from merged parse): `missing-diff-lines` → repair
  `plan.txt` (same repair prose as today; do not require a secondary `EMIT_PLAN_STATUS` check);
  `snapshot-failed` → abort before Step 3; `validate-driver-failed` → infrastructure failure;
  other `emit-failed` → generic hard failure.
- exit 0 + `VALIDATE_STATUS=defects-found` → shared **Plan command validator failure** body
  (Fix-and-retry / Override / Cancel).
- exit 0 otherwise → Step 2b.5.

Re-emit sites keep their existing pre-EMIT dedup pass (`gate-b-dedup-plan.sh --snapshot-trailers`
then `--dedup`) OUTSIDE the driver, because dedup mutates `plan.txt` before `diff-lines.txt` is
recomputed. They then call `design-postplan-emit.sh` WITHOUT `--snapshot-original`, parse with the
**same file-first + stdout fallback** block, route `defects-found` to the shared body (site-specific
`--site` per table below), and continue to Step 2b.5 on exit 0 otherwise.

| Call site | Flags | Shared validator `--site` on `defects-found` |
|-----------|-------|-----------------------------------------------|
| Step 2b (initial) | `--snapshot-original` | `design Step 2b` |
| Gate A optional-trailer guard | (none) | `design discussion-round2` |
| Gate B shared post-apply pipeline | (none) | `design Step 3.5 / Gate B` |
| discussion-round2 plan revision | `--force-validate` | `design discussion-round2` |

## Files to modify/create

### NEW: `skills/design/scripts/design-postplan-emit.sh`
Phase driver per the Approach. `set -euo pipefail`; source `lib-phase-driver.sh`; `larch_quiet_init`;
`fail()` → exit 2; strict argv (`--design-tmpdir` required, `--snapshot-original`, `--force-validate`,
`-h/--help`). Resolve plugin root via `phase_driver_resolve_plugin_root` and export `CLAUDE_PLUGIN_ROOT` +
`DESIGN_TMPDIR`. Read `run-params.json` `review_budget` / `workflow_path` (`jq` with `sed` fallback,
matching the current Step 2b `_wp_snap` read). Implement `_postplan_resolve_issue()`,
`_postplan_pause_checkpoint()`, `_postplan_write_result_and_emit()` (flush helper per FINDING_1),
and per-step `set +e` capture around `design-driver.sh`, `snapshot-plan-round.sh`, and
`invoke-plan-validator.sh`. Initialize all KVs per the matrix; run the three internal steps; on every
0/1 exit call `_postplan_write_result_and_emit` before `exit`. KVs: `POSTPLAN_EMIT_STATUS`,
`EMIT_PLAN_STATUS`, `DIFF_LINES`, `SNAPSHOT_STATUS`, `VALIDATE_STATUS`, `VALIDATE_DEFECT_COUNT`,
`VALIDATE_SKIPPED_COUNT`, `VALIDATE_UNSAFE_TOKEN_COUNT`, `VALIDATE_LOG_FILE`, optional `WARN=`.
Executable bit set. Bash 3.2-safe.

### NEW: `skills/design/scripts/design-postplan-emit.md`
Sibling contract (per `.claude/rules/script-md-siblings.md`): purpose, callers (SKILL.md Step 2b;
approval-gates.md Gate A/Gate B; discussion-rounds.md round-2), flags (`--snapshot-original`,
`--force-validate`), the full KV/result-env contract including the default/status matrix,
exit-code table, `POSTPLAN_EMIT_STATUS=missing-diff-lines` repair routing, the
`defects-found`-is-not-failure invariant, the "stops before Step 2b.5 / AskUserQuestion" boundary,
pause checkpoint behavior (orchestrator prelude + `_postplan_resolve_issue` / driver-internal
checkpoints), **FINDING_1 invariant** (`set +e` per child call; `_postplan_write_result_and_emit`
mandatory on all 0/1 exits — child non-zero must never skip result-env/stdout), the no-duplication
note (wraps `design-driver.sh`, `snapshot-plan-round.sh`, `invoke-plan-validator.sh`),
**orchestrator handoff** (`_postplan_out` capture; symlink-guarded file-first
`.design-postplan-emit-result.env`; stdout merge fills only still-unset allowlisted keys; mandatory-key
abort when merge leaves routing keys empty on rc 0/1 — mirror `design-route.md` / `design-publish.md`),
and harness + Makefile lines.

### NEW: `skills/design/scripts/test-design-postplan-emit.sh`
Offline harness modeled on `test-design-publish.sh` / `test-invoke-plan-validator.sh`. Stub the
three helpers via a fake `CLAUDE_PLUGIN_ROOT`/`PATH` or fixture `design-driver.sh`/validator so no
network/external tools run. Cases: (1) happy SIMPLE non-quick (EMIT ok + no snapshot + validator ok,
exit 0, `POSTPLAN_EMIT_STATUS=ok`); (2) initial HARD with `--snapshot-original` (snapshot `taken`, exit 0);
(3) re-emit with snapshot suppressed (`SNAPSHOT_STATUS=skipped-suppressed`, exit 0); (4) `review_budget=quick`
without `--force-validate` (`VALIDATE_STATUS=skipped-quick`, validator not run, exit 0); (5) `defects-found` →
exit 0 with status surfaced, `POSTPLAN_EMIT_STATUS=ok`; (6) `missing-diff-lines` → exit 1
`POSTPLAN_EMIT_STATUS=missing-diff-lines` (not `emit-failed`); (7) snapshot failure when required → exit 1
`snapshot-failed`; (8) validator infra failure → exit 1 `validate-driver-failed`; (9) usage/config error →
exit 2; (10) result-env written before stdout emit on **all** partial-failure paths; all mandatory KVs
present when EMIT/snapshot/validator child exits non-zero (stub child rc=1 — asserts flush occurred, not
bare `set -e` abort); (11) `.pause-requested` present → `design-pause-save.sh` exec before first internal
step with `export ISSUE_NUMBER=...` in `source-env.sh` fixture; (12) `review_budget=quick` + `--force-validate` →
validator runs (parity with discussion-round2).

### NEW: `skills/design/scripts/test-design-postplan-emit.md`
Harness stub pointing at `design-postplan-emit.md` (primary owns the contract).

### UPDATED: `skills/design/SKILL.md`
Step 2b: replace the three post-plan fences (EMIT_PLAN, HARD-snapshot, validator KV-parse) with **one**
fence that keeps the canonical two-line prelude, then `design-postplan-emit.sh --design-tmpdir
"$DESIGN_TMPDIR" --snapshot-original` inside `set +e` capture (`_postplan_out` / `_postplan_rc`),
then **file-first** parse of `.design-postplan-emit-result.env` (symlink-guarded) followed by **stdout
fallback** from `_postplan_out` for still-unset allowlisted keys (mirror Step 0b / Step 5c — see Approach),
exit-2 abort prose, exit-1 hard-failure branch keyed on merged `POSTPLAN_EMIT_STATUS`
(`missing-diff-lines` → repair `plan.txt`), and `defects-found` → shared body branch. Update the Gate A
optional-trailer guard paragraph: after dedup breadcrumb, add a `set +e` Bash fence (prelude +
`design-postplan-emit.sh` without `--snapshot-original`, snapshot suppressed; **same parse block** as Step 2b);
on driver exit 0 + merged `VALIDATE_STATUS=defects-found`, execute **### Plan command validator failure (shared)** with
`--site` `design discussion-round2` and **Cancel** → Gate A; on exit 0 otherwise → Step 2b.5; preserve
exit-1/exit-2 handling mirroring Step 2b. Keep `gate-b-dedup-plan.sh --snapshot-trailers` / `--dedup`
references intact. Keep `ACTION=EMIT_PLAN` and `ACTION=VALIDATE_PLAN_COMMANDS` literals in the shared
validator-failure section only.

**Lead-in prose fix (FINDING_1):** Rewrite the "Immediately after saving plan.txt" paragraph
(~SKILL.md lines 762-771 today) to name `design-postplan-emit.sh --snapshot-original` only; remove
any bare `ACTION=EMIT_PLAN` instruction from that paragraph. Without this, an executor following
the stale lead-in prose AND the consolidated fence would pipe `ACTION=EMIT_PLAN` a second time,
producing divergent snapshot and validator paths (double-emit).

**Cross-ref refresh (FINDING_4):** Grep-update stale normative pointers that still name inline
`ACTION=EMIT_PLAN` / `invoke-plan-validator.sh` at re-emit boundaries:
- **Step 2b.5 Callable from** — name `design-postplan-emit.sh` (initial Step 2b; Gate B settled path;
  post-plan discussion sub-round) instead of bare `ACTION=EMIT_PLAN` re-emit.
- **Step 3.5 Gate B** prose (~settled path / Step 2b.5 after re-emit) — same driver name.
- **Step 1e optional-trailer guard** — replace inline EMIT + `when review_budget is full` validator
  with prelude + driver call + file-first/stdout parse prose (driver owns quick skip; Gate A does not pass `--force-validate`).

### UPDATED: `skills/design/references/approval-gates.md`
"Shared post-apply pipeline" steps 7–8: replace inline `ACTION=EMIT_PLAN` +
`invoke-plan-validator.sh` with one `design-postplan-emit.sh` call (snapshot suppressed; no
`--force-validate`) + **file-first/stdout KV parse (same as Step 2b)** + `defects-found` → shared body (`--site` `design Step 3.5 / Gate B`) +
Step 2b.5 on exit 0 otherwise, keeping the "runs the dedup/snapshot guard before the driver issues
`ACTION=EMIT_PLAN`" ordering phrase (retains pins 456/459: `before \`ACTION=EMIT_PLAN\``). Preserve
`gate-b-dedup-plan.sh` `--snapshot-trailers` / `--dedup` / `diff_added` / `diff_deleted` references.
Drop the separate `When review_budget is full` guard — the driver emits `skipped-quick` on quick
(matching today's Gate B step-8 semantics).

### UPDATED: `skills/design/references/discussion-rounds.md`
Round-2 sub-round "Plan revision authority" paragraph: same swap — dedup guard, then one
`design-postplan-emit.sh --force-validate` call (snapshot suppressed) + **file-first/stdout parse** + `defects-found` →
shared body (`--site` `design discussion-round2`) + Step 2b.5 on exit 0 otherwise, keeping the
"before `ACTION=EMIT_PLAN`" ordering phrase and trailer-preservation prose.

### UPDATED: `skills/design/references/flags.md` (FINDING_2)
**Plan-command validator** section (~line 68): replace “runs unconditionally on both SIMPLE and HARD
after each successful `ACTION=EMIT_PLAN`” with driver-accurate semantics:
- Post-plan validation is owned by `design-postplan-emit.sh` after each successful plan emit on
  `plan.txt` (initial Step 2b and re-emit sites), and still runs on `composed-plan.md` in Step 5c
  publish path.
- When `review_budget` is `quick`, the driver skips the validator (`VALIDATE_STATUS=skipped-quick`)
  at Step 2b, Gate A re-emit, and Gate B — matching the full plan-review panel skip.
- `discussion-round2` re-emit passes `--force-validate` so validation still runs on quick (parity with
  today’s unconditional `invoke-plan-validator.sh` at that site).
- Keep the existing **Defect handling** bullet (shared AskUserQuestion body).

### UPDATED: `scripts/test-design-structure.sh`
Add driver pins: bind `DESIGN_POSTPLAN_EMIT_SH`, assert executable; assert it contains the
`ACTION=EMIT_PLAN` dispatch, `snapshot-plan-round.sh` `write-original`, `invoke-plan-validator.sh`,
`_postplan_resolve_issue` (or equivalent), `_postplan_pause_checkpoint` (or equivalent),
`_postplan_write_result_and_emit` (or equivalent), and per-step `set +e` around at least one child
call (FINDING_1); EMIT at-or-before validator (order check on the **driver script**, not SKILL.md
inline fences).

Assert SKILL.md, approval-gates.md, and discussion-rounds.md each invoke `design-postplan-emit.sh`;
assert SKILL.md reads `.design-postplan-emit-result.env` file-first, merges `_postplan_out` for
still-unset allowlisted keys (`<<<"${_postplan_out:-}"` or equivalent), and carries driver exit-2 abort
prose; assert Step 2b post-plan fence retains the canonical prelude before the driver call.

**flags.md pin (FINDING_2):** migrate line ~124 pin from
`Plan-command validator runs unconditionally on both SIMPLE and HARD` to driver-accurate anchors, e.g.
`review_budget` + `skipped-quick` + `design-postplan-emit.sh` + `--force-validate` (must FAIL if
flags.md reverts to unconditional-only wording).

**Coupled pin migration (lockstep with prose — includes 14c14d–h):**
- **14b10** → grep Step 2b block for `design-postplan-emit.sh` before `check-plan-size.sh` / Step 2b.5
  (drop inline EMIT-before-validator awk).
- **14c14c** → retarget to `design-postplan-emit.sh` invoke in `approval-gates.md` (drop bare
  `ACTION=EMIT_PLAN`-only pin or fold into driver invoke pin).
- **14c14d** → `approval-gates.md` must reference `design-postplan-emit.sh` (replaces
  `invoke-plan-validator.sh` pin).
- **14c14e** → awk: first `design-postplan-emit.sh` at or before first `Step 2b.5` in shared
  post-apply section (replaces EMIT-before-validator ordering pin).
- **14c14f** → `discussion-rounds.md` must reference `design-postplan-emit.sh` (replaces bare
  `ACTION=EMIT_PLAN` pin).
- **14c14g** → `discussion-rounds.md` must reference `design-postplan-emit.sh` (replaces
  `invoke-plan-validator.sh` pin).
- **14c14h** → awk: `design-postplan-emit.sh` at or before `Step 2b.5` in plan-revision authority
  (replaces EMIT-before-validator ordering pin).
- **discussion-rounds validator pin (line ~163)** → retarget to `design-postplan-emit.sh` (FINDING_6;
  do not leave a standalone `invoke-plan-validator.sh` file-level grep on `discussion-rounds.md`).
- **14c14i (Gate A, FINDING_8)** — bounded block pin: between `Optional trailer guard (Gate A re-entry
  rewrites)` and the next `<!-- step:` / `## Step` header, require `design-postplan-emit.sh` AND the
  shared `defects-found` / `Plan command validator failure` routing (not satisfied by a file-level
  SKILL.md grep alone).
- **FINDING_21** → `check-plan-size.sh` after `design-postplan-emit.sh` in Step 2b block (not bare
  `ACTION=EMIT_PLAN`).
- **FINDING_21 approval-gates** → `Step 2b.5` after `design-postplan-emit.sh` in shared post-apply
  section (not bare `ACTION=EMIT_PLAN`).
- **FINDING_1 double-emit exclusion pin** — bounded-block pin: within the Step 2b block (from the
  `<!-- step:2b` / `## Step 2b` marker to the next step header), assert `ACTION=EMIT_PLAN` does NOT
  appear outside the `VALIDATE_PLAN_COMMANDS` / validator-failure subsection. Must FAIL if the
  "Immediately after saving plan.txt" paragraph or any fence outside that subsection retains bare
  `ACTION=EMIT_PLAN`.
- **1124–1125** → grep `design-postplan-emit.sh` for `snapshot-plan-round.sh` / `write-original`
  (replaces SKILL.md inline snapshot pins).
- **456/459** → unchanged (`before \`ACTION=EMIT_PLAN\`` ordering phrase retained in references).

Each rewritten pin must still FAIL when its guarded property is violated (temporarily break to
confirm — no vacuous greps).

### UPDATED: `Makefile`
Add `test-design-postplan-emit` target (mirror `test-design-publish`), append it to a
`test-harnesses-N` shard line and the two `.PHONY` lines.

### UPDATED: `docs/` (only if grep finds stale pointers) (FINDING_2)
Grep `docs/`, `README.md`, `skills/**` for prose naming the inline Step 2b EMIT/snapshot/validator
fences (drift-prone-prose rule). **Explicit file list must include**
`skills/design/references/flags.md` **Plan-command validator** section (not only SKILL.md /
approval-gates / discussion-rounds). Update any stale reference to name the driver and
`review_budget=quick` / `--force-validate` parity. Likely churn is `flags.md` plus the files above;
this is a verification step, not assumed churn beyond those.

## Edge cases

- `review_budget=quick`: validator skipped at Step 2b, Gate A, and Gate B (driver emits
  `skipped-quick`); **not** skipped at discussion-round2 (`--force-validate`).
- HARD initial vs HARD re-emit: snapshot only at the initial call (flag present); re-emit emits
  `skipped-suppressed` even on HARD.
- Idempotent snapshot: `snapshot-plan-round.sh write-original` preserves an existing
  `plan.txt-original` (emit `SNAPSHOT_STATUS=preserved`); never overwrite.
- `defects-found` must reach the orchestrator with exit 0 so the shared AskUserQuestion fires; an
  exit-1 here would wrongly trigger the hard-failure repair path — **all four call sites**, including
  Gate A optional-trailer guard.
- `missing-diff-lines` must surface as `POSTPLAN_EMIT_STATUS=missing-diff-lines` (exit 1) so
  orchestrator repair prose fires without a parallel `EMIT_PLAN_STATUS`-only branch.
- Plugin-root resolution must work when `CLAUDE_PLUGIN_ROOT` is unset (driver invoked from a fresh
  Bash subshell) — rely on `phase_driver_resolve_plugin_root` + `session-env.sh`.
- `invoke-plan-validator.sh` requires `DESIGN_TMPDIR` + `CLAUDE_PLUGIN_ROOT` exported; the driver
  must export both before calling it.
- Cooperative pause: `.pause-requested` between internal steps must still `exec` pause-save; issue
  resolution must use prelude-sourced or `export ISSUE_NUMBER=` `source-env.sh`, not bare
  `phase_driver_session_get` alone.
- Partial failure: snapshot/validator keys must read `not-run` / `skipped-*`, never empty, when an
  earlier step aborts.
- **Child non-zero under `set -e` (FINDING_1):** EMIT/snapshot/validator rc != 0 must still flush
  result-env + stdout KVs before exit 1; never rely on the shell aborting out of the driver.
- **Result-env write failure / missing file (FINDING_1):** orchestrator MUST still populate routing
  keys from `_postplan_out` when the env file is absent, unreadable, or a refused symlink; abort only
  when merge leaves `POSTPLAN_EMIT_STATUS` / `VALIDATE_STATUS` unset on rc 0/1.

## Failure modes

1. **Structural-test pin drift breaks CI.** The Step 2b / approval-gates / discussion-rounds / Gate A
   pins (especially 14c14d–i and line ~163) are tightly coupled to inline literals. Earliest signal:
   `make test-design-structure` fails (or, worse, passes vacuously). Mitigation: migrate every coupled
   pin listed above in the same change as the prose edit; after editing, temporarily break each guarded
   property to confirm the pin still fails.
2. **`defects-found` mis-mapped to a hard failure.** If the driver exits non-zero on
   `defects-found`, or Gate A omits the shared body branch, the orchestrator skips the
   AskUserQuestion. Mitigation: harness case (#5); explicit Gate A + Gate B + discussion-round2
   prose; site table in Approach; Gate A bounded pin 14c14i.
3. **Snapshot suppressed at the initial call or taken at a re-emit.** Wrong `--snapshot-original`
   wiring would either lose the HARD assessor baseline or snapshot a post-revision plan. Mitigation:
   harness cases #2/#3; only initial Step 2b passes the flag.
4. **Pause regression.** Collapsing three fences without driver checkpoints, dropping the prelude, or
   resolving issue via `phase_driver_session_get` on `export ISSUE_NUMBER=` lines. Mitigation:
   `_postplan_resolve_issue`; harness case #11 with export-format fixture; structural pin for
   prelude-before-driver in Step 2b fence.
5. **discussion-round2 quick-skip behavior change.** Omitting `--force-validate` at that call site
   would skip validation on quick runs for the first time. Mitigation: Scope documents parity;
   harness case #12; `--force-validate` in call-site table.
6. **KV contract drift.** Orchestrator reads empty/stale keys after early abort. Mitigation: init
   matrix in driver + contract doc; harness case #10 (stub non-zero child rc).
7. **`set -e` abort before result flush (FINDING_1).** Missing `set +e` on a child call or exiting 1
   without `_postplan_write_result_and_emit` leaves no `.design-postplan-emit-result.env`. Mitigation:
   per-step capture pattern in driver; contract doc invariant; harness case #10; structural pin for
   `set +e` + flush helper in driver script.
8. **Stdout fallback omitted (FINDING_1).** File-first-only parse when result-env is missing leaves
   empty `POSTPLAN_EMIT_STATUS` / `VALIDATE_STATUS` despite KVs in `_postplan_out` — wrong routing.
   Mitigation: Step 2b inline parse block; re-emit cross-ref; structural pin for `_postplan_out` merge;
   contract doc orchestrator handoff section.
9. **flags.md drift (FINDING_2).** Consumer doc still claims unconditional validator after driver
   lands. Mitigation: explicit `flags.md` update + structural pin migration; docs grep includes
   `flags.md`.
10. **Double-emit from stale Step 2b lead-in prose (FINDING_1).** The "Immediately after saving
    plan.txt" paragraph (~SKILL.md:762-771) names bare `ACTION=EMIT_PLAN`; without rewriting it,
    an executor following that paragraph AND the consolidated fence pipes `ACTION=EMIT_PLAN` a
    second time, diverging snapshot and validator state. Mitigation: lead-in prose rewrite in
    SKILL.md (FINDING_1 note above); FINDING_1 double-emit exclusion pin in structural tests.

## Testing strategy

- New `bash skills/design/scripts/test-design-postplan-emit.sh` (12 cases above) and
  `make test-design-postplan-emit`.
- `bash scripts/test-design-structure.sh` — all pins green, including 14c14d–i rewrites, Gate A
  bounded pin, FINDING_1 driver pins (`set +e`, flush helper), FINDING_1 stdout-fallback pin,
  FINDING_1 double-emit exclusion pin (Step 2b block must not contain bare `ACTION=EMIT_PLAN`
  outside the validator-failure section), and FINDING_2 `flags.md` validator pin.
- `bash scripts/relevant-checks.sh` (or `make lint`) for shellcheck, markdownlint, bash32, the
  script-md-sibling and skill-invocation linters, and the references-headers check.
- Spot-run the existing `test-design-driver`, `test-invoke-plan-validator`, `test-snapshot-plan-round`
  harnesses to confirm the wrapped helpers are unchanged.
- Grep-verify `skills/design/references/flags.md` Plan-command validator section matches driver
  `skipped-quick` / `--force-validate` semantics (FINDING_2).

## Acceptance

- `skills/design/scripts/design-postplan-emit.sh` exists, is executable, and is built on `lib-phase-driver.sh`. It runs `ACTION=EMIT_PLAN`, a conditional HARD `snapshot-plan-round.sh write-original` (only with `--snapshot-original` AND `workflow_path == HARD`), and a conditional `invoke-plan-validator.sh` (skipped on `review_budget == quick` unless `--force-validate`). It emits the combined KV / result-env contract (`POSTPLAN_EMIT_STATUS`, `EMIT_PLAN_STATUS`, `DIFF_LINES`, `SNAPSHOT_STATUS`, `VALIDATE_STATUS` + counts + log) and uses exit 2 = config, 1 = op-failure, 0 = success (including `defects-found` and `skipped-quick`).
- Per-child `set +e` capture and a `_postplan_write_result_and_emit` flush run on every 0/1 exit (no `set -e` abort before the result-env / stdout KVs are written). Driver-internal pause checkpoints + `_postplan_resolve_issue` preserve the three inter-step pause opportunities.
- Sibling `design-postplan-emit.md` contract and offline harness `test-design-postplan-emit.sh` (+ `.md` stub) exist; `make test-design-postplan-emit` passes all listed cases (happy SIMPLE, HARD snapshot, snapshot-suppressed re-emit, quick-skip, `--force-validate`, `defects-found` → exit 0, `missing-diff-lines` → exit 1, snapshot-failure, validator-infra-failure, config error, result-env-before-stdout flush on partial failure, pause checkpoint).
- `skills/design/SKILL.md` Step 2b replaces the three inline fences with one driver call carrying the canonical prelude + `set +e` capture + file-first/stdout KV parse; the Gate A re-entry guard, `approval-gates.md` Gate B "Shared post-apply pipeline", and `discussion-rounds.md` round-2 each route EMIT+validator through the driver (snapshot suppressed; discussion-round2 passes `--force-validate`).
- `defects-found` still fires the shared Fix-and-retry / Override / Cancel `AskUserQuestion` at all four call sites; `missing-diff-lines` still triggers the `plan.txt` repair path; Step 2b.5 still runs after the driver returns. The orchestrator boundary is unchanged (driver stops before the AskUserQuestion and Step 2b.5).
- Loop-internal EMIT_PLAN sites (`plan-review-loop.sh`, `revise-plan-with-waterfall.sh`) are unchanged.
- `scripts/test-design-structure.sh` coupled pins are migrated in lockstep (14b10, 14c14c-h, FINDING_21, 1124-1125 retargeted to the driver; new driver pins for executable + internal EMIT/snapshot/validator + SKILL/approval-gates/discussion-rounds invocation + result-env file-first read + exit-2 prose) and each still fails when its guarded property is violated. `skills/design/references/flags.md` Plan-command-validator section reflects driver-accurate `skipped-quick` / `--force-validate` semantics.
- `bash scripts/test-design-structure.sh`, `make test-design-postplan-emit`, and `bash scripts/relevant-checks.sh` (shellcheck, markdownlint, bash32, script-md-siblings, skill-invocation, references-headers) all pass. No behavior change to the post-plan emit contract beyond the consolidation.

diff_lines: 884
