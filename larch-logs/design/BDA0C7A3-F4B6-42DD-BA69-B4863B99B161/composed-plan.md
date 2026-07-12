## Plan

## Approach

1. Route every size-triggered, explicit `--partition` / `-p`, semantic-sprawl, Gate B, settle-dispatch, and Step 5c publish-size refusal directly into one inline Split-path. Remove every preliminary Split / Override / Cancel, Split / Cancel, and Decompose / Override / Cancel partition prompt.
2. At Split-path entry, the main agent reads the current plan or, before plan materialization, the feature description plus optional discussion artifact. It computes a concrete risk-minimizing partition without subagents.
3. Use the existing partition Markdown schema. Order pieces so shared or risky foundations land first. Each piece must state scope, firm headings, acceptance criteria, explicitly declared dependencies, and a size estimate.
4. Run `decompose prepare` before prompting. It must accept only the dependencies declared by the inline proposal, reject a one-piece proposal, reject bad references and cycles, and never synthesize serial edges. If validation fails, repair the proposal inline and rerun validation; do not ask the operator to resolve internal partition details.
5. Present exactly one `AskUserQuestion` for every partition process:
   - When a valid proposal is prepared, offer partitioning into the listed pieces, override with the existing warning, and Other or chat.
   - When inline repair cannot produce a valid multi-piece acyclic proposal, still emit this one unified question with the partition option explicitly marked unavailable and its concise validation-failure reason. Selecting the unavailable partition option records the failure and terminates the Split-path; Override and Other/chat retain their normal outcomes. Do not emit another `AskUserQuestion`.
   - Other or chat exits the structured partition path without another `AskUserQuestion`.
6. If the operator accepts a valid partition, retain the existing `/larch:issue` batch filing and annotation mechanics, including the authoritative `partition-deps.tsv` intra-batch edges.
7. After a complete annotation, run `decompose migrate-deps` before `close-original`:
   - Validate session-backed live-mutation authorization from `source-env.sh` with `check_live_mutation_auth` before any GitHub dependency read or `block-issue` mutation. On denial, emit stable migration status rows, make zero `gh` calls, preserve the original issue and tmpdir, and leave the operation retryable through a properly authorized session.
   - Resolve and validate every filed issue number and repository from the annotation record.
   - Snapshot the original issue’s incoming (`blocked_by`) and outgoing (`blocking`) relations in retry state before the first mutation.
   - Verify the declared intra-piece graph against `partition-deps.tsv`.
   - Recreate every incoming relation as `each new piece blocked by the original blocker`, and every outgoing relation as `the original client blocked by each new piece`.
   - Invoke the canonical `block-issue add-blocked-by` and new `block-issue remove-blocked-by` CLI paths for mutations; use the existing GitHub dependency read helpers to verify live state after every add and removal.
   - Treat an already-present replacement edge and an already-absent original edge as successful idempotent state only after live verification.
   - Add and verify all replacement edges before removing any original edge. Re-read the relevant live original relation immediately before removal and fail closed if it no longer matches the persisted migration state.
   - Write `.decompose-deps-migrated` only after the complete replacement graph is verified and no persisted original relation remains.
8. Require `close-original` to verify the dependency-migration sentinel and live migration postcondition before commenting or closing the original issue. Do not allow a partial filing, migration failure, authorization denial, stale sentinel, or unverified graph to reach closure.
9. For a Step 5c publish-time size refusal, accepted partitioning is terminal: after filing, annotation, dependency migration, and original closure, export `SUMMARY_OUTCOME=approved-partition`, run the Final summary block, and exit `0`. Do not resume ordinary Step 5c publishing or continuation against the closed original issue. Only the unified Override outcome reruns `design-step5c.sh`.
10. Keep panel dispatch and aggregate infrastructure available for its existing callers, but remove it from the Split-path.

## Dependency migration semantics

