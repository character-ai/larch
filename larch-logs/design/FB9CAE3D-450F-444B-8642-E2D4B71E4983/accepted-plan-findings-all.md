### FINDING_1: Inherited exception edges lack a before-close approval and write step
- **Reviewer(s)**: Cursor-Arch, Cursor-Pragmatic, Cursor-Requirements, Cursor-dyn-exception-gate-ordering
- **Severity**: important
- **Concern**: Inherited OOS-to-non-OOS exception edges are split from safe edges, but the approval gate runs after source closure or is scoped to audit edges. Approved inherited exceptions may be dropped, written without approval, or never written before sources close.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add an inherited-exception AskUserQuestion sub-step at the end of oos-6 (or a new oos-6b): surface each (non-OOS client, [OOS] blocker) pair with title and reason; write only approved edges before oos-7
  - From Cursor-Pragmatic, Cursor-Requirements: Reorder or split gates: run an inherit-only exception prompt immediately after oos-6 (before oos-7), write approved inherited exceptions there; keep oos-9 for audit-derived exceptions only
  - From Cursor-dyn-exception-gate-ordering: Reorder and align prose: add an inherit-phase exception prompt/write at the end of oos-6; move Sequence step 7 (close) to after that gate; keep oos-9 for audit-origin exceptions only
  - From Cursor-dyn-exception-gate-ordering: Change step 12 to write all approved exception edges, or split writes: approved inherit exceptions written at end of oos-6; oos-9 writes only audit-origin approvals
  - From Cursor-dyn-exception-gate-ordering: Extend planned oos-6 with an inherit exception sub-step: prompt approve/reject, write approved edges, record rejected; scope oos-9 to audit candidates not already decided in oos-6


### FINDING_4: Sources can close after dependency reads, writes, or inherited decisions are incomplete
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Codex-Innovation, Codex-Pragmatic, Codex-dyn-symbol-existence
- **Severity**: important
- **Concern**: Dependency read failures are warnings, and close-sources can still run before inherited writes or inherited exception decisions are complete. That can orphan unknown or unwritten native dependencies.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Gate close-sources per combined group: skip closing any source whose fetch-deps entry is missing or warned until inherit writes succeed, or fail the inherit phase closed
  - From Codex-Arch: Track dependency-read failures and inherited exception decisions per source. Do not pass affected sources to close-sources until their dependency reads succeeded and all inherited edges are written, or leave the source open when an inherited edge is unresolved/rejected
  - From Codex-Innovation: Make failed source dependency reads close-blocking; skip close-sources for affected source issues or stop before closure until reads succeed
  - From Codex-Pragmatic: Close only sources whose dependency reads succeeded and whose required inherited writes either succeeded, were already present, or were explicitly rejected by the exception gate. Leave failed sources open and summarize them.
  - From Codex-dyn-symbol-existence: Have fetch-deps report failed dependency reads per source issue, and make the skill skip closing those source issues or stop closure until their dependency reads succeed


### FINDING_6: Open-issue audit excludes archival open issues
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Concern**: Using issue list-issues for the audit may filter out open archival research, investigate, or report issues. Dependencies between those issues and new combined OOS issues would never be detected or written.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: For this audit, fetch all open issues without _title_archival filtering, for example with a combine-issues scoped open-issue fetch or an include-archival mode used only here


### FINDING_7: Audit prose scanning misses combined-issue “Blocks” direction
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Concern**: prose-audit relies on parse_prose_blockers, which may not parse “Blocks #N” text in a combined issue body. That misses the combined-blocks-open direction.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Add minimal Blocks/Blocking #N handling for prose-audit's combined-issue scan and emit (referenced_open_issue, combined_issue), or otherwise define Tier-1 scanning to cover that direction




### FINDING_1: Partition deferred source closure by combined issue
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: Multi-group `close-sources` can close or label the wrong source issues unless eligible sources are grouped by the combined issue they were merged into.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: In oos-7, require partitioning eligible sources by their `source_to_combined` host; invoke `close-sources` once per combined issue with matching `--source-issues`; aggregate `CLOSED_ISSUES` in the summary.


### FINDING_2: Provide metadata needed to classify OOS exception edges
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: The inherited-edge classifier cannot mechanically detect non-OOS issues that would be blocked by newly combined `[OOS]` issues without issue titles, states, and the newly combined issue set.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Pass fetch-deps/classify a repo issue map (number, title, state) plus the run's combined_issue IDs, or have classify fetch titles via gh.issue_view_title_body_read before splitting safe vs exception edges


