### FINDING_1: Drafter launchers still call deleted scout filter wrapper
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Codex-Innovation, Cursor-Pragmatic, Codex-Pragmatic, Codex-Requirements, Cursor-dyn-wire-parity, Codex-dyn-wire-parity, Cursor-dyn-retirement-sweep
- **Severity**: important
- **Concern**: The plan deletes `skills/design/scripts/scout-plan-archetypes-wrapper.sh` but omits cutover for the only production `--filter-manifest` callers in `scripts/launch-codex-drafter.sh` and `scripts/launch-claude-drafter.sh`. After deletion, Step 2b drafter scout filtering fails or is silently swallowed (`2>/dev/null || true`), so `scout-plan-manifest.json` is not materialized and Step 3 dynamic plan-review slots stay empty.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add UPDATED entries for scripts/launch-codex-drafter.sh and scripts/launch-claude-drafter.sh: replace the wrapper call with python3 "$PLUGIN_ROOT/python/cli.py" scout filter-manifest; preserve exit-0 filter mode, SCOUT_STATUS KV parsing, parse-failed gating, and 2>/dev/null|| true swallowing at the launcher
  - From Cursor-Innovation: Add ### UPDATED entries for scripts/launch-codex-drafter.sh and scripts/launch-claude-drafter.sh (and launch-claude-drafter.md) replacing the wrapper with python3 "$PLUGIN_ROOT/python/cli.py" scout filter-manifest, preserving SCOUT_STATUS gating and jq validation.
  - From Codex-Innovation: Add UPDATED entries for both launchers and replace the filter command with python3 "$PLUGIN_ROOT/python/cli.py" scout filter-manifest ... while preserving SCOUT_STATUS parsing and output move semantics
  - From Cursor-Pragmatic: Add UPDATED entries for scripts/launch-codex-drafter.sh and scripts/launch-claude-drafter.sh calling python3 cli.py scout filter-manifest with the same || true capture and SCOUT_STATUS parse-failed gating as today
  - From Codex-Pragmatic: Add UPDATED sections for both drafter launchers and replace the wrapper calls with python3 "$PLUGIN_ROOT/python/cli.py" scout filter-manifest "$candidate" "$filtered" --max-archetypes 3, preserving SCOUT_STATUS parsing and fallback behavior.
  - From Codex-Requirements: add UPDATED sections for both drafter launchers and replace the filter calls with python3 "$PLUGIN_ROOT/python/cli.py" scout filter-manifest, preserving status parsing
  - From Cursor-dyn-wire-parity: Add `### UPDATED:` entries for `scripts/launch-codex-drafter.sh` and `scripts/launch-claude-drafter.sh` calling `python3 "$PLUGIN_ROOT/python/cli.py" scout filter-manifest` with the same stdout `SCOUT_STATUS` parsing (`parse-failed` only fails) and stderr suppression contract as today.
  - From Codex-dyn-wire-parity: Add UPDATED sections for both launchers and replace the wrapper call with python3 "$PLUGIN_ROOT/python/cli.py" scout filter-manifest INPUT OUTPUT --max-archetypes 3 while preserving SCOUT_STATUS parsing, scout-plan-manifest.json, and filter_failed behavior
  - From Cursor-dyn-retirement-sweep: Add ### UPDATED entries for scripts/launch-codex-drafter.sh and scripts/launch-claude-drafter.sh calling python3 "$PLUGIN_ROOT/python/cli.py" scout filter-manifest; update scripts/launch-claude-drafter.md prose


### FINDING_2: make lint harnesses still exec or copy retired scout / scope-anchor scripts
- **Reviewer(s)**: Codex-Requirements, Cursor-dyn-retirement-sweep
- **Severity**: important
- **Concern**: The plan deletes retired scout and scope-anchor bash scripts but omits offline harness callers that still `exec` or copy them. After deletion, `make lint` / harness shards fail on missing `scout-dynamic-archetypes.sh` or `lib-scope-anchor-handoff.sh`, and scope-anchor relay coverage in dispatch/plan-review tests breaks unless stubs are retargeted.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Add UPDATED coverage for these existing harnesses, and any make lint-retired-scripts hits they expose, so they use the new Python CLI surface or local stubs instead of retired paths
  - From Cursor-dyn-retirement-sweep: Update both harnesses to stub scope-anchor via python/cli.py or inline minimal relay helpers; add explicit ### UPDATED harness rows


