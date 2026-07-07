## Plan

## Summary

Add a plan-size guardrail to `/design` that measures firm-heading count and distinct top-level surfaces alongside existing plan-body-line and diff-size signals, blocks an oversized single plan from finalizing by default, and lets the operator decompose it (existing panel, hardened prepare output) or record an explicit `oversize_override: operator` trailer in the plan block. Thresholds live in `python/larch/core/config.py` with calibration rationale anchored to the #6514 incident.

Reuses Step 2b.5 `hard-trigger` routing (`SIZE_TRIGGER_FIRED` → `step2b5_next_action_for` unchanged), optional-trailer preservation across the revise waterfall and Gate B snapshot/dedup, and the decompose panel. Adds a fail-closed Step 5c finalization guard on the authoritative `plan.txt` body, with compose/publish paths and downstream metadata scanners taught to treat `oversize_override: operator` as trailer metadata end-to-end.

Split-path prepare is hardened so filed part issues carry per-piece firm-heading inventories, acceptance criteria (panel-authored or deterministic fallback), serial `blocked-by` edges, and scaffold bodies ready for per-issue `/design` before `/implement`. Every Override path writes the override trailer to `plan.txt` and deletes stale `composed-plan.md` so publish cannot fail open on divergent composed artifacts.

## Approach

- Fold new signals into the existing detector. `check_plan_size_main` gains firm-heading and surface counting and folds `firm-headings` / `surfaces` reason tokens into `TRIGGER_REASONS` and `SIZE_TRIGGER_FIRED`. `step2b5_next_action_for` already routes `SIZE_TRIGGER_FIRED=true` to `hard-trigger`; the action decider needs no change.
- Override is a preserved optional trailer. `oversize_override: operator` is taught to `parse_optional_metadata`, added to `OPTIONAL_KEYS`, mirrored in `OPTIONAL_TRAILER_KEYS` (Gate B snapshot/dedup), and recognized by publish compose, Step 5c auto-compose, difficulty parsing, bootstrap plan stripping, and implement preflight metadata scans. When present it suppresses the size hard trigger (mirroring `mechanical_churn` for diff only); the detector emits `OVERSIZE_OVERRIDE=operator`.
- Thresholds centralize in config. Existing literals (800/1500/2000) and new thresholds (firm headings 25, surfaces 4) become `Final` constants in `python/larch/core/config.py` with a rationale comment; the detector references them (G-Cfg-1).
- Drafter and postplan contracts expose the override trailer. `design_step2b.py` prompt strings document `oversize_override: operator` as an allowed optional trailer immediately above `diff_lines:`; Step 2b `postplan-rc12-split` and every other hard-trigger site share the same Split / Override / Cancel contract.
- Interactive Override at every hard-trigger site. Every Split / Override / Cancel site (initial Step 2b, `postplan-rc12-split`, discussion merged, retained Step 2b.5, Gate B `gate-b-hard-size`, Step 5c oversize recovery) invokes `plan set-oversize-override` on `plan.txt`, then **always** `rm -f "$DESIGN_TMPDIR/composed-plan.md"` before `design step2b-postplan --write-completion-only` or continuing to Step 3 / Step 5c retry. No in-place `composed-plan.md` override path; authoritative guard stays on `plan.txt` and recompose rebuilds `composed-plan.md` from the updated source.
- Fail-closed finalization guard on authoritative plan body. `publish_core` re-checks size on `plan.txt` via `plan check-size --design-tmpdir "$DESIGN_TMPDIR" --plan-file "$DESIGN_TMPDIR/plan.txt"` (same artifact as Step 2b.5; avoids composed-only envelope lines inflating `PLAN_LINES`). Treat subprocess non-zero exit, missing `PLAN_SIZE_STATUS`, or any value other than the successful ok path as publish refusal (`return 4`). Only when check-size succeeds **and** `SIZE_TRIGGER_FIRED=false` may publish continue. When check-size succeeds with `SIZE_TRIGGER_FIRED=true`, emit `PUBLISH_REFUSE_REASON=oversize-no-override`. When check-size itself fails, emit `PUBLISH_REFUSE_REASON=size-check-failed`. `finalize-step5.md` branches on those KVs before the review-provenance special case.
- Decompose panel and prepare emit implement-ready scaffolds. Extend panel prompt schema (`_common-tail.txt`, `aggregate_partition` merge prompt, `decompose-panel.md`) with required `- firm-headings:` and `- acceptance:` bullets per piece. `prepare_partition_issues` derives missing bullets from the parent `plan.txt` using `issue_wire.extract_scope_paths(..., include_optional=False)` and deterministic fallbacks; returns `missing-piece-metadata` when either bullet is still empty. Emit serial execution-order edges: sort pieces by `Piece N` number, then write adjacent `blocked-by` TSV rows `(N → N+1)` for every consecutive pair; merge panel `- Dependencies:` only when they do not break acyclicity or the serial chain. Filed part issue bodies include firm-heading inventory, acceptance criteria, and a placeholder `larch:plan` block noting per-piece `/design` is required before `[DESIGNED]` / `/implement`.