### FINDING_3: Require paginated full-open-issue fetch for audit
- **Reviewer(s)**: Cursor-Pragmatic, Cursor-dyn-module-reference
- **Severity**: important
- **Concern**: `list_open_main` may silently audit only the first 200 open issues unless the plan requires a paginated fetch of the full open-issue set.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Specify list_open_main must fetch all open issues via gh api --paginate (mirror issue_create.list_issues_main) and filter to state=open in Python; add a test that a second page of open issues is included.
  - From Cursor-dyn-module-reference: Specify `list_open_main` should use `gh api --paginate repos/{repo}/issues?state=open&per_page=100` (same pattern as `issue_create.list_issues_main` at `python/issue_create.py:733`), filter out pull requests, exclude closed issues, and keep archival titles.


### FINDING_4: Add write path for safe audit-derived dependency edges
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Concern**: The audit phase detects safe combined↔open dependencies but does not explicitly write those edges after exception gating.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Add oos-8b (or extend oos-9): after exception decisions, call issue add-blocked-by for all remaining safe audit candidates; mirror oos-6 safe-edge write/idempotency/failure recording; count them in oos-10 audit_edges_written


### FINDING_5: Parse dependency endpoint issue objects, not bare integers
- **Reviewer(s)**: Cursor-dyn-api-endpoint
- **Severity**: important
- **Concern**: `fetch_deps_main` may inherit no edges if it treats dependency endpoint results as bare integers instead of paginated arrays of issue objects with numeric `number` fields.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-api-endpoint: In fetch_deps_main, after gh.loads_json_paginated_list, extract each row's numeric number field (int or digit string) from dict rows; do not treat top-level array elements as bare issue numbers. Point tests at python/test_blocker.py:49-50 object payloads.


### FINDING_6: Update deferred-close KV consumers and close tallies
- **Reviewer(s)**: Cursor-dyn-skill-step-flow
- **Severity**: important
- **Concern**: The skill can report misleading zero source-closure counts, or treat deferred closure as failure, if oos-5 keeps consuming `CLOSED_ISSUES` after `apply --defer-close`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-skill-step-flow: In oos-5 parse COMBINED_ISSUE SOURCE_ISSUES CLOSING_DEFERRED; stop using CLOSED_ISSUES for per-group close counts; change the per-group line to note closure deferred; move the final source-closed tally to oos-10 using close-sources output


### FINDING_7: Parse comment bodies during prose audit
- **Reviewer(s)**: Cursor-dyn-module-reference
- **Severity**: important
- **Concern**: Tier-1 prose audit can miss comment-only dependency prose if it fetches comments but only parses issue bodies.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-module-reference: Require running `blocker.parse_prose_blockers` and the new Blocks parser on every fetched comment body, not only issue bodies. Add prose-audit tests for comment-sourced edges.



### FINDING_1: Expose dependency remap/classify/closure helpers through CLI
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Requirements
- **Severity**: important
- **Concern**: Tested remap, classification, and close-eligibility logic is planned as internal Python helpers, but the skill can only invoke `python/cli.py combine-issues` verbs. Without CLI entrypoints, oos-6/oos-7 must duplicate graph logic in prose or ad hoc imports, which can drift from tests and misclassify edge direction or closure eligibility.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Register and wire CLI verbs (for example `combine-issues inherit-edges` or separate `remap-inherited` / `classify-inherited`) that accept fetch output plus `source_to_combined`, emit safe/exception/unknown edge JSON, and update oos-6 to consume that output instead of duplicating logic inline.
  - From Cursor-Innovation: The skill cannot call private helpers; an LLM reimplementing graph remap and (client, blocker) classification will drift from pytest-covered logic and can invert edges or mis-bucket OOS exception cases. Register one mechanical verb (for example combine-issues prepare-inherited) that accepts fetch-deps JSON plus source_to_combined and list-open metadata and emits safe, exception, unknown, and per-source close-eligibility JSON; keep oos-6/oos-7 as orchestration over that stdout.
  - From Cursor-Requirements: Register CLI entrypoints (e.g. combine-issues plan-inherited and combine-issues close-eligible) that consume fetch-deps/list-open JSON and emit classified edge and closure-eligibility JSON for oos-6/oos-7 to call


### FINDING_2: Tier-2 audit candidates need an explicit safe-write policy
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: oos-8 can produce Tier-2 audit candidates, but oos-9 auto-writes safe audit edges without a normalization or approval gate. Speculative Tier-2 reasoning can therefore become a registered dependency even though uncertain Tier-2 edges should surface as proposals.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Define one audit-candidate schema (prose vs Tier-2, confidence, prior decision refs), merge/dedupe in `oos-8`, and require operator approval for every Tier-2 edge before `oos-9` writes (or explicitly drop Tier-2 auto-writes and keep Tier-1 prose only)


### FINDING_3: Verify or fail closed on the blocking dependency read endpoint
- **Reviewer(s)**: Cursor-dyn-api-endpoint-gap
- **Severity**: important
- **Concern**: The plan assumes a symmetric GitHub `dependencies/blocking` read endpoint, but the repository only shows the blocked-by read path. If the endpoint is wrong, all blocking-direction inheritance can fail before source closure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-api-endpoint-gap: Add a pre-implementation smoke check or test fixture that pins the blocking argv and a captured gh api response; if the endpoint is unavailable document a fallback or fail closed with an explicit operator-visible error rather than assuming symmetry


