## Goal
Implement issue #3650: [IMPLEMENTING] [URGENT] Remove OOS from ship-pr; add post-ship file_oos.py (supersedes #3639)\n\n## Summary.

## Implementation Plan
## Summary

**Remove all out-of-scope (OOS) handling from the ship driver** (`python/ship.py` and the legacy `scripts/ship-pr.sh`) and relocate OOS filing into a new, dedicated **post-ship** step backed by `python/file_oos.py`. After this change, the ship driver ships the PR and knows nothing about OOS; a separate, mandatory, idempotent step files accepted OOS follow-up issues after ship-pr returns.

This **supersedes #3639** (the bash OOS gate's futile vendor CI-fix waterfall). Rather than patch the bash gate's failure routing, we delete the gate from both paths — the bug becomes structurally impossible because ship-pr no longer touches OOS.

Severity: **URGENT** — #3639 can stall a routine `/implement --merge` run for ~1.5h (or hang) on the bash fallback path. The decoupling removes that failure mode entirely and eliminates a recurring bug cluster (#3550, #3639, #3457, #3496, #3495, plus `safe_bail_reason_value` OOS-routing churn) rooted in entangling OOS adjudication with the ship state machine.

## Motivation

Today the ship driver does **not** file OOS — filing already lives in the main agent at Step 9a.1 (`/issue` pipeline). What lives in ship-pr is a **fail-closed disposition gate** that blocks `pr-create` until filing evidence (`oos-issues.ndjson`) exists, then bounces back to Step 9a.1 (Exit 3 `NEEDS_USER_INPUT` / `oos-filing`). Findings:

- **Every gate input is produced upstream of ship-pr** and is static during the run: `oos-accepted-review.md` (Step 5), `oos-accepted-design.md` (`/design`), `oos-accepted-main-agent.md` (main-agent dual-write), manifest `oos_observations` (`materialize-manifest-oos.sh`), `security-oos-observations.md`. Nothing new is born inside ship-pr's pr-create/CI phases (the CI loop is mechanical and never runs the voting panel). The gate computes nothing it couldn't compute elsewhere.
- The gate's only action on failure is "go file elsewhere." A guard at the wrong altitude.
- The entanglement with ship-pr's exit-code taxonomy, the `OOS_PENDING` resume state, and the recovery waterfall is where the bugs live — not in counting OOS blocks.

OOS items are, by definition, **non-blocking follow-ups for work that shipped**. They should not gate the PR. Filing them after ship-pr embraces that and removes OOS from the ship critical path.

## Design

### New: `python/file_oos.py` (deterministic OOS engine)

A stdlib-only module + CLI entry (`python3 python/file_oos.py`), run as a **terminal post-ship step**. Responsibilities (all the deterministic mechanics currently scattered across `oos.py` + Step 9a.1):