- If original issue `O` is blocked by existing issue `B`, each new piece `P1…Pn` must be blocked by `B`; only then remove `O blocked-by B`.
- If original issue `O` blocks existing issue `C`, `C` must be blocked by each `P1…Pn`; only then remove `C blocked-by O`.
- The persisted migration manifest records validated filed-piece mappings and the original incoming/outgoing edges. Re-entry uses that manifest to converge after an interrupted removal phase rather than losing relations that were already removed.
- `migrate-deps` must validate `source-env.sh` live-mutation authorization before dependency reads as well as adds or removals. Authorization denial is an operational failure with stable status rows, no GitHub calls, and no mutation.
- Before every removal, reread the original relation. If GitHub reports a relation not represented in the migration manifest, or a manifest relation changed incompatibly, preserve the original issue and fail closed.
- Add, remove, and read operations use GitHub’s authenticated `gh api` contract. Mutation command success alone is insufficient; live dependency reads are the source of truth.
- A duplicate replacement add is successful only when the readback contains the relationship. An already-removed original edge is successful only when the readback confirms it is absent.
- A dependency read, add, remove, verification, or authorization failure records the external-command or authorization failure through the existing execution-issues path, preserves the original issue and design tmpdir, and leaves migration retryable.
- A sentinel is advisory only: on re-entry, validate its filed-piece mapping and live dependency postcondition before trusting it. Remove or reject stale completion state when the live graph no longer satisfies the postcondition.

## Files to modify/create

### UPDATED: skills/design/references/decompose-panel.md

- Replace panel dispatch, proposal selection, aggregation, unanimous-no-split, and repeated repair prompts in the Split-path with the inline main-agent partition procedure.
- Define the one-question contract and its Partition, Override, and Other/chat outcomes.
- Require pre-prompt `decompose prepare` validation. The main agent repairs invalid metadata, missing coverage, one-piece proposals, bad references, and cycles inline; no Split-path branch may emit a second `AskUserQuestion`.
- Define the unrecoverable-validation fallback: after inline repair fails, emit the same single question with Partition marked unavailable and its validation reason; selecting it records the validation failure and exits, while Override and Other/chat remain available. Do not silently terminate before the question.
- Preserve complete batch filing and annotation behavior.
- Add post-annotation `decompose migrate-deps` before `close-original`.
- Require migration success and `.decompose-deps-migrated` before closure, and document authorization denial, retry, stale-sentinel, fail-closed, and complete-batch behavior.
- State that `partition-deps.tsv` contains only proposal-declared, acyclic intra-piece dependencies; independent pieces remain independent.
- Preserve panel-dispatch and aggregate command documentation only as non-Split-path infrastructure.

### UPDATED: skills/design/SKILL.md

- Remove the standalone `_postplan_rc=12` question.
- Route `_postplan_rc=12`, `_postplan_rc=13`, explicit partition requests, and every referenced Split-path entry directly to the unified inline procedure.
- Replace the Step 5c `Decompose / Override / Cancel` size-refusal prompt with entry into the unified Split-path so publish-time `oversize-no-override` and `size-check-failed` receive the same single proposal question.
- Specify that a valid Step 5c accepted partition is terminal: complete filing, annotation, migration, and original closure; set `SUMMARY_OUTCOME=approved-partition`; run Final summary; and exit `0` without returning to ordinary publish flow.
- Preserve Step 5c override behavior by rerunning `design-step5c.sh`, and preserve non-size validator and architectural-assessment refusal behavior.
- Preserve oversize-override handling, Step 2b completion markers, cancellation/final-summary behavior, and continuation to Step 3 where the accepted path is not terminal.
- State that the main agent computes and repairs the partition without subagents.

### UPDATED: skills/design/references/step2b5-rc-handling.md

- Change `hard-trigger` handling from a preliminary Split / Override / Cancel prompt to immediate unified Split-path entry.
- Keep `partition-split` as direct entry and make both actions use the same one-question contract in `decompose-panel.md`.
- Move override and cancellation outcomes into that unified question; do not issue a local prompt.
- Preserve retained completion-marker behavior after non-exiting override paths.

### UPDATED: skills/design/references/approval-gates-gate-b.md

- Route Gate B hard-size and explicit partition outcomes directly to the unified Split-path.
- Remove Gate B-specific Split / Override / Cancel wording and require its size route to share the same prepared inline proposal and one-question contract.
- Preserve Gate B’s override completion and Step 3 continuation semantics after the unified path returns.

### UPDATED: skills/design/references/settle-rc-dispatch.md

- Change `gate-b-hard-size` and `gate-a-hard-size` from local hard-size prompts to direct unified Split-path entry.
- Keep `gate-a-split` and `gate-b-split` as direct aliases of that same path.
- Ensure settle dispatch does not issue a preceding partition-choice `AskUserQuestion`.

