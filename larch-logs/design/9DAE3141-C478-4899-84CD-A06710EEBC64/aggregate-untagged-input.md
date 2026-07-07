### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/design/decompose.py:97-191
- **Concern**: Partition prepare derives firm-heading inventory when panel bullets are absent but not acceptance criteria. Scenario: The plan requires `prepare_partition_issues` to parse optional `- acceptance:` bullets and only auto-derive `- firm-headings:` when absent. `test_decompose.py` is expected to assert acceptance criteria in filed part bodies, yet no step derives acceptance from the parent plan when the panel omits that bullet. Split part issues can land without per-part acceptance criteria, missing binding scope for decomposed serial issues.
- **Proposed resolution**: Add a fail-closed or deterministic fallback: derive per-piece acceptance from the parent plan (for example a scoped slice of Testing strategy / acceptance prose matched to the piece inventory), or return a prepare error when either bullet is missing after the aggregator contract update.

### FINDING_3:
- **Reviewer(s)**: Codex-Arch
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/design/design_step2b.py:412-436
- **Concern**: Step 2b still hard-codes the old trailer grammar. It only teaches `diff_added` / `diff_deleted` / `mechanical_churn`, and the `LARCH_PLAN_BEGIN` text still omits `oversize_override: operator`.. Scenario: The actual plan-drafting prompt can keep emitting the pre-change format, so oversized plans never get the new override trailer and the guardrail cannot be exercised end to end.
- **Proposed resolution**: Add `python/larch/design/design_step2b.py` to the UPDATED list and extend both prompt strings to mention `oversize_override: operator` as an allowed trailer before `diff_lines:`.

### FINDING_4:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/design/design_publish.py
- **Concern**: The Step 5c publish oversize guard only refuses when SIZE_TRIGGER_FIRED=true. Scenario: If plan check-size exits non-zero or emits PLAN_SIZE_STATUS=missing-diff-lines/missing-plan/invalid-mechanical-churn, publish_core could still write the plan block because SIZE_TRIGGER_FIRED stays false, defeating the fail-closed finalization guard after a corrupted or hand-edited plan.txt
- **Proposed resolution**: In publish_core, treat plan check-size subprocess non-zero exit or any PLAN_SIZE_STATUS other than a successful ok path as publish refusal (return 4 with PUBLISH_REFUSE_REASON=oversize-no-override or a distinct size-check-failed KV) before named-block write; only treat SIZE_TRIGGER_FIRED=false as pass when check-size succeeded

### FINDING_5:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: minor
- **Focus area**: correctness
- **Location**: python/larch/design/plan_quality.py
- **Concern**: Firm-heading and surface counts are not tied to Files-section firm scope. Scenario: The plan adds standalone _firm_heading_count/_plan_surfaces scans over the whole plan body, which can diverge from issue_wire.extract_scope_paths(..., use_fallback=False, include_optional=False) used for implement coverage; prose or example ### NEW:/UPDATED: lines outside Files to modify/create could inflate counts and false-trigger hard size while the one-shot implementer contract stays smaller
- **Proposed resolution**: Derive firm paths via extract_scope_paths (or shared helper with the same heading regex, section bounds, and backtick stripping); count firm headings and distinct surfaces from that path list only, excluding MAY_UPDATE

### FINDING_6:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: major
- **Focus area**: correctness
- **Location**: plan.txt:14-15,75-76
- **Concern**: Override updates only plan.txt; composed-plan.md can stay stale. Scenario: After a Step 2b.5 or Gate B Override, `design_step5c.py` will skip auto-compose when `composed-plan.md` already exists, so `publish_core` can pass the new size guard on `plan.txt` and still publish an old composed plan that lacks `oversize_override: operator`.
- **Proposed resolution**: Make every Override path delete `composed-plan.md` or rewrite it immediately before continuing, not only the Step 5c recovery branch.

### FINDING_7:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: major
- **Focus area**: correctness
- **Location**: plan.txt:15,75
- **Concern**: Step 5c docs allow an in-place composed-plan retry even though the guard checks plan.txt. Scenario: The documented `--plan-file "$DESIGN_TMPDIR/composed-plan.md"` retry path does not touch `plan.txt`, so the next `plan check-size --plan-file "$DESIGN_TMPDIR/plan.txt"` still sees the plan as oversized and refuses finalization.
- **Proposed resolution**: Remove the in-place composed-plan alternative, or make the retry path update `plan.txt` too and keep the authoritative guard/file pair aligned.

