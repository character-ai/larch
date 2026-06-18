### FINDING_1: Embedded plan-review-loop still invokes deleted prune-nit shell
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic, Codex-Requirements
- **Severity**: blocking
- **Concern**: Deleting `skills/review/scripts/prune-nit-findings.sh` without repointing the gzip-embedded `plan-review-loop.sh` consumer. The embedded loop still defaults `PLAN_REVIEW_PRUNE_NITS_SH` to that deleted path, while `_rewrite_prune_asset` only rewrites `reviewer-prune`. After deletion, `/design` plan-review nit pruning fails (rc 127), fail-opens via `prune-nit.env` (`STATUS=skipped`), and ballot composition changes silently before tally.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add ### UPDATED: python/plan_review.py and python/test_plan_review.py. Extend _rewrite_prune_asset (or sibling) to retarget PLAN_REVIEW_PRUNE_NITS_SH default and invocation to python3 "$PLUGIN_ROOT/python/cli.py" review prune-nit-findings; add test_embedded_plan_review_prune_nit_uses_review_cli mirroring test_embedded_plan_review_reviewer_prune_uses_review_cli
  - From Cursor-Innovation: Add ### UPDATED: python/plan_review.py: extend _rewrite_prune_asset (or plan-review-loop decode path) to replace the default prune-nit shell path with python3 "$PLUGIN_ROOT/python/cli.py" review prune-nit-findings (same pattern as reviewer-prune CLI rewrite); add regression test via legacy_asset_bytes
  - From Cursor-Pragmatic: Add a plan_review.py _decode_legacy_asset rewrite for plan-review-loop.sh (and any other embedded asset that invokes prune-nit-findings.sh) to call python3 "$PLUGIN_ROOT/python/cli.py" review prune-nit-findings; add an embedded-body regression test mirroring test_embedded_plan_review_reviewer_prune_uses_review_cli before deleting the skills script
  - From Codex-Requirements: Add UPDATED python/plan_review.py to rewrite the embedded plan-review-loop default/invocation to python3 "$PLUGIN_ROOT/python/cli.py" review prune-nit-findings while preserving the LARCH_PLAN_REVIEW_PRUNE_NITS_SH override; add a small python/test_plan_review.py assertion for the decoded asset


### FINDING_2: Tracked docs still cite retired compose-review-findings.sh
- **Reviewer(s)**: Codex-Arch, Codex-Innovation, Codex-Pragmatic, Cursor-Requirements, Codex-Requirements
- **Severity**: blocking
- **Concern**: The plan retires `python/legacy_review_shell/compose-review-findings.sh` and appends it to `python/migrated-scripts.tsv`, but omits existing tracked references in `SECURITY.md` and `docs/run-logs.md`. After the manifest append, `make lint-retired-scripts` will flag those exact path literals, so `make lint` cannot pass and docs still describe a deleted shell producer.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Add UPDATED entries for SECURITY.md and docs/run-logs.md, and replace the retired shell path with python/cli.py review compose-findings or python/compose_review.py as the producer contract.
  - From Codex-Innovation: Add SECURITY.md and docs/run-logs.md to the plan and replace those producer references with the Python review compose-findings entrypoint/module, keeping the redaction contract wording
  - From Codex-Pragmatic: Add SECURITY.md and docs/run-logs.md to the plan and replace those producer-contract references with python/compose_review.py or python/cli.py review compose-findings while preserving the redaction and JSONL contracts
  - From Cursor-Requirements: Add ### UPDATED: docs/run-logs.md repointing review-findings-full.jsonl contract text to python/compose_review.py and python/cli.py review compose-findings only (drop the .sh path)
  - From Cursor-Requirements: Add ### UPDATED: SECURITY.md naming python/compose_review.py / review compose-findings as the JSONL redaction authority (remove legacy_review_shell/compose-review-findings.sh)
  - From Codex-Requirements: Add UPDATED docs/run-logs.md and UPDATED SECURITY.md to replace the retired script path/facade wording with python/cli.py review compose-findings and python/compose_review.py as the producer surface