### FINDING_4: Stale `$PLAN_REVIEW_SCOUT_SH` cutover bullet in plan-review-loop.sh
- **Reviewer(s)**: Cursor-dyn-wire-parity
- **Severity**: important
- **Concern**: The plan tells implementers to rewire `$PLAN_REVIEW_SCOUT_SH`, but production `plan-review-loop.sh` no longer invokes a scout subprocess. Implementing that bullet can reintroduce a removed Step 3 scout launch or add dead env wiring; dynamic archetypes now come from Step 2b drafter output consumed by `dispatch-plan-review-panel.sh`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-wire-parity: Remove the `$PLAN_REVIEW_SCOUT_SH` bullet from the `plan-review-loop.sh` cutover; limit that file to findings-header and scope-anchor CLI replacements only.


### FINDING_5: scope-anchor relay CLI must pin relay-gate status inputs
- **Reviewer(s)**: Cursor-dyn-wire-parity
- **Severity**: important
- **Concern**: The plan adds `scope-anchor relay-allowed` / `design-handoff` / `retally-handoff` verbs but does not pin relay-gate inputs. Sourced helpers read in-process `TALLY_PLAN_REVIEW_STATUS` and `LOOP_STATUS`; a subprocess CLI that omits them or only reads the environment will always deny relay and drop `SCOPE_ANCHOR_FILE` on `run-step3-review.sh` and `persist-retally-step3-env.sh` paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-wire-parity: Specify that relay-allowed, design-handoff, and retally-handoff accept `--tally-plan-review-status` and `--loop-status` (mirroring persist-retally argv) and apply the same `ok|main-agent-vote-required` + `complete|main-agent-vote-required` gate before emitting a canonical path.


### FINDING_7: `render scope-anchor` must enforce `DESIGN_TMPDIR` containment
- **Reviewer(s)**: Cursor-dyn-wire-parity
- **Severity**: important
- **Concern**: The `render scope-anchor` cutover does not state the `DESIGN_TMPDIR` containment requirement. The bash helper rejects anchors outside `$DESIGN_TMPDIR`; if the Python renderer only checks readability, MainAgent voting can read arbitrary host files when `SCOPE_ANCHOR_FILE` is poisoned.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-wire-parity: Require `render scope-anchor` to take `--design-tmpdir` (or equivalent) and enforce the same canonical under-tmpdir check before redact/escape output.


### FINDING_9: aggregate-findings.sh still sources deleted lib-scope-anchor-handoff
- **Reviewer(s)**: Cursor-dyn-retirement-sweep
- **Severity**: important
- **Concern**: The plan only swaps the validate call in aggregate-findings, not the `source` line. `skills/review/scripts/aggregate-findings.sh` still sources `scripts/lib-scope-anchor-handoff.sh`; after deletion the `/review` aggregate path fails at startup.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-retirement-sweep: Remove the source; call python3 cli.py scope-anchor validate --mode review from validate_scope_anchor_file only


### FINDING_11: relevant-checks.sh edit-trigger map still keys on deleted lib
- **Reviewer(s)**: Cursor-dyn-retirement-sweep
- **Severity**: important
- **Concern**: Edit-trigger map still keys on deleted `lib-scope-anchor-handoff.sh`. After the lib is removed, edits to `python/rendering.py` scope-anchor logic no longer auto-run `test-plan-review-loop`, `test-run-step3-review`, or scope-anchor pytest.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-retirement-sweep: Add a case for python/rendering.py (and/or python/test_rendering.py) that appends the same make/pytest targets instead of the retired scripts/lib-scope-anchor-handoff.sh path


### FINDING_12: Stale-reference sweep omits tracked literals and contract docs
- **Reviewer(s)**: Cursor-dyn-retirement-sweep, Codex-dyn-retirement-sweep
- **Severity**: important
- **Concern**: Stale-reference sweep is incomplete beyond files already listed. Tracked docs, harnesses, and `scripts/relevant-checks.sh` still cite retired full paths (`scout-plan-archetypes-wrapper.sh`, `lib-scope-anchor-handoff.sh`, `decompose-panel-dispatch.sh`, `scout-dynamic-archetypes.sh`, etc.). After rows land in `python/migrated-scripts.tsv`, `make lint-retired-scripts` cannot pass and several harnesses still copy or exec deleted scripts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-retirement-sweep: Expand the doc sweep to these sibling .md files (and plan-review.md decompose line ~240) with Python CLI authority strings
  - From Codex-dyn-retirement-sweep: Add these files to the stale-reference update set and remove, repoint, or build the retired path literals at runtime only where a test fixture needs them.