### FINDING_8:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Focus area**: code-quality
- **Location**: skills/design/scripts/decompose-prompts/_common-tail.txt
- **Concern**: Decompose panel output schema omits firm-headings and acceptance bullets. Scenario: The plan only updates decompose-panel.md and prepare_partition_issues. Archetype prompts still require Scope/Dependencies/Diff_lines only, and aggregate_partition hardcodes the same schema in decompose.py. Panel output will omit - firm-headings: and - acceptance:, so prepare cannot reliably populate per-part inventories required by acceptance criterion 1.
- **Proposed resolution**: Add ### UPDATED: skills/design/scripts/decompose-prompts/_common-tail.txt and extend the aggregate_partition merge schema in python/larch/design/decompose.py (lines 605-611) with - firm-headings: and - acceptance: bullets; keep decompose-panel.md in sync.

### FINDING_9:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Focus area**: code-quality
- **Location**: python/larch/design/decompose.py
- **Concern**: prepare_partition_issues has no acceptance fallback when panel omits it. Scenario: The plan derives firm-heading inventories when - firm-headings: is absent but never defines acceptance derivation. Partition-input bodies can ship without per-part acceptance criteria, failing acceptance criterion 1 even when Split-path succeeds.
- **Proposed resolution**: Specify acceptance fallback in prepare_partition_issues (for example slice Testing strategy bullets for in-scope firm headings, or a bounded default tied to each piece scope) and pin it in python/tests/design/test_decompose.py.

### FINDING_10:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/design/decompose.py
- **Concern**: Firm-heading to piece scope matching is unspecified. Scenario: Scope lines are free text while firm headings are concrete paths. Without a normative match rule (prefix/path equality via shared extract_scope_paths), derived inventories can be empty or wrong and acceptance criterion 1 tests become flaky.
- **Proposed resolution**: Reuse issue_wire.extract_scope_paths(..., include_optional=False) for the parent plan; match each heading to a piece when it equals or is under a scope path token; document the rule in prepare_partition_issues and test_decompose.py.

### FINDING_11:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: minor
- **Focus area**: correctness
- **Location**: python/larch/design/plan_quality.py
- **Concern**: optional-trailers parse extension is listed under the wrong file. Scenario: The plan puts optional-trailers parse CLI changes under _plan_quality_commands.py, but optional_trailers_main and the parse subcommand live in plan_quality.py. Implementers may update the dataclass only and omit CLI output/metadata_trailer_lines wiring.
- **Proposed resolution**: Move the parse CLI bullet to plan_quality.py optional_trailers_main (emit oversize_override, extend metadata_trailer_lines), keeping OptionalMetadata/OPTIONAL_KEYS in _plan_quality_commands.py. ### 1. [completeness] Decompose panel prompts missing from plan (`skills/design/scripts/decompose-prompts/_common-tail.txt`, `python/larch/design/decompose.py:605-611`) The plan updates `decompose-panel.md` and `prepare_partition_issues`, but the runtime panel contract is `_common-tail.txt` plus the inline aggregator schema in `aggregate_partition`. Those still require only Scope, Dependencies, and Diff_lines. Without prompt-schema updates, reviewers will not emit `- firm-headings:` or `- acceptance:`, so prepare cannot satisfy acceptance criterion 1. **Suggested revision:** Add `_common-tail.txt` and the `aggregate_partition` schema to **Files to modify**, mirroring prior decompose grammar changes. ### 2. [completeness] No acceptance fallback in `prepare_partition_issues` (`python/larch/design/decompose.py`) The plan defines a firm-heading fallback but not an acceptance fallback. Part issues can be filed with inventories only and no acceptance criteria, which breaks the stated acceptance criterion. **Suggested revision:** Define and test acceptance derivation when the panel omits `- acceptance:` (for example from Testing strategy text scoped to each piece). ### 3. [correctness] Underspecified firm-heading ↔ scope matching (`python/larch/design/decompose.py`) Piece `- scope:` values are prose; firm headings are paths. Without a shared matching rule, derived inventories may be empty for realistic partitions. **Suggested revision:** Reuse `issue_wire.extract_scope_paths` and a documented prefix/equality rule; pin edge cases in `test_decompose.py`. ### 4. [correctness] Wrong file for optional-trailers parse CLI (`python/larch/design/plan_quality.py`) `optional_trailers_main` lives in `plan_quality.py`, not `_plan_quality_commands.py`. The plan’s file attribution risks an incomplete trailer round-trip. **Suggested revision:** Target `plan_quality.py` for parse CLI and `metadata_trailer_lines` updates. --- **[OUT_OF_SCOPE]** `skills/design/references/step2b5-rc-handling.md:20` — Hard-trigger operator display still omits `FIRM_HEADINGS` / `SURFACES_TOUCHED`; worth a doc-only follow-up, not blocking. **[OUT_OF_SCOPE]** `skills/design/references/approval-gates.md:143` — Gate B prose still lists legacy line/diff thresholds only; update when touching that file for Override wiring. **[OUT_OF_SCOPE]** `python/larch/design/plan_quality.py:979-980` — Revise-waterfall prompt still names three optional trailers; model-facing polish after `oversize_override` lands. Prior-round accepted items (Override wiring, `plan.txt` publish guard, trailer consumer sweep, Step 5c recovery, `PUBLISH_REFUSE_REASON` routing) appear addressed in the current plan; the gaps above are additive.