### Surface definition (judgment call, flagged for plan review)

For each firm heading's path: `python/larch/<pkg>` when the path is under `python/larch/<pkg>/...`; `python/larch` for a top-level file directly in that package; otherwise the first path segment (`skills`, `docs`, `scripts`, `python`, ...). Count distinct surfaces across firm headings only (MAY_UPDATE excluded). Larch multi-surface refactors trip `surfaces > 4`; the release valve is Override or decompose; firm-heading count remains the primary fits-in-one-pass signal.

### Firm-heading → piece matching (prepare fallback)

Parse parent firm headings from `plan.txt` (same grammar as detector; MAY_UPDATE excluded). For each piece, parse `- scope:` path tokens. A heading path matches a piece when it equals a scope token or is under one (`path == token` or `path.startswith(token.rstrip("/") + "/")`). Unmatched headings fail closed with `missing-piece-metadata` unless the panel supplied `- firm-headings:` explicitly.

### Acceptance fallback (prepare)

When `- acceptance:` is absent from a piece body, derive bounded bullets from the parent plan's `## Testing strategy` section: include strategy bullets whose cited paths or symbols intersect that piece's firm-heading inventory; if none match, emit a single default tied to the piece scope (`Verify <scope summary> per parent Testing strategy`). Empty result after fallback → `missing-piece-metadata`.

## Files to modify

### UPDATED: python/larch/core/config.py
- Add a `# Plan-size guardrail thresholds (#6527)` block of `Final` constants: `PLAN_SIZE_MAX_PLAN_BODY_LINES = 800`, `PLAN_SIZE_MAX_DIFF_ADDED = 2000`, `PLAN_SIZE_MAX_DIFF_LINES = 1500`, `PLAN_SIZE_MAX_FIRM_HEADINGS = 25`, `PLAN_SIZE_MAX_SURFACES = 4`, `OVERSIZE_OVERRIDE_OPERATOR = "operator"`.
- Rationale comment anchored to run 0BE6E8A0 / #6514 (85 firm headings, `diff_lines: 4800`, silent 25-of-85 landing under `STATUS=complete`).

### UPDATED: python/larch/design/_plan_quality_commands.py
- Add `oversize_override: str | None` field to `OptionalMetadata` (after `mechanical_churn`).
- Add `"oversize_override"` to `OPTIONAL_KEYS`.
- Extend `optional-trailers parse` CLI surface to print the oversize_override value.

### UPDATED: python/larch/design/plan_quality.py
- `parse_optional_metadata`: recognize `oversize_override: operator` in the contiguous metadata-block upward scan and value-extraction loop; thread into `OptionalMetadata` and `keys`.
- Add `_firm_heading_count(text)`, `_plan_surface(path)`, `_plan_surfaces(text)` per the surface definition.
- `check_plan_size_main`: replace inline literals with `config.PLAN_SIZE_*`; compute `firm_headings` and `surfaces`; append hard triggers in fixed priority order; when `meta.oversize_override == config.OVERSIZE_OVERRIDE_OPERATOR`, force `SIZE_TRIGGER_FIRED=false` and set advisory; emit `FIRM_HEADINGS`, `SURFACES_TOUCHED`, `OVERSIZE_OVERRIDE`, `PLAN_SIZE_STATUS=ok` on success.
- Add `set_oversize_override_main(argv)`: `--design-tmpdir` plus optional `--plan-file` / `--remove`; atomically insert `oversize_override: operator` immediately above `diff_lines:` (or remove it); idempotent; symlink/CRLF-safe.