1. **Detect** accepted, non-security OOS across the upstream inputs above. Reuse the block-counting / header-parsing logic currently in `python/oos.py`, **including the #3550 legacy-header support** (`### FINDING_N: [OUT_OF_SCOPE]` counts, not just `### OOS_N:`) and the security-header classification that excludes security findings from public filing.
2. **Idempotency** via the existing `$IMPLEMENT_TMPDIR/oos-issues-created.md` sentinel — recover prior URLs/tallies with no re-file (NEVER #14 / Invariant #1 in SKILL.md).
3. **Record** outcomes: write `oos-issues.ndjson` and the `oos-issues` larch-log batch (filed + "Rejected / Out-of-Scope" not-filed sub-block), then refresh the final report / tracking-issue `larch:final-summary` comment with filed URLs.
4. **Carve-outs**: `forked_target=true` → no filing (text-only in final report); `repo_unavailable=true` → skip filing, keep items in `oos-accepted-*.md` and report "Skipped — repo unavailable". Security findings are NEVER filed here (SECURITY.md private flow).

**Boundary (important):** the actual GitHub issue creation + **semantic cross-run dedup remains the `/issue` pipeline** (LLM), invoked by the orchestrator step. `file_oos.py` prepares the to-file set and consumes/records the result; it does **not** call an LLM and should **not** be reduced to raw `gh issue create` (that would drop `/issue`'s dedup and risk duplicate OOS issues across runs). This matches larch's deterministic-script / LLM-orchestrator split.

### Orchestrator wiring (`skills/implement/SKILL.md`)

- Step 8+ no longer handles an OOS bounce from ship-pr: remove `OOS_PENDING` and the Exit 3 `oos-filing` handling around the ship-pr `Invoke:`.
- Rehome OOS filing (current Step 9a.1) to a **terminal post-ship step** that runs **after ship-pr returns**, gated `repo_unavailable=false` + non-fork, composing `file_oos.py` + `/issue`.
- This step is **mandatory and loud**: its failure surfaces and the run does **not** terminate clean until OOS is filed (idempotent re-run recovers). See Invariant change below.

### Invariant change — NEVER #14 enforcement point

NEVER #14 ("never silently drop a voted-in OOS finding") moves from a **pre-merge hard gate** to a **mandatory, loud, idempotent post-ship filer**. The merge is no longer blocked on OOS; instead the *run* is not considered done until the post-ship filer succeeds. A failure is loud and re-runnable, never a silent drop. **Update SKILL.md's NEVER #14 (and any prose describing the OOS gate / `OOS_PENDING` checkpoint) to describe the new model** — do not leave the documented invariant describing a gate that no longer exists.

## Removal checklist

### `python/ship.py` (61 refs → 0)
Remove: `import oos`; `oos_observation_count()`, `resolve_oos_accepted_design_path()`, `_materialize_manifest_oos()`, `_oos_gate()`, `_pending_oos_gate()`, `_has_oos_gate_inputs()`; the pr-create-phase call block that invokes `_materialize_manifest_oos` / `_pending_oos_gate` before `pr.ensure_pr`; the `OOS_PENDING` state read/write/serialize and `ctx.oos_pending` usage; all `config.NEEDS_USER_OOS_FILING` returns. After removal, `grep -i oos python/ship.py` must be empty.

### `python/oos.py` (whole module)
Move the reusable detection/parsing (block counting, OOS/legacy/security header regexes — the #3550 fix) into `file_oos.py`. Delete gate-only logic (`disposition_ok` and friends) that has no post-decouple consumer. Rename tests `test_oos.py` → `test_file_oos.py`.

### `python/config.py` (3 refs)
Remove `NEEDS_USER_OOS_FILING` if unused after ship.py removal. Relocate `INLINE_TRIAGE_MARKER` / `OOS_FILED_URL_FIELD` to `file_oos.py` if still needed there.

### `python/run_context.py` (2 refs) and `python/run_logs.py` (1 ref)
Remove the `oos_pending` field and the `OOS_PENDING` state read helper.

### `scripts/ship-pr.sh` (bash — this is what actually resolves #3639)
Remove: `run_oos_disposition_gate_if_required_before_oos_pending_false`; the `pr-prep-oos` gate-failure routing through `run_recovery_waterfall pr-prep fix "$fail_file" pr-prep-oos`; the manifest-OOS and security-OOS `OOS_PENDING=true; advance_phase pr-create` checkpoint branches; the `OOS_PENDING` state key and the "refusing PR creation while OOS_PENDING=true" guard; the `pr-prep-oos` case in `run_recovery_waterfall`'s verify dispatcher. `run_pr_prep_phase` advances straight to `pr-create`.


## Test plan
`python/test_ship.py` (drop OOS gate/materialize/pending cases), `python/test_run_context.py`, `python/test_config.py`; new `python/test_file_oos.py` (port + extend `test_oos.py`, keep the #3550 legacy-header assertion). Bash `scripts/test-*.sh` harnesses that assert OOS-gate behavior.