### FINDING_14: Shared `validate_dynamic_manifest` must preserve caller-specific reserved slug sets
- **Reviewer(s)**: Codex-dyn-scout-security
- **Severity**: important
- **Concern**: The `validate_dynamic_manifest` plan does not preserve caller-specific reserved slug sets. Using one shared reserved list either lets plan-review accept arch/innovation/pragmatic/requirements dynamic slugs or makes `/review` reject currently valid slugs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-scout-security: Add a mode or reserved_slugs parameter and test security rejected for /review while arch is rejected only for plan-review


### FINDING_15:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/design/scripts/plan-review-loop.sh:17-22; skills/design/scripts/test-plan-review-loop.sh:1179-1185
- **Concern**: [SCOPE-REDUCTION] Plan-review-loop scout cutover targets a stale/nonexistent hook. Scenario: The plan says to change a PLAN_REVIEW_SCOUT_SH default in plan-review-loop, but current plan-review-loop has no scout hook and the harness asserts review rounds must not call the scout wrapper; adding or preserving that path would change behavior in a pure port
- **Proposed resolution**: Remove the plan-review-loop scout bullet. Keep plan-review-loop changes to findings-header and scope-anchor CLI cutover, and cut over the actual scout/filter call sites in the drafter scripts and review dispatch paths.


### FINDING_16:
- **Reviewer(s)**: Codex-dyn-wire-parity
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/design/scripts/test-plan-review-loop.sh:1178-1185; skills/design/scripts/dispatch-plan-review-panel.sh:298-324
- **Concern**: [SCOPE-REDUCTION] Plan asks to cut over a PLAN_REVIEW_SCOUT_SH default in plan-review-loop even though current loop must not invoke scout. Scenario: The existing test asserts the scout wrapper is not called during review rounds; dynamic plan archetypes are consumed from $DESIGN_TMPDIR/scout-plan-manifest.json by dispatch-plan-review-panel.sh, so adding a Python scout call here would reintroduce duplicate per-round scout orchestration
- **Proposed resolution**: Drop the plan-review-loop scout-default bullet; keep loop changes limited to findings header and scope-anchor CLI cutover, and route scout wrapper/filter call-site work to the drafter launchers and dispatch-panel consumer




### FINDING_1: PLUGIN_ROOT fallback keyed on deleted scope-anchor library
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: `PLUGIN_ROOT` fallback is keyed on `lib-scope-anchor-handoff.sh` file presence. After the bash library is deleted, both `plan-review-loop.sh` (lines 11–16) and `run-step3-review.sh` (lines 165–167) always take the `REPO_ROOT` fallback branch, changing plugin-root resolution in harness and consumer checkouts versus today when the sourced file exists under `CLAUDE_PLUGIN_ROOT`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Remove or replace the lib-scope-anchor-handoff.sh existence OR-check when cutting over to python/cli.py scope-anchor; resolve PLUGIN_ROOT the same way as other post-migration design scripts without depending on a retired path


### FINDING_2: plan-review-loop.sh incomplete sh-to-py cutover leaves runtime call sites
- **Reviewer(s)**: Cursor-Innovation, Cursor-Requirements
- **Severity**: important
- **Concern**: The plan only replaces sourcing `lib-findings-classification.sh`, but `plan-review-loop.sh` still calls `emit_findings_classification_header` at lines 283 and 1790, still uses `larch_scope_anchor_design_handoff_value` / scope-anchor handoff helpers (lines 235–238), and still retains the `lib-scope-anchor-handoff.sh` existence guard and source (lines 14–43). After the bash helpers are deleted, `write_empty_review_artifacts` and the tally-error path invoke undefined functions and Step 3 aborts on zero-findings or tally-error rounds; `make test-plan-review-loop` breaks.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Expand the plan-review-loop.sh cutover: drop the lib-scope-anchor existence check; replace both header emissions with python/cli.py voting findings-classification-header; replace design handoff with python/cli.py scope-anchor design-handoff plus explicit --tally-plan-review-status and --loop-status
  - From Cursor-Requirements: After the bash helper is deleted, write_empty_review_artifacts and the tally-error path call an undefined function and Step 3 aborts on zero-findings or tally-error rounds Replace every emit_findings_classification_header redirect with python3 "$PLUGIN_ROOT/python/cli.py" voting findings-classification-header (same pattern as tally-plan-review.sh)