### FINDING_4: Define the prose-audit dedup input contract
- **Reviewer(s)**: Cursor-dyn-dedup-state-handoff
- **Severity**: important
- **Concern**: `prose_audit_main` mentions an optional inherited-edge input but does not define a CLI flag or JSON schema. Implementers can omit it or invent incompatible argv and tuple formats.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-dedup-state-handoff: Add explicit argparse e.g. --existing-edges-file with JSON list of [client, blocker] int pairs document tuple order matches (client_issue blocker_issue) and register in cli.py combine_issues section


### FINDING_5: Make oos-8 invoke prose-audit with concrete argv
- **Reviewer(s)**: Cursor-dyn-dedup-state-handoff
- **Severity**: important
- **Concern**: oos-8 calls `combine-issues prose-audit` without the required `--repo`, `--combined-issues`, `--open-issues`, or dedup input. The skill cannot run the audit mechanically without guessing state.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-dedup-state-handoff: Add fenced invocation passing --combined-issues from recorded oos-5 IDs --open-issues from list-open output and --existing-edges-file built from oos-6/6b ledger




### FINDING_2: close-eligible input schemas are undefined
- **Reviewer(s)**: Cursor-Arch, Cursor-Pragmatic, Cursor-dyn-json-schema-chain, Cursor-dyn-deferred-close-integrity
- **Severity**: important
- **Concern**: `close-eligible` consumes write-result and exception-decision files without a normative JSON contract, so implementations can disagree about failed, idempotent, unresolved, approved, or rejected edge states and close sources incorrectly.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Specify write-results JSON in the plan (e.g. list of {edge,client,blocker,phase,status} with status written|already_present|failed) and add close-eligible tests that parse the exact schema
  - From Cursor-Pragmatic: Add explicit schemas in `combine_issues.py` (e.g. `write_results`: list of `{edge, source_issues, status, error?}`; `exception_decisions`: list of `{edge, decision}` with `approved|rejected|unresolved`) and pin them in `test_combine_issues.py`
  - From Cursor-dyn-json-schema-chain: Add documented schemas for write-results (per-edge client/blocker/outcome/source_issues) and exception-decisions (per-edge approved|rejected|unresolved) and state that close-eligible reads the full plan-inherited JSON document via --inherited-plan-file
  - From Cursor-dyn-deferred-close-integrity: Add an explicit schema e.g. decisions array of {edge:[client,blocker],decision:approved|rejected|unresolved} keyed by edge tuple; document that only unresolved blocks closure; pin in python/test_combine_issues.py.


### FINDING_3: existing_edges assembly is ambiguous for inherited and decided edges
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: The plan does not define how `existing_edges.json` derives edge pairs for rejected exception decisions or unknown inherited edges, so audit deduplication can either re-surface rejected edges or suppress valid candidates.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Define existing_edges construction: inherited edges from plan-inherited output only; add separate decided_edges list for rejected/approved audit decisions; document merge rules in oos-8


### FINDING_4: Tier-2 audit pair selection is unbounded
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: The Tier-2 semantic audit can expand to combined issue by open issue reasoning across the full open set, which conflicts with the non-goal excluding a full LLM audit and may not finish.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Bound Tier-2 to explicit triggers only (e.g. Tier-1 candidate on one endpoint, shared file paths in OOS item Location fields, or native remap candidates); state in skill that unaudited pairs are intentionally skipped


### FINDING_5: close-eligible cannot account for OOS-blocked sources
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: `close_eligible_main` has no input that marks sources with remaining blocked OOS items, so it can declare a source eligible and let `close-sources` close it despite unresolved blocked items.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Add --blocked-sources-file (or per-source has_blocked_items in combined_issues.json) and make close_eligible_main mark those sources ineligible with an explicit reason; add a test that a blocked source never appears in eligible_by_combined.


### FINDING_6: Prose audit does not remap consumed source references
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Concern**: Prose audit runs after source closure and scans literal issue references, so prose-only links to consumed source issues can be emitted against closed endpoints and never registered on the combined host.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Add `--source-to-combined-file` to `prose_audit_main` (and wire it in oos-8) to rewrite consumed source numbers to their combined hosts before dedup/write, or run prose audit before oos-7 closure.


### FINDING_7: Unknown inherited edges are not recoverable after metadata refresh
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Concern**: `plan-inherited` can emit unknown edges when metadata is missing, but the later open-issue refresh does not reclassify them and `existing_edges.json` can suppress them, so they may never be written or resolved.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: After the oos-8 `list-open` refresh, re-run `plan-inherited` (or a narrow unknown-only reclassify step) before audit; omit unresolved `unknown_edges` from `existing_edges.json` until classified or explicitly operator-resolved.