### FINDING_12:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: major
- **Focus area**: correctness
- **Location**: skills/design/scripts/decompose-prompts/_common-tail.txt:23-34
- **Concern**: Prior FINDING_8 fix is incomplete: the plan updates decompose.py and decompose-panel.md, but not the common prompt schema that panel-dispatch actually expands for decomposition reviewers.. Scenario: Split-path reviewers still see the old schema with only Scope, Dependencies, Diff_lines, and Why independently mergeable. They will usually omit per-piece firm-heading inventory and acceptance criteria, so prepare_partition_issues cannot emit the required per-part acceptance criteria into filed part issues.
- **Proposed resolution**: Add skills/design/scripts/decompose-prompts/_common-tail.txt as a firm UPDATED file and extend its required Piece schema with firm-headings and acceptance bullets, matching decompose.py and decompose-panel.md.

### FINDING_13:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:301
- **Concern**: The drafter hard-trigger path still omits Override. Scenario: The plan adds Split / Override / Cancel for inline `_postplan_rc=12`, but the default Step 2b drafter path still dispatches `DRAFTER_NEXT_ACTION=postplan-rc12-split` with Split / Cancel only. An oversized drafter plan cannot record `oversize_override: operator` and must decompose or cancel.
- **Proposed resolution**: Add `skills/design/SKILL.md` `postplan-rc12-split` handling (and any drafter-sidecar prompt text) to the same Split / Override / Cancel contract: on Override call `plan set-oversize-override` on `plan.txt`, then continue per `step2b5-rc-handling.md`.

### FINDING_14:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: minor
- **Focus area**: correctness
- **Location**: python/larch/design/plan_quality.py:201-258
- **Concern**: The plan threads `oversize_override` into `keys` but not the `values` tuple. Scenario: `optional-trailers snapshot-values` / `validate-values` and `validate_optional_trailers_preserved` compare `meta.values` to `.gate-b-optional-trailer-keys.values`. Keys-only wiring lets Gate B snapshots include `oversize_override=operator` while value validation still fails or passes incorrectly after review rewrites.
- **Proposed resolution**: In `parse_optional_metadata`, add `oversize_override` to both `keys` and `values` (`oversize_override=operator`), and extend `test_plan_quality.py` optional-trailer snapshot/validate cases accordingly.

### FINDING_15:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: minor
- **Focus area**: correctness
- **Location**: python/larch/design/plan_quality.py:428-559
- **Concern**: Plan omits threshold KVs from plan-quality output. Scenario: The acceptance criteria require size signals and thresholds in plan-quality output, but the proposed check-size changes emit counts, reasons, and OVERSIZE_OVERRIDE only; a run cannot machine-verify which calibrated limits were applied.
- **Proposed resolution**: Add explicit threshold output keys for the configured limits and thread them through postplan/result-env allowlists, docs, and tests where size KVs are presented.

### FINDING_16:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/design/decompose.py:97-184
- **Concern**: Split path still files part issues without implement-admissible per-part plans. Scenario: The proposed decompose update adds inventories and acceptance text, but it leaves the existing issue-body shape that embeds a placeholder larch:plan and no per-part review_status/rounds_completed or designed admission state; /implement on a filed part either fails admission or consumes an unreviewed stub, violating the part-issue acceptance criteria.
- **Proposed resolution**: Update the Split path workflow to generate and review each per-part plan through the normal approval provenance path before marking parts implement-ready; tests should assert each filed part has a valid larch:plan block and unchanged preflight-readable metadata.

### FINDING_17:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/design/decompose.py:126-167
- **Concern**: Partition dependencies are only acyclic, not serial. Scenario: The plan keeps the existing panel dependency graph and tests only no-cycle behavior; a chosen partition with independent pieces writes no blocked-by chain, so multiple part issues can be implemented in parallel despite the issue requiring serial part issues with native blocked-by edges.
- **Proposed resolution**: Treat partition order as execution order or topologically sort it, then emit adjacent blocked-by edges for every Part N to depend on Part N-1; keep extra panel dependencies only if they do not break the serial chain and pin the TSV in tests.