### UPDATED: skills/design/references/discussion-rounds.md

- Replace the semantic-sprawl Split / Cancel prompt with direct unified Split-path entry.
- Preserve the existing at-most-once sprawl-trigger cap and cancellation behavior through the unified Other/chat outcome.
- Make the feature-only input contract explicit: the main agent uses feature description and optional discussion artifact when no `plan.txt` exists.

### UPDATED: skills/design/references/flags.md

- Update `--partition` / `-p` and hard-trigger prose to identify the inline unified Split-path rather than the decomposition panel.
- State that all size and partition entry routes share one partition question and proposal-declared dependency graph.
- Document that unrecoverable automatic-proposal validation still reaches the one-question fallback rather than issuing follow-up partition-detail questions.

### UPDATED: python/larch/design/design_step2b.py

- Align emitted Step 2b / postplan action routing so `rc=12`, `rc=13`, explicit partition, and hard-trigger callers reach the unified Split-path without a separate partition prompt.
- Preserve action-envelope and completion-marker contracts consumed by retained callers.

### UPDATED: skills/design/references/finalize-step5.md

- Route `PUBLISH_REFUSE_REASON=oversize-no-override|size-check-failed` to the unified Split-path instead of a standalone Decompose / Override / Cancel gate.
- Preserve the existing non-size Step 5c validator and architectural-assessment refusal branches.
- Specify that Override reruns Step 5c.
- Specify that accepted partitioning completes filing, annotation, dependency migration, and original closure; exports `SUMMARY_OUTCOME=approved-partition`; runs the Final summary block; and exits `0` without an ordinary Step 5c retry or Step 3 continuation.

### UPDATED: python/larch/design/decompose.py

- Change `prepare_partition_issues` to emit only explicit dependencies declared in the inline partition proposal.
- Reject one-piece proposals, invalid piece references, duplicate/invalid filed mappings, metadata gaps, and declared cycles; never silently drop cycle-forming edges or insert serial edges.
- Add typed helpers to parse the complete annotation mapping, validate GitHub issue URLs against the expected repository, parse dependency-read payloads, and load/write a durable dependency-migration manifest.
- Add `migrate-deps` logic that:
  - validates `source-env.sh` using `check_live_mutation_auth` before any dependency read, GraphQL lookup, or add/remove mutation;
  - returns stable, redacted authorization-denial rows and makes no `gh` invocation when authorization is absent, invalid, stale, or mismatched;
  - reads original blocked-by and blocking relations through `larch.git.gh`;
  - persists the initial validated edge set before mutation;
  - derives incoming and outgoing replacement edge sets;
  - calls canonical CLI mutation paths for add and removal;
  - rereads live dependencies after every mutation;
  - prevents removal until all replacement edges verify;
  - checks intra-piece edges against `partition-deps.tsv`;
  - supports idempotent partial retry; and
  - writes `.decompose-deps-migrated` only after the complete live graph postcondition verifies.
- Emit stable, redacted `KEY=value` status rows, including `DECOMPOSE_DEPS_STATUS`, `DECOMPOSE_DEPS_PHASE`, and `DECOMPOSE_DEPS_SENTINEL`; use exit `0` only for verified completion, `1` for operational migration or authorization failure, and `2` for usage or invalid persisted input.
- Record failed external commands and authorization failures through the existing execution-issues path without exposing helper stdout or stderr in normal operator output.
- Make `close_original_issue` require successful dependency migration and revalidate the migration postcondition before comment/close.
- Leave panel dispatch and aggregation functions intact.

### UPDATED: python/larch/issue/issue_block.py

- Add a canonical `remove-blocked-by` operation alongside `add-blocked-by`.
- Resolve both issue node IDs in the same repository, execute GitHub’s authenticated GraphQL dependency-removal mutation, and use the same repository validation and error-redaction conventions as add.
- Define idempotent behavior for a relationship already absent, while requiring `decompose migrate-deps` to confirm absence through the canonical dependency read path.
- Emit stable machine rows for success and failure without claiming verified removal before the caller’s readback.

### UPDATED: python/larch/cli.py

- Register `decompose migrate-deps`.
- Register `block-issue remove-blocked-by` beside the canonical `block-issue add-blocked-by` command.

### UPDATED: python/tests/design/test_decompose.py