### UPDATED: python/larch/cli.py
- Register `("plan", "set-oversize-override"): ("larch.design.plan_quality", "set_oversize_override_main")` in the dispatch table and ported-verb allowlist next to `("plan", "check-size")`.

### UPDATED: python/larch/design/design_postplan.py
- Pass `FIRM_HEADINGS`, `SURFACES_TOUCHED`, `OVERSIZE_OVERRIDE` from `size_kv` into the `kvs.update({...})` block and `flush()` print list.

### UPDATED: python/larch/design/design_publish.py
- Extend `_OPTIONAL_TRAILER_RE` and `_is_trailer_region_line()` to treat `oversize_override: operator` as trailer text (aligned with `parse_optional_metadata`).
- Preserve `oversize_override` through `_splice_plan_provenance` and any trailer-region peeling.
- In `publish_core`, immediately after the review-provenance refusal block and before pause / named-block write: run `plan check-size --design-tmpdir <tmpdir> --plan-file <tmpdir>/plan.txt` via `_run_cli` (authoritative plan body; both args required). Fail closed: non-zero subprocess exit, absent `PLAN_SIZE_STATUS`, or `PLAN_SIZE_STATUS` not equal to the successful ok token → `PUBLISH_REFUSE_REASON=size-check-failed`, `return 4`. When check-size succeeds and `SIZE_TRIGGER_FIRED=true` → `PUBLISH_REFUSE_REASON=oversize-no-override`, `return 4`. Only `PLAN_SIZE_STATUS=ok` with `SIZE_TRIGGER_FIRED=false` passes the guard.

### UPDATED: python/larch/design/design_step5c.py
- Add `PUBLISH_REFUSE_REASON` to `STEP5C_PUBLISH_RESULT_ALLOW_KEYS`; assert it survives `_step5c_safe_publish_env` on refusal paths.
- Extend `_AUTO_COMPOSE_OPTIONAL_TRAILER_RE`, `_split_plan_body_and_trailers`, `_peel_trailing_optional_trailers`, and `_optional_trailer_lines_from_values_file` to include `oversize_override: operator`.
- Ensure `_build_trailer_lines_from_sidecars` / auto-compose round-trip carries the override from `plan.txt` or `.gate-b-optional-trailer-keys.values` into `composed-plan.md` (always rebuilt from `plan.txt` after Override deletes stale compose).
- Thread `FIRM_HEADINGS` / `SURFACES_TOUCHED` / `OVERSIZE_OVERRIDE` through retained `step2b5_main` presentation when surfacing size KVs (same passthrough as `design_postplan.py`).

### UPDATED: python/larch/design/design_step2b.py
- Extend `_compose_drafter_prompt` drafting bullets and `LARCH_PLAN_BEGIN` contract line to document optional `oversize_override: operator` immediately above `diff_lines:` (alongside `diff_added` / `diff_deleted` / `mechanical_churn`).
- Extend any inline drafter sidecar / postplan operator-prompt text emitted for `postplan-rc12-split` to list Split / Override / Cancel with Override calling `plan set-oversize-override` then deleting `composed-plan.md` when present.

### UPDATED: python/larch/review/plan_review_common.py
- Add `"oversize_override"` to `OPTIONAL_TRAILER_KEYS` (keep in sync with `_plan_quality_commands.OPTIONAL_KEYS`; prefer importing shared set if trivial).
- Add `FIRM_HEADINGS`, `SURFACES_TOUCHED`, `OVERSIZE_OVERRIDE` to `POSTPLAN_EMIT_KEYS`.

### UPDATED: python/larch/calibration/difficulty.py
- Add `oversize_override: operator` to `_PLAN_TRAILER_LINE_RE` so `oversize_override` does not terminate the trailing metadata span before `review_status` / `rounds_completed` / `difficulty`.

### UPDATED: python/larch/state/bootstrap.py
- Add `oversize_override: operator` to `_OPTIONAL_PLAN_SIZE_TRAILER_RE` in `_strip_plan_provenance_headers` so materialization does not treat the override as plan body.

### UPDATED: python/larch/implement/preflight.py
- Add `"oversize_override: "` to the allowed metadata-prefix scan tuple alongside `diff_added:` / `mechanical_churn:` so review provenance remains visible when the override trailer is present.