### FINDING_3: tally-plan-review.sh still writes classification headers via deleted helper
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: The plan only replaces the `lib-findings-classification` source, not direct header writes. `tally-plan-review.sh` still calls `emit_findings_classification_header` at lines 121 and 420 after the library is deleted; classification TSV creation fails and `make test-tally-plan-review` breaks.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Add tally-plan-review.sh to Files to modify/create: route both header writes through python/cli.py voting findings-classification-header (or a shared shell helper that wraps that verb)


### FINDING_6: Harnesses still copy deleted lib-scope-anchor-handoff.sh
- **Reviewer(s)**: Cursor-Innovation, Cursor-Pragmatic
- **Severity**: important
- **Concern**: Multiple harnesses still copy `scripts/lib-scope-anchor-handoff.sh`. After deletion, `cp` fails before panel/voter assertions run: `skills/design/scripts/test-dispatch-plan-review-panel.sh` (line 420) and `scripts/test-dispatch-plan-voters.sh` (line 141). `make test-dispatch-plan-review-panel` and `make test-dispatch-plan-voters` break even though the dispatched scripts under test do not source that library.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation, Cursor-Pragmatic: Add test-dispatch-plan-review-panel.sh to the cutover list: remove the lib-scope-anchor copy (or stub python/cli.py scope-anchor if a downstream test still needs it)
  - From Cursor-Innovation: Update scripts/test-dispatch-plan-voters.sh in the stale-reference / harness sweep


### FINDING_7: plan-review.md still references deleted decompose-panel-dispatch.sh
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: The `plan-review.md` update list omits the decompose bash authority at line 240. After `decompose-panel-dispatch.sh` is deleted, line 240 still names that script; operators and `lint-retired-scripts` may miss it because only scout/scope-anchor edits are specified.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Extend the plan-review.md delta to retarget the Split-path decompose reference to python/cli.py decompose panel-dispatch (same as decompose-panel.md)

---

**Merge notes**

| Merged | Source IDs | Rationale |
|--------|------------|-----------|
| FINDING_2 | FINDING_2 + FINDING_9 | Same file, same failure mode: retired bash helpers leave undefined `emit_findings_classification_header` and scope-anchor calls in `plan-review-loop.sh`. |
| FINDING_6 | FINDING_6 + FINDING_7 | Same stale-harness pattern (`cp` of deleted `lib-scope-anchor-handoff.sh`), different files, same fix class. |

**Kept separate**

- **FINDING_1** vs **FINDING_2**: Arch’s PLUGIN_ROOT resolution risk (architectural, two files) is distinct from Innovation/Requirements’ runtime call-site cutover gaps in `plan-review-loop.sh`.
- **FINDING_3**: `tally-plan-review.sh` is a separate file with its own header-write sites.
- **FINDING_4**, **FINDING_5**, **FINDING_7**: Distinct Python ports, test seams, and doc surfaces.




### FINDING_7: run-step3-review.sh scope-anchor validate cutover omits --mode design
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Concern**: The plan cuts over `validate_design` to `scope-anchor validate` but does not pin `--mode design` the way `aggregate-findings --mode review` is pinned. An implementer may call scope-anchor validate without design mode or with wrong argv, so `validate_scope_anchor_handoff` / `recover_main_agent_scope_anchor` containment can diverge from `larch_scope_anchor_validate_design`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: In the run-step3-review.sh delta specify python3 ... scope-anchor validate --mode design --design-tmpdir "$DESIGN_TMPDIR" --path <file> and how canonical path is parsed back into SCOPE_ANCHOR_FILE