### FINDING_2: Prune-nit embedded rewrite needs CLI argv array, not path swap
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: `_rewrite_prune_asset` retargets `REVIEWER_PRUNE_SH` to a `REVIEWER_PRUNE_CLI` argv array (lines 892–899), but the decoded `plan-review-loop.sh` still binds `PLAN_REVIEW_PRUNE_NITS_SH` and invokes `"$PLAN_REVIEW_PRUNE_NITS_SH"`. A one-line default swap to `python3 … review prune-nit-findings` is not a valid executable for that call shape; `/design` plan-review gets rc 127, fail-open `prune-nit.env`, and ballot drift.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Mirror `DISPATCH_WATERFALL_CMD` in the same function: if `LARCH_PLAN_REVIEW_PRUNE_NITS_SH` is set, honor it; else `PLAN_REVIEW_PRUNE_NITS_CLI=(python3 "$PLUGIN_ROOT/python/cli.py" review prune-nit-findings)`; replace every `"$PLAN_REVIEW_PRUNE_NITS_SH"` / `"${PLAN_REVIEW_PRUNE_NITS_SH}"` call with `"${PLAN_REVIEW_PRUNE_NITS_CLI[@]}"`


### FINDING_3: Plan-mode prune port must preserve two-file rollback on OOS failure
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Concern**: The shell `prune-nit-findings.sh` plan-mode path (lines 195–208) moves the rewritten findings file first, then the OOS temp file; if the OOS replace fails it restores the original findings content before emitting `STATUS=skipped`. The G2 plan lists plan-mode remove/renumber/append behavior and generic atomic writes but never requires that rollback, so a naive Python port can leave nit blocks removed from `findings-in-scope.md` without a matching OOS append.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Add an explicit `prune_nit_findings` plan-mode step: snapshot original findings (and OOS when present), commit via same-directory temps, and on any post-findings OOS failure restore the snapshots before emitting `STATUS=skipped`



### FINDING_2: AGGREGATE_DISPATCH_SH argv dispatch semantics
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: The plan does not pin argv dispatch semantics when the aggregate bash body moves in-process. Scenario: Live bash uses `dispatch_cmd` array semantics: `AGGREGATE_DISPATCH_SH` is a one-element executable override, default is `(python3 "$PLUGIN_ROOT/python/cli.py" agent dispatch-waterfall)`, invoked as `"${dispatch_cmd[@]}"` (`python/legacy_review_shell/aggregate-findings.sh:702-706,894). A Python port that treats the default as one shell string or passes `AGGREGATE_DISPATCH_SH` incorrectly will ENOENT on aggregation dispatch and leave findings unmerged.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: In the review_aggregate.py section, specify proc.run argv: override env runs [AGGREGATE_DISPATCH_SH, *dispatch_args]; default runs [sys.executable, cli, agent, dispatch-waterfall, *dispatch_args]; preserve existing test stubs that set AGGREGATE_DISPATCH_SH to a single script path


### FINDING_3: Missing _MACHINE_STDOUT_KEYS for prune-nit-findings
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Concern**: Plan registers `review prune-nit-findings` in `_REGISTRY` but does not require a matching `_MACHINE_STDOUT_KEYS` entry. Scenario: review core and embedded plan-review invoke prune via `python3 cli.py review prune-nit-findings` as a child process; without `_MACHINE_STDOUT_KEYS` the child may inherit `LARCH_QUIET_ACTIVE` and corrupt `PRUNED_COUNT`/`INSCOPE_REMAINING`/`STATUS` KV stdout that `review_pipeline` writes to `prune-nit.env`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Add ("review", "prune-nit-findings") to _MACHINE_STDOUT_KEYS alongside review aggregate-findings and other KV-emitting review verbs