### UPDATED: python/larch/design/decompose.py
- In `aggregate_partition` merge prompt (lines 605–611): extend required `### Piece N:` schema with `- firm-headings: <comma-separated paths>` and `- acceptance: <one or more implementable criteria>` bullets.
- In `prepare_partition_issues`:
  - Load parent `plan.txt` when present; call `issue_wire.extract_scope_paths(plan_text=..., include_optional=False)` for scope tokens.
  - Parse panel `- firm-headings:` / `- acceptance:` when present; otherwise derive via firm-heading→piece matching and acceptance fallback rules above.
  - Return `missing-piece-metadata` when either bullet is empty after fallback.
  - After cycle check, sort pieces by `Piece N` number; emit `partition-deps.tsv` with adjacent serial edges `(i+1 → i+2)` for execution order; fold panel `- Dependencies:` only when they preserve acyclicity and do not remove the serial chain.
  - Extend each part issue body in `partition-input.txt` with `**Firm headings**`, `**Acceptance**`, and placeholder `larch:plan` noting operator must run `/design` on each filed piece before `/implement` (per `decompose-panel.md`).

### UPDATED: skills/design/scripts/decompose-prompts/_common-tail.txt
- Extend required output schema with `- firm-headings:` and `- acceptance:` bullets under each `### Piece N:` (match `aggregate_partition` merge prompt and `decompose-panel.md`).

### UPDATED: skills/design/SKILL.md
- Step 2b.5 `_postplan_rc=12` (initial site) and `postplan-rc12-split` drafter dispatch: Split / Override / Cancel (was Split / Cancel on initial/rc12). On Override: `plan set-oversize-override --design-tmpdir "$DESIGN_TMPDIR"`, `rm -f "$DESIGN_TMPDIR/composed-plan.md"`, then `design step2b-postplan --write-completion-only`, continue to Step 3.
- Step 2b drafter trailer-grammar note: document optional `oversize_override: operator` in the final metadata block.
- Step 5c shared validator failure: insert oversize special case **before** the review-provenance block, keyed on `PUBLISH_REFUSE_REASON=oversize-no-override` or `size-check-failed` from `.design-publish-result.env`. Offer Decompose (Split-path) / Override / Cancel. Override: `plan set-oversize-override` on `plan.txt`, `rm -f "$DESIGN_TMPDIR/composed-plan.md"`, then re-run `design-step5c.sh` (recompose only). Fail-closed under `--skip-approve`.

### UPDATED: skills/design/references/step2b5-rc-handling.md
- §1 `hard-trigger`: initial Step 2b, discussion merged, and `postplan-rc12-split` callers offer Split / Override / Cancel. **Every Override** invokes `plan set-oversize-override` on `plan.txt`, deletes `composed-plan.md`, then `design step2b-postplan --write-completion-only`. Retained callers unchanged prompt shape but same Override write + compose-delete requirement.
- Add `FIRM_HEADINGS`, `SURFACES_TOUCHED`, `OVERSIZE_OVERRIDE` to the direct-entry KV allowlist.

### UPDATED: skills/design/references/settle-rc-dispatch.md
- `gate-b-hard-size` row: Override invokes `plan set-oversize-override` on `plan.txt`, deletes `composed-plan.md`, then `design step2b-postplan --write-completion-only` (mirror initial Step 2b.5).

### UPDATED: skills/design/references/approval-gates.md
- Gate B hard-trigger Split / Override / Cancel: Override calls `plan set-oversize-override`, deletes `composed-plan.md`, then completion write.
- Optional trailer guard (step 1): snapshot/dedup keys include `oversize_override` alongside `diff_added`, `diff_deleted`, `mechanical_churn`; document the fourth key in the prose.

### UPDATED: skills/design/references/finalize-step5.md
- Before the review-provenance special case (`VALIDATE_LOG_FILE` empty, `VALIDATE_MISSING_SCRIPT_COUNT` 0): when `PUBLISH_REFUSE_REASON=oversize-no-override` or `size-check-failed`, route to Decompose (Split-path) / Override (`plan set-oversize-override` on `plan.txt`, delete `composed-plan.md`, re-run `design-step5c.sh`) / Cancel. Keep SKILL.md and this file in sync.

### UPDATED: skills/design/scripts/check-plan-size.md
- Document new keys, thresholds, reason tokens, surface definition, override suppression, `PLAN_SIZE_STATUS`, `PUBLISH_REFUSE_REASON` values, and expanded "Edit in sync" list (`config.py`, `design_publish.py`, `design_step5c.py`, `design_step2b.py`, `plan_review_common.py`, `difficulty.py`, `bootstrap.py`, `preflight.py`, `docs/issue-anchored-plan.md`).