- Replace automatic-serial-edge expectations with tests that `prepare_partition_issues` writes only declared edges and preserves independent pieces without a dependency edge.
- Add declared-edge, duplicate-edge, invalid-reference, one-piece, metadata, and cycle rejection coverage.
- Add Split-path contract coverage proving unrecoverable automatic-proposal validation still presents exactly one unified question, marks partition unavailable, and terminates only after the selected unavailable outcome without issuing a second question.
- Add migration fixtures for incoming, outgoing, bidirectional, multiple, duplicate, empty, partial, and changed-live dependency graphs.
- Verify every filed piece inherits incoming blockers and every outgoing client becomes blocked by every filed piece.
- Verify intra-piece dependency relationships against `partition-deps.tsv`.
- Verify `migrate-deps` validates session-backed live-mutation authorization before any dependency read or mutation, emits the documented denial rows, and makes zero mocked `gh` calls when unauthorized.
- Verify replacement edges are added and read-verified before any original edge removal.
- Verify read, add, verification, removal, authorization denial, malformed filed URL, repository mismatch, missing issue mapping, inconsistent piece count, and changed-live-graph failures write no completion sentinel and do not permit original closure.
- Verify successful re-entry skips completed additions/removals, uses the persisted migration manifest, and converges after interruption.
- Verify stale sentinels are rejected when live graph postconditions fail.
- Verify documented migration status rows and exit codes.
- Retain existing panel and aggregate tests because those facilities remain available.

### UPDATED: python/tests/issue/test_issue_block.py

- Add canonical removal tests for successful GraphQL removal, node-ID lookup failure, mutation error, malformed arguments, repository validation, and already-absent/idempotent behavior.
- Verify stable `KEY=value` success and failure grammar for both add and removal operations.

## Edge cases

- A feature-only partition has no `plan.txt`. The main agent uses the feature description and optional discussion artifact while still supplying explicit piece metadata and declared dependencies.
- A one-piece proposal is not a partition. Recompute it inline or allow the unified override/Other-chat outcome; do not ask a second question.
- If valid multi-piece acyclic partitioning remains impossible after inline repair, present the single fallback partition question with Partition unavailable; record and terminate only if that unavailable option is selected.
- Independent pieces must remain independent: `decompose prepare` must not add a serial chain.
- The original issue may have no external dependency relations. Migration completes only after valid filed mappings and intra-piece dependency verification.
- `migrate-deps` must reject an unauthorized, stale, or mismatched live-mutation session before performing a dependency read, node lookup, add, or removal.
- GitHub may report a replacement edge already present or an original edge already absent. Confirm the live state and continue.
- Filing may partially succeed. Do not migrate dependencies or close the original until annotation records a complete batch.
- Filed issue URLs must be valid GitHub issue URLs for the current repository and map one-to-one to expected pieces. Reject unexpected repositories, malformed issue numbers, duplicates, and count mismatches before mutation.
- Existing relationships may change during migration. Compare live state with the persisted migration manifest before removal and fail closed on incompatible change.
- An operator’s Other or chat response may supply custom direction. Exit the structured partition path without launching another `AskUserQuestion`.
- Publish-time accepted partitioning is terminal after final summary; do not rerun publishing or continue workflow steps against the original issue.
- Publish-time oversize, Gate B hard-size, retained Step 2b.5 hard-size, explicit partition, and sprawl paths must each reach the same single-question Split-path without an earlier partition-choice question.

## Failure modes

- If inline partition validation cannot produce a valid acyclic, multi-piece scheme, emit the one-question unavailable-partition fallback. Do not ask partition-detail questions; if its unavailable Partition option is selected, record the failure and terminate.
- If live-mutation authorization fails, record the authorization failure with stable migration rows, perform no GitHub calls, preserve the original issue and tmpdir, and do not close the original issue.
- If issue filing or annotation is incomplete, preserve existing partial-filing behavior and do not touch the original dependency graph.
- If any replacement edge cannot be added or read-verified, leave all original edges intact.
- If a replacement edge verifies but an original edge cannot be removed or read-verified absent, preserve migration state for idempotent retry and do not close the original issue.
- If a migration manifest cannot be parsed, does not match the current filed mapping, or conflicts with live original relations, fail closed without mutation.
- If the migration sentinel exists but live postconditions no longer hold, reject stale completion and rerun validated migration rather than trusting the sentinel.
- If closure preconditions are absent or fail readback, do not post the close comment or run `gh issue close`.
- If a Step 5c accepted partition reaches final summary, exit successfully after that summary rather than re-entering publish or ordinary continuation.

