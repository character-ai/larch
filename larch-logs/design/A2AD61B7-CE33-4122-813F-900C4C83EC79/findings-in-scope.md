### FINDING_1: Split path can emit non-implementable part issues
- **Reviewer(s)**: Cursor-Arch, Cursor-Pragmatic, Codex-Pragmatic, Codex-Requirements
- **Severity**: major
- **Concern**: The split/decompose path can still produce part issues that lack per-piece acceptance criteria, consistent scope matching, valid part-plan provenance, or serial blocked-by edges, so the filed pieces are not reliably implement-ready.
- **Suggested revisions (informational for voters; coder decides):**
  - From Cursor-Arch: Add a fail-closed or deterministic fallback: derive per-piece acceptance from the parent plan (for example a scoped slice of Testing strategy / acceptance prose matched to the piece inventory), or return a prepare error when either bullet is missing after the aggregator contract update.
  - From Cursor-Pragmatic: Add ### UPDATED: skills/design/scripts/decompose-prompts/_common-tail.txt and extend the aggregate_partition merge schema in python/larch/design/decompose.py (lines 605-611) with - firm-headings: and - acceptance: bullets; keep decompose-panel.md in sync.
  - From Cursor-Pragmatic: Specify acceptance fallback in prepare_partition_issues (for example slice Testing strategy bullets for in-scope firm headings, or a bounded default tied to each piece scope) and pin it in python/tests/design/test_decompose.py.
  - From Cursor-Pragmatic: Reuse issue_wire.extract_scope_paths(..., include_optional=False) for the parent plan; match each heading to a piece when it equals or is under a scope path token; document the rule in prepare_partition_issues and test_decompose.py.
  - From Codex-Pragmatic: Add skills/design/scripts/decompose-prompts/_common-tail.txt as a firm UPDATED file and extend its required Piece schema with firm-headings and acceptance bullets, matching decompose.py and decompose-panel.md.
  - From Codex-Requirements: Update the Split path workflow to generate and review each per-part plan through the normal approval provenance path before marking parts implement-ready; tests should assert each filed part has a valid larch:plan block and unchanged preflight-readable metadata.
  - From Codex-Requirements: Treat partition order as execution order or topologically sort it, then emit adjacent blocked-by edges for every Part N to depend on Part N-1; keep extra panel dependencies only if they do not break the serial chain and pin the TSV in tests.

### FINDING_2: Oversize override is missing from the drafting contract
- **Reviewer(s)**: Codex-Arch, Cursor-Requirements
- **Severity**: major
- **Concern**: The oversized-plan override contract is not fully exposed through the Step 2b drafter/prompt path, so operator override cannot be selected or recorded consistently.
- **Suggested revisions (informational for voters; coder decides):**
  - From Codex-Arch: Add python/larch/design/design_step2b.py to the UPDATED list and extend both prompt strings to mention `oversize_override: operator` as an allowed trailer before `diff_lines:`.
  - From Cursor-Requirements: Add `skills/design/SKILL.md` `postplan-rc12-split` handling (and any drafter-sidecar prompt text) to the same Split / Override / Cancel contract: on Override call `plan set-oversize-override` on `plan.txt`, then continue per `step2b5-rc-handling.md`.

### FINDING_3: Publish gating can fail open on stale or invalid composed plans
- **Reviewer(s)**: Cursor-Innovation, Codex-Innovation
- **Severity**: major
- **Concern**: The Step 5c publish flow can still finalize a stale or oversized composed plan when size checks fail or when plan.txt and composed-plan.md diverge.
- **Suggested revisions (informational for voters; coder decides):**
  - From Cursor-Innovation: In publish_core, treat plan check-size subprocess non-zero exit or any PLAN_SIZE_STATUS other than a successful ok path as publish refusal (return 4 with PUBLISH_REFUSE_REASON=oversize-no-override or a distinct size-check-failed KV) before named-block write; only treat SIZE_TRIGGER_FIRED=false as pass when check-size succeeded
  - From Codex-Innovation: Make every Override path delete `composed-plan.md` or rewrite it immediately before continuing, not only the Step 5c recovery branch.
  - From Codex-Innovation: Remove the in-place composed-plan alternative, or make the retry path update `plan.txt` too and keep the authoritative guard/file pair aligned.

### FINDING_4: Plan-size and trailer metadata wiring is incomplete
- **Reviewer(s)**: Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements, Codex-Requirements
- **Severity**: major
- **Concern**: Plan-size accounting and trailer metadata are not fully scoped or threaded, so the reported size signals and optional trailer state can be inaccurate or unmachineverifiable.
- **Suggested revisions (informational for voters; coder decides):**
  - From Cursor-Innovation: Derive firm paths via extract_scope_paths (or shared helper with the same heading regex, section bounds, and backtick stripping); count firm headings and distinct surfaces from that path list only, excluding MAY_UPDATE
  - From Cursor-Pragmatic: Move the parse CLI bullet to plan_quality.py optional_trailers_main (emit oversize_override, extend metadata_trailer_lines), keeping OptionalMetadata/OPTIONAL_KEYS in _plan_quality_commands.py.
  - From Cursor-Requirements: In parse_optional_metadata, add `oversize_override` to both `keys` and `values` (`oversize_override=operator`), and extend `test_plan_quality.py` optional-trailer snapshot/validate cases accordingly.
  - From Codex-Requirements: Add explicit threshold output keys for the configured limits and thread them through postplan/result-env allowlists, docs, and tests where size KVs are presented.

### FINDING_5:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Focus area**: architecture
- **Location**: python/larch/design/plan_quality.py:428-560
- **Concern**: [SCOPE-REDUCTION] Firm-heading and surface counting should reuse canonical scope-path extraction instead of new parallel parsers. Scenario: The plan adds `_firm_heading_count`, `_plan_surface`, and `_plan_surfaces` plus separate path matching inside `prepare_partition_issues`. `issue_wire.extract_scope_paths(..., include_optional=False)` already parses firm `### NEW|UPDATED|REWRITTEN:` headings, backtick paths, parenthetical stripping, and Files-section boundaries for `/implement` coverage. Parallel logic can disagree on heading/path sets, producing false surface triggers, wrong inventories, or drift from implementer coverage diagnostics.
- **Proposed resolution**: Implement firm-heading count and distinct-surface derivation on top of `extract_scope_paths` (or a shared helper imported by both `plan_quality` and `decompose.py`), applying `_plan_surface` only to those canonical paths; use the same source list for decompose inventory matching. ### 1. architecture — `python/larch/design/decompose.py:97-191` **Concern:** The plan tests per-part acceptance criteria but `prepare_partition_issues` only parses `- acceptance:` from the panel body and does not derive it when missing (unlike firm-headings). **Suggested revision:** Add acceptance derivation or fail-closed validation so every split part body always carries acceptance criteria. ### 2. architecture — `python/larch/design/plan_quality.py:428-560` **Concern:** New surface/firm-heading parsers duplicate `issue_wire.extract_scope_paths`, risking inconsistent counts across Step 2b.5, decompose prepare, and `/implement` coverage. **Suggested revision:** Reuse shared scope-path extraction; apply surface bucketing only to those paths. Prior-round accepted items (Override wiring, `plan.txt` publish guard, trailer preservation, `PUBLISH_REFUSE_REASON`, composed-plan retry, Gate B keys, downstream scanners) are addressed in the current plan. I did not re-raise them.