### FINDING_1: Review-mode scope-anchor validate omits containment argv
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation
- **Severity**: important
- **Concern**: The planned cutover to `scope-anchor validate --mode review` in `aggregate-findings.sh` drops the second argument that bash passes today (`$REVIEW_TMPDIR_CANON`). Without an explicit `--review-tmpdir` (or equivalent), review-mode validation cannot enforce under-root and tmp/cache allowlist checks, so valid session anchors may be rejected or paths outside the review session may be accepted.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: root containment check fails or is skipped after deleting `scripts/lib-scope-anchor-handoff.sh` Add `scope-anchor validate --mode review --review-tmpdir "$REVIEW_TMPDIR" --path <file>` to the `aggregate-findings.sh` cutover and document the same argv on the `scope-anchor validate` CLI in `python/rendering.py`
  - From Cursor-Innovation: Add review-mode CLI flags (e.g. `--review-tmpdir` + `--path`), implement parity in `python/rendering.py`, and wire `validate_scope_anchor_file` to pass `$REVIEW_TMPDIR_CANON`.


### FINDING_3: plan-review-loop.md still documents per-round scout invocation
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Concern**: The plan updates `plan-review-loop.sh` but not its sibling contract doc. `plan-review-loop.md` still documents per-round `$PLAN_REVIEW_SCOUT_SH` / `scout-plan-archetypes-wrapper.sh` invocation even though the loop no longer runs scout. After cutover, maintainers and harness authors may reintroduce per-round scout wiring or miss that dynamic slots come only from Step 2b drafter output consumed by `dispatch-plan-review-panel.sh`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Add ### UPDATED: skills/design/scripts/plan-review-loop.md: remove PLAN_REVIEW_SCOUT_SH argv prose; document drafter-produced scout-plan-manifest.json as the only dynamic manifest source for review rounds.

---

**Merge notes**: FINDING_1 and FINDING_2 from the input both target `aggregate-findings.sh:92-94` and the same missing `--review-tmpdir` containment contract; they were merged. FINDING_3 and FINDING_4 are distinct surfaces (relay gate vs contract doc) and remain separate.



### FINDING_1: `scout_plan_archetypes` omits `SCOUT_PLAN_ARCHETYPES_SCOUT_SH` harness override
- **Reviewer(s)**: Cursor-Arch, Cursor-Pragmatic
- **Severity**: important
- **Concern**: `scout_plan_archetypes` does not list the `SCOUT_PLAN_ARCHETYPES_SCOUT_SH` harness override seam that `scout-plan-archetypes-wrapper.sh` uses today (default `scripts/scout-dynamic-archetypes.sh` for the inner scout subprocess). The plan only documents `SCOUT_DYNAMIC_ARCHETYPES_*` seams used by `scout_dynamic_archetypes` itself. Porting without this seam breaks offline control of the inner launch path, breaks `test-scout-plan-archetypes-wrapper.sh` / documented override contract in `plan-review.md`, and can hide plan-archetypes-only regressions.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add `SCOUT_PLAN_ARCHETYPES_SCOUT_SH` to `scout_plan_archetypes` test seams and pytest coverage mirroring `skills/design/scripts/scout-plan-archetypes-wrapper.sh:282-286`.
  - From Cursor-Pragmatic: Add `SCOUT_PLAN_ARCHETYPES_SCOUT_SH` to the `scout_plan_archetypes` seam list (alongside the dynamic-archetypes launch overrides) and cover it in `python/test_plan_scout.py`.


### FINDING_3: Plan omits `scope-anchor design-handoff` argv for multi-candidate precedence
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Concern**: `plan-review-loop.sh` calls `larch_scope_anchor_design_handoff_value` with two candidates (`_PARSED_SCOPE_ANCHOR_FILE` then `_LOOP_SCOPE_ANCHOR_IN`) and relay gating. The plan only says to replace that helper with `scope-anchor design-handoff` and pass relay statuses, but does not define equivalent CLI flags or candidate ordering. A thin cutover can drop the second candidate or relay gating and emit the wrong `SCOPE_ANCHOR_FILE` in `.step3-plan-review-result.env`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Specify `scope-anchor design-handoff` argv mirroring the shell helper (e.g. `--design-tmpdir`, `--tally-plan-review-status`, `--loop-status`, ordered `--candidate` paths or `--parsed-path` / `--loop-input-path`), document first-match-wins semantics, and require `plan-review-loop.sh` to capture stdout into `_scope_anchor_handoff_value` the same way as today.