## Testing strategy

- Run the focused Python modules:
  - `python/tests/design/test_decompose.py`
  - `python/tests/issue/test_issue_block.py`
  - affected `python/tests/git/test_gh.py` coverage for dependency-read helper contracts.
- Run changed-file Python lint and type checks for `python/larch/design/decompose.py`, `python/larch/design/design_step2b.py`, `python/larch/issue/issue_block.py`, `python/larch/cli.py`, and their changed tests.
- Run changed-skill Markdown and prompt-contract checks for `skills/design/SKILL.md` and every modified design reference.
- Manually trace `_postplan_rc=12`, `_postplan_rc=13`, explicit `--partition`, Gate A hard-size, Gate B hard-size, semantic sprawl, and Step 5c size refusal. Confirm each partition process reaches exactly one `AskUserQuestion`, including unrecoverable proposal-validation fallback.
- Exercise the unavailable-partition fallback by stubbing an inline proposal that remains invalid after repair. Confirm the user sees one question, no follow-up prompt occurs, and selecting the unavailable Partition option records the terminal failure.
- Exercise stubbed end-to-end partitions with incoming and outgoing original dependencies. Confirm proposal-declared intra-piece edges, filing, annotation, live-mutation authorization, replacement-edge add/readback, original-edge removal/readback, migration sentinel, and original closure occur in that order.
- Exercise unauthorized `migrate-deps` with invalid or missing live-mutation session state. Confirm stable authorization status rows, no `gh` dependency reads or mutations, no sentinel, and no closure.
- Exercise interrupted migration after replacement adds and after partial removals. Confirm re-entry uses the persisted migration manifest, avoids duplicate work, verifies the live graph, and closes only after full convergence.
- Exercise Step 5c accepted partitioning. Confirm filing, annotation, migration, and closure complete; `SUMMARY_OUTCOME=approved-partition` reaches Final summary; the command exits `0`; and `design-step5c.sh` is not rerun. Confirm only Override reruns Step 5c.

## Acceptance

- Run the focused Python modules:
  - `python/tests/design/test_decompose.py`
  - `python/tests/issue/test_issue_block.py`
  - affected `python/tests/git/test_gh.py` coverage for dependency-read helper contracts.
- Run changed-file Python lint and type checks for `python/larch/design/decompose.py`, `python/larch/design/design_step2b.py`, `python/larch/issue/issue_block.py`, `python/larch/cli.py`, and their changed tests.
- Run changed-skill Markdown and prompt-contract checks for `skills/design/SKILL.md` and every modified design reference.
- Manually trace `_postplan_rc=12`, `_postplan_rc=13`, explicit `--partition`, Gate A hard-size, Gate B hard-size, semantic sprawl, and Step 5c size refusal. Confirm each partition process reaches exactly one `AskUserQuestion`, including unrecoverable proposal-validation fallback.
- Exercise the unavailable-partition fallback by stubbing an inline proposal that remains invalid after repair. Confirm the user sees one question, no follow-up prompt occurs, and selecting the unavailable Partition option records the terminal failure.
- Exercise stubbed end-to-end partitions with incoming and outgoing original dependencies. Confirm proposal-declared intra-piece edges, filing, annotation, live-mutation authorization, replacement-edge add/readback, original-edge removal/readback, migration sentinel, and original closure occur in that order.
- Exercise unauthorized `migrate-deps` with invalid or missing live-mutation session state. Confirm stable authorization status rows, no `gh` dependency reads or mutations, no sentinel, and no closure.
- Exercise interrupted migration after replacement adds and after partial removals. Confirm re-entry uses the persisted migration manifest, avoids duplicate work, verifies the live graph, and closes only after full convergence.
- Exercise Step 5c accepted partitioning. Confirm filing, annotation, migration, and closure complete; `SUMMARY_OUTCOME=approved-partition` reaches Final summary; the command exits `0`; and `design-step5c.sh` is not rerun. Confirm only Override reruns Step 5c.

review_status: complete
rounds_completed: 2
difficulty: HARD
diff_added: 515
diff_deleted: 265
mechanical_churn: false
oversize_override: operator
diff_lines: 780