### UPDATED: skills/design/references/flags.md
- Extend plan-size thresholds section with firm-heading and surfaces triggers, config constant names, `oversize_override` suppression, and the three new machine-output keys.

### UPDATED: docs/issue-anchored-plan.md
- Document plan-size signals, thresholds, `oversize_override: operator` trailer position and preservation, Step 5c finalization guard (`plan.txt` authoritative; composed recompose after Override), split-path per-piece firm-heading / acceptance scaffolds, serial blocked-by semantics, and tolerant readers for plans without the trailer (G-Wire-2).

### UPDATED: skills/design/references/decompose-panel.md
- Require per-piece `- firm-headings:` inventory and `- acceptance:` criteria in partition proposal bodies (panel prompts and aggregator output).
- Document prepare fallbacks, `missing-piece-metadata` refusal, serial adjacent blocked-by TSV, and that each filed part requires its own `/design` → Gate C approval before `[DESIGNED]` / `/implement` (no auto-chain).

### UPDATED: python/tests/design/test_plan_quality.py
- `parse_optional_metadata`: `oversize_override: operator` without truncating trailers above it; absent yields None; malformed value stops block.
- `check_plan_size_main`: firm-heading/surface counting, config thresholds, override suppression, new keys always emitted, `PLAN_SIZE_STATUS=ok`.
- `set_oversize_override_main`: insert/remove/idempotent/guards.

### UPDATED: python/tests/design/test_design_publish.py
- Finalization guard on `plan.txt`: oversized without override → `return 4`, `PUBLISH_REFUSE_REASON=oversize-no-override`; check-size subprocess failure → `size-check-failed`; with override proceeds; under-threshold proceeds.
- `_OPTIONAL_TRAILER_RE` / provenance splice: `oversize_override` survives `_splice_plan_provenance`.

### UPDATED: python/tests/design/test_design_step5c.py
- `test_step5c_auto_compose_preserves_optional_trailers` (or equivalent): `oversize_override: operator` round-trips from `plan.txt` through auto-compose to `composed-plan.md`.
- Oversize refusal result-env path asserts `PUBLISH_REFUSE_REASON` in allow-keys output.
- Step 5c Override retry: after `set-oversize-override` + `composed-plan.md` delete + recompose, publish guard passes.

### UPDATED: python/tests/design/test_decompose.py
- `_common-tail` / aggregator schema fixture includes firm-headings and acceptance bullets.
- Oversized `plan.txt` fixture → `SIZE_TRIGGER_FIRED` / `hard-trigger` partition file → `prepare_partition_issues` emits per-part firm-heading inventory, acceptance criteria (panel and fallback paths), serial adjacent TSV `(1→2, 2→3, ...)`, and valid acyclic deps.
- `missing-piece-metadata` when scope matching leaves empty firm-headings or acceptance after fallback.
- Filed `partition-input.txt` scaffold includes placeholder `larch:plan` and acceptance prose readable by preflight metadata scan helpers.

### UPDATED: python/tests/calibration/test_difficulty.py
- Trailer-span case: plan text with `oversize_override: operator` still exposes `review_status` / `rounds_completed` / `difficulty` to `trailing_plan_metadata_lines`.

### UPDATED: python/tests/implement/test_preflight.py
- Metadata scan: `oversize_override: operator` present does not hide `review_status:` / `rounds_completed:` lines.

### MAY_UPDATE: python/tests/design/test_design_postplan.py
- Extend postplan KV-flow cases for firm-heading / surface-driven `rc=12` / `hard-trigger` and new keys in result env when passthrough assertions require it.

### MAY_UPDATE: python/tests/design/test_design_lifecycle.py
- Add `step2b5_next_action_for` case for firm-heading / surface-origin `SIZE_TRIGGER` if explicit coverage is wanted.

### MAY_UPDATE: python/tests/review/test_plan_review_gate_b.py
- Gate B optional-trailer snapshot round-trip with `oversize_override` in `.gate-b-optional-trailer-keys.values` when harness exists; only if current gate-b-dedup tests need extension.

## Edge cases
- `oversize_override: operator` must not break parsing of `diff_added:` / `mechanical_churn:` above it in any consumer (`parse_optional_metadata`, publish regex, auto-compose peel, difficulty span, bootstrap strip, preflight scan).
- Override must survive revise waterfall and Gate B rewrites via `OPTIONAL_KEYS` + `OPTIONAL_TRAILER_KEYS` + snapshot tests.
- Post-review growth caught at Gate B re-emit and Step 5c guard on `plan.txt`.
- MAY_UPDATE headings excluded from firm-heading and surface counts.
- `mechanical_churn` suppresses only the diff trigger; firm-heading / surface triggers still fire unless overridden.
- Every Override path deletes `composed-plan.md`; Step 5c recompose is the only rebuild path (no `--plan-file composed-plan.md` override write).
- `--skip-approve` cannot bypass Step 5c oversize or size-check refusal; Decompose / Override / Cancel still fires.
- Valid override on an under-threshold plan emits `OVERSIZE_OVERRIDE=operator` harmlessly.
- Prepare serial edges plus panel deps: extra panel edges allowed only when cycle check passes and every piece remains reachable from Piece 1.
- Split-filed parts remain `[DESIGNING]` until operator runs `/design` on each; prepare scaffold is not `[DESIGNED]`-ready.

## Failure modes
1. Trailer-parser regression drops existing size trailers. Signal: `test_plan_quality` preservation cases. Mitigation: recognition branch plus preservation test with `oversize_override` above other trailers.
2. Override not written or compose not deleted at a retained Override site. Signal: operator Override then Step 5c refusal or stale composed body. Mitigation: shared Override helper sequence (`set-oversize-override` + delete compose) at every site; integration test per site class.
3. Compose/publish drops override so Step 5c guard or `/implement` preflight loses provenance. Signal: auto-compose / splice / preflight tests. Mitigation: firm UPDATED sweep of all trailer regexes and Gate B snapshot keys.
4. Oversize refusal misrouted to review-provenance Fix-and-retry. Signal: `finalize-step5.md` / SKILL ordering tests with `PUBLISH_REFUSE_REASON`. Mitigation: branch before review-provenance on explicit KV including `size-check-failed`.
5. Split prepare emits thin part issues. Signal: `test_decompose` `missing-piece-metadata` and filed-body assertions. Mitigation: panel schema + deterministic fallbacks + fail-closed prepare status.
6. Publish guard fails open on check-size errors. Signal: `test_design_publish` subprocess-failure fixture. Mitigation: refuse unless `PLAN_SIZE_STATUS=ok` and `SIZE_TRIGGER_FIRED=false`.
7. Threshold too aggressive (`surfaces > 4`) false-positives. Mitigation: Override release valve; firm-heading count primary; calibration candidate noted in config.

## Testing strategy
- Unit: detector, parser, `set_oversize_override_main`, trailer regexes in publish/step5c/difficulty/bootstrap/preflight, prepare fallbacks and serial TSV.
- Integration: Step 5c finalization guard (oversize + check-size failure), refusal-to-override retry with compose delete, Gate B trailer snapshot, decompose prepare inventory, auto-compose round-trip, `postplan-rc12-split` Override contract.
- `make py-lint`, `make py-test`, and design harness shards (`test-check-plan-size`, `test-gate-b-apply-mode`, `test-design-structure.sh`) pass.

## Difficulty
HARD: multi-consumer plan-grammar change (new preserved trailer), fail-closed finalization guard with subprocess fail-closed semantics, Override + compose-delete wiring across every hard-trigger site including drafter/rc12, split-path prepare hardening with serial deps and metadata fallbacks, plus config / docs / SKILL sweeps. Contained by unchanged decompose panel dispatch and `step2b5_next_action_for` routing.

## Acceptance

- Unit: detector, parser, `set_oversize_override_main`, trailer regexes in publish/step5c/difficulty/bootstrap/preflight, prepare fallbacks and serial TSV.
- Integration: Step 5c finalization guard (oversize + check-size failure), refusal-to-override retry with compose delete, Gate B trailer snapshot, decompose prepare inventory, auto-compose round-trip, `postplan-rc12-split` Override contract.
- `make py-lint`, `make py-test`, and design harness shards (`test-check-plan-size`, `test-gate-b-apply-mode`, `test-design-structure.sh`) pass.

review_status: complete
rounds_completed: 2
difficulty: HARD
diff_added: 880
diff_deleted: 55
mechanical_churn: false
diff_lines: 1080
