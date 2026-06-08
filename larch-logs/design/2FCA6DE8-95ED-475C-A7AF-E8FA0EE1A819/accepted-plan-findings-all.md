### FINDING_1: Helper deletion is unsafe while live bash callers still invoke retired scripts
- **Reviewer(s)**: Cursor-Arch, Cursor-Edge, Codex-Edge, Cursor-Innovation, Codex-Innovation, Codex-Pragmatic, Cursor-Requirements, Codex-Requirements, Cursor-dyn-call-site-sweep
- **Severity**: important
- **Concern**: The plan deletes absorbed helper scripts before all live bash consumers are cut over or explicitly protected. This affects both the documented `LARCH_SHIP_PR_IMPL=bash` legacy path and default/top-level scripts such as preflight, bootstrap, finalize, launch-review, session setup, and issue helpers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add a binding retention rule: do not delete any absorbed script still referenced from ship-pr.sh or implement-finalize.sh until E1; or narrowly repoint only those $SCRIPT_DIR call sites to cli.py while leaving the rest of ship-pr untouched
  - From Cursor-Edge: Expand UPDATED call-site sweep to explicitly include every remaining scripts/*.sh and skills/**/scripts/*.sh caller (at minimum preflight implement-bootstrap implement-finalize launch-review lint-fix-loop fetch-issue-details) before each domain deletion; gate deletion on grep-zero retired basenames outside ship-pr.sh and migrated-scripts.tsv
  - From Cursor-Edge: Defer retiring any script still referenced from scripts/ship-pr.sh until E1 (or add an explicit minimal ship-pr cutover slice); do not treat ship-pr untouched as permission to delete its dependencies
  - From Codex-Edge: Add an explicit root scripts/*.sh cutover/audit step for all non-retired bash consumers before deletion, not only skills/**/scripts/*.sh and verify-skill-called.sh
  - From Codex-Edge: Either keep every helper still required by legacy ship-pr.sh until E1, or explicitly retire/update the bash selector and docs in this PR; do not both leave ship-pr.sh untouched and delete its dependencies
  - From Cursor-Innovation: Add an explicit retention carve-out: do not delete any script still referenced from ship-pr.sh implement-finalize.sh or ci-wait.sh internals until E1; narrow DoD to delete only scripts with zero remaining live callers after cutover (lint-retired-scripts gate)
  - From Codex-Innovation: Resolve the contradiction: either include a mechanical ship-pr.sh cutover for its external helper invocations to python/cli.py, or defer deletion of helper scripts still required by ship-pr.sh until the legacy path is retired
  - From Codex-Pragmatic: Add scripts/ship-pr.sh and scripts/implement-finalize.sh external helper invocations to the B1 cutover, or explicitly keep any helper they still call until E1; do not delete a helper while a live bash caller remains.
  - From Cursor-Requirements: Add an explicit retain-until-E1 list for every script still invoked from ship-pr.sh (or defer their manifest deletion until E1); narrow B1 deletion to scripts with zero ship-pr callers unless E1 is a hard prerequisite
  - From Codex-Requirements: Expand the sweep to top-level scripts/*.sh, scripts/*.md, agent-lint.toml, and Makefile/docs entries; explicitly rewire known callers before manifest deletion
  - From Cursor-dyn-call-site-sweep: Add an explicit scripts/*.sh cutover table (or extend the sweep surface) covering every non-ship-pr root script that invokes an absorbed helper, plus scripts/test-implement-structure.sh pins that still require scripts/*.sh strings in skills/implement/SKILL.md.


### FINDING_2: git-commit/git-stage parity is marked present despite missing pathspec and multi-path behavior
- **Reviewer(s)**: Codex-Arch, Codex-Requirements
- **Severity**: important
- **Concern**: The plan treats git commit/stage support as already available, but the Python helper does not preserve the old `git-commit.sh`/`git-stage.sh` contracts for pathspec files, NUL-separated pathspecs, `--no-trailer`, multi-path staging, and safe recovery commits.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Mark these as gaps and add public git helpers for multi-path add plus commit-with-message/file/pathspec options; wire git_cli to those helpers and port test-git-commit-only semantics
  - From Codex-Requirements: Add a full importable git commit helper or extend the existing one to match git-commit.sh exactly, then have git commit CLI call it


### FINDING_3: count-commits cutover drops verifier status side channel and harness coverage
- **Reviewer(s)**: Codex-Arch, Cursor-Edge, Codex-dyn-call-site-sweep
- **Severity**: important
- **Concern**: Rewiring `verify-skill-called.sh` to a count-only CLI would lose the `COUNT_COMMITS_STATUS_FILE` / status-token contract used to fail closed on missing refs or git errors. Related tests and docs still directly depend on the sourced bash library.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Specify that git count-commits preserves COUNT_COMMITS_STATUS_FILE or otherwise returns both count and status, then update verify-skill-called and its tests to consume that contract
  - From Cursor-Edge: Specify git count-commits parity with lib-count-commits.sh status tokens (CLI flag or KV) and update verify-skill-called.sh plus scripts/test-verify-skill-called.sh Section 5 to exercise the CLI path instead of sourcing the deleted library
  - From Codex-dyn-call-site-sweep: Add scripts/test-verify-skill-called.sh and its .md contract to the cutover: remove direct lib sourcing, assert the new git count-commits CLI through verify-skill-called, and update docs before deleting the library


### FINDING_4: Harness, manifest, Makefile, docs, and prose-reference cleanup is incomplete
- **Reviewer(s)**: Codex-Arch, Codex-Innovation, Codex-Pragmatic, Cursor-Requirements, Codex-Requirements, Codex-dyn-call-site-sweep
- **Severity**: important
- **Concern**: The deletion/stale-reference plan misses tracked harnesses, `.md` siblings, Makefile targets, agent-lint rows, docs, and bare basename prose references for absorbed scripts. This can leave `make lint`, `lint-retired-scripts`, or migrated-script validation red, or silently drop parity coverage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Expand the plan to inventory every tracked reference to retired paths, port/delete/update those harnesses and structural tests, and remove or update their Makefile targets before the manifest/lint gate
  - From Codex-Innovation: Append every deleted path to migrated-scripts.tsv, including md siblings and harness md files, and explicitly remove or retarget the omitted Makefile and agent-lint entries while porting those harness semantics to pytest
  - From Codex-Pragmatic: Expand the stale-reference step beyond skills/docs/Makefile to all tracked files reported by lint-retired-scripts; update or remove these surviving references while preserving tests with runtime-built CLI paths.
  - From Cursor-Requirements: Extend deletions to all B1-related test-* harnesses and .md siblings; port semantics to pytest; drop Makefile shard targets and agent-lint.toml allowlist rows for retired harnesses
  - From Codex-Requirements: Add those harnesses and their md siblings to the parity, pytest-port, deletion, manifest, Makefile, docs, and agent-lint cleanup steps
  - From Codex-dyn-call-site-sweep: Add scripts/test-git-commit-only.sh and scripts/test-rebase-push-{keep-on-conflict,force-lease,fork-mode,no-push-fetch-retry}.sh to the pytest-port/delete list, then update or remove their Makefile targets and docs/linting rows
  - From Codex-dyn-call-site-sweep: Add an explicit absorbed-basename prose sweep for the scoped files and enumerate/update the current bare-name references to CLI verbs or deliberate historical exceptions


### FINDING_5: check-main-sync contract is underspecified and misclassified
- **Reviewer(s)**: Cursor-Edge, Codex-dyn-contract-mapping
- **Severity**: important
- **Concern**: The plan does not preserve the full `check-main-sync.sh` safety contract, including dirty-tree refusal, log-only commit guards, hard-reset error handling, `SYNC_STATUS`, and non-zero exit mappings. Treating it like an always-exit-0 KV verb could allow unsafe continuation after fail-closed sync problems.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Edge: Document and test 1:1 parity with check-main-sync.sh guard chain in python/git.py check_main_sync and git check-main-sync CLI tests before deleting the bash script
  - From Codex-dyn-contract-mapping: Revise the plan so git check-main-sync preserves SYNC_STATUS plus exit codes 0/1/2, and add parity tests for blocked and probe-error cases


### FINDING_6: snapshot-untracked must preserve always-exit-0 failure behavior
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Concern**: The plan omits the legacy `snapshot-untracked.sh` behavior of returning 0 on operational failures while deleting the output file, which downstream baseline logic relies on.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Edge: Bind snapshot_untracked/git snapshot-untracked to always return 0 delete output on operational failure and preserve argument-error no-touch behavior from snapshot-untracked.sh


### FINDING_8: checkpoint-probe uses the wrong rebase KV grammar
- **Reviewer(s)**: Codex-Edge, Codex-Pragmatic
- **Severity**: important
- **Concern**: The plan introduces or documents `CHECKPOINT_RESULT` instead of preserving the existing `REBASE_OUTCOME`/`REBASE_ERROR`/`CONFLICT_FILES` contract used by implement steps and checkpoint routing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Edge: Preserve the current checkpoint KV grammar: `REBASE_OUTCOME=ok|skipped|conflict|failed`, `SKIPPED_ALREADY_*`, `CONFLICT_FILES`, `REBASE_ERROR`, plus the phantom tail keys; do not introduce `CHECKPOINT_RESULT`
  - From Codex-Pragmatic: Mirror the documented KV grammar exactly; keep check_phantom_dirty side-effect-free with STATUS/REASON/PHANTOM_COUNT/PHANTOM_PATHS_FILE, and perform execution-issues appends only in probe_with_warn after parsing.


### FINDING_9: gh-run-logs is mapped to the wrong backing behavior
- **Reviewer(s)**: Codex-Innovation, Cursor-dyn-contract-mapping, Codex-dyn-contract-mapping
- **Severity**: important
- **Concern**: The plan maps `gh-run-logs` to a full-log reader instead of the failed-log contract: `--log-failed`, pointer header, tail-100 cap, redaction, and in-progress exit 3 semantics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Add a dedicated gh failed-run-logs helper or change the mapping for this verb; cover the pointer line, tail -100 cap, --log-failed, and exit 3 detection in python/test_gh_cli.py
  - From Cursor-dyn-contract-mapping: Point gh run-logs at ci_monitor.collect_failed_logs (or add a thin gh.run_logs_failed wrapper with the same behavior) and map state in_progress/error/ready to exits 3/1/0 in gh_cli run-logs.
  - From Codex-dyn-contract-mapping: Add a gh.run_failed_log_read or CLI-specific wrapper that exactly mirrors scripts/gh-run-logs.sh before deleting the script


### FINDING_10: phantom probe contract names the wrong external path key and side-effect layer
- **Reviewer(s)**: Codex-Innovation, Codex-Pragmatic
- **Severity**: important
- **Concern**: The phantom plan preserves internal `NEW_UNTRACKED_PATHS_FILE` rather than the external `PHANTOM_PATHS_FILE`/`PHANTOM_COUNT` contract, and risks moving warning append side effects into the wrong layer.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Update the plan to preserve PHANTOM_STATUS, optional PHANTOM_REASON, PHANTOM_COUNT, PHANTOM_PATHS_FILE, and optional PHANTOM_APPEND_WARN_ERROR; treat NEW_UNTRACKED_PATHS_FILE as private input from check-mid-run-dirty-tree only
  - From Codex-Pragmatic: Mirror the documented KV grammar exactly; keep check_phantom_dirty side-effect-free with STATUS/REASON/PHANTOM_COUNT/PHANTOM_PATHS_FILE, and perform execution-issues appends only in probe_with_warn after parsing.


### FINDING_11: rebase-push is marked present against a function that lacks script parity
- **Reviewer(s)**: Codex-Pragmatic, Codex-dyn-contract-mapping
- **Severity**: important
- **Concern**: The planned `rebase-push`/checkpoint backing function does not implement the legacy flag matrix, conflict preservation behavior, KV output, or exit-code mapping required by existing implement conflict-resolution branches.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: Add a minimal exact-parity rebase-push primitive/CLI for --continue, --no-push, --skip-if-pushed, and --keep-on-conflict, then have push checkpoint-probe compose that primitive plus the phantom probe.
  - From Codex-dyn-contract-mapping: Add a script-parity rebase-push primitive or mark this row as a gap; preserve the existing 0/1/2/3 exit mapping and old flags explicitly


### FINDING_12: create-branch --branch creation mode is missing from the plan
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Concern**: The plan only calls out create-branch check/classification behavior, but bootstrap depends on the `--branch` creation mode, output keys, validation, fetch behavior, and exit codes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Add the --branch contract to the plan and tests: success, existing branch, prefix validation, fetch failure, and exact output/exit codes


### FINDING_13: check-remote-branch structured RC and ERROR fields would be lost
- **Reviewer(s)**: Codex-dyn-contract-mapping
- **Severity**: important
- **Concern**: Promoting the private finalize helper as-is cannot preserve the old `check-remote-branch.sh` KV contract, which emits `STATE`, `RC`, and redacted `ERROR` on transport failures.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-contract-mapping: Add a public structured remote-branch result with state, rc, and error text, then have finalize use only state while the CLI emits the full old KV contract


### FINDING_14: git-sync-local-main exit and fetch contract is inaccurate
- **Reviewer(s)**: Codex-dyn-contract-mapping
- **Severity**: important
- **Concern**: The plan adds behavior not present in the old script, including a non-existent exit 2 and an implied fetch path, instead of preserving the cached-base-ref update contract and 0/1 exit mapping.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-contract-mapping: Revise the plan to preserve the old no-fetch RESULT=updated|absent|already_current contract and 0/1 exit mapping, or explicitly justify and test any intentional contract change


### FINDING_15: finalize parity tests still patch the deleted private helper
- **Reviewer(s)**: Codex-dyn-contract-mapping
- **Severity**: important
- **Concern**: The finalize repoint step omits an existing pytest monkeypatch of the private remote-branch helper; deleting or replacing that helper without updating the test will break `make py-test`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-contract-mapping: Include the existing finalize parity test in the mechanical repoint: patch finalize.git.remote_branch_state, or adjust it to the new structured helper shape


### FINDING_16:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: plan.txt:22-27,171-176
- **Concern**: [SCOPE-REDUCTION] Deletion list conflicts with ship-pr.sh out-of-scope rule. Scenario: Plan forbids editing scripts/ship-pr.sh until E1 but lists for deletion scripts ship-pr still shells out to (resolve-repo, git-commit, git-push, create-pr, ci-behind-count, git-force-push, ci-rerun-failed, ci-failed-jobs, rebase-push, git-sync-local-main, ci-wait, merge-pr). Deleting them breaks LARCH_SHIP_PR_IMPL=bash while the skill still documents that path
- **Proposed resolution**: Add an explicit retention carve-out: do not delete any script still invoked from ship-pr.sh until E1; narrow Deletions to scripts with zero ship-pr callers (or document that bash ship is intentionally broken post-B1)




### FINDING_1: Retired-script deletion gate mishandles ship-pr/retained-bash references
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Codex-Requirements, Codex-dyn-retention-boundary
- **Severity**: important
- **Concern**: The plan’s deletion/manifest gate relies on `lint-retired-scripts` assumptions that are either inconsistent with `ship-pr.sh` retention or unable to catch non-literal helper references such as `$SCRIPT_DIR/foo.sh`. This can either block valid deletions on retained ship-pr references, or worse, allow deletion of helpers still used by the retained bash path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add an explicit plan step to exclude scripts/ship-pr.sh from migration_lint scanning until E1 (or document that the stale-reference sweep may rewrite comment-only path literals in ship-pr.sh before manifest append)
  - From Cursor-Innovation: Replace basename/outside-ship-pr wording with: no manifest entry or file deletion until zero repo-wide references including ship-pr.sh; deferred scripts stay on disk until E1
  - From Codex-Requirements: Add an explicit rg-based absorbed-basename stale-reference gate excluding scripts/ship-pr.sh, the manifest, and scripts intentionally deferred to E1 before deletion, or extend migration_lint for this B1 set.
  - From Codex-dyn-retention-boundary: Add a B1 plan step to update python/migration_lint.py and tests to match repo-relative, $SCRIPT_DIR/basename, and bare helper-call forms; any match in scripts/ship-pr.sh must block deletion and force E1 deferral, not be ignored


### FINDING_2: Call-site/stale-reference sweep omits tracked .claude and script-doc surfaces
- **Reviewer(s)**: Codex-Arch, Codex-Edge, Codex-Pragmatic, Codex-Requirements
- **Severity**: important
- **Concern**: The cutover sweep does not include all tracked surfaces that load or are scanned in this repo, especially `.claude/skills/**`, `.claude/rules/**`, and retained `scripts/*.md` contract docs. This can leave live non-ship consumers on deleted bash helpers or make `lint-retired-scripts` fail after manifest updates.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Expand the cutover sweep to include .claude/skills/**/*.md, .claude/skills/**/scripts/*.sh, .claude/rules/*.md, and related .claude tests/docs; retarget those callers to python3 cli.py before deletion/manifest updates.
  - From Codex-Edge: Broaden the call-site/stale-reference sweep to all tracked files that lint-retired-scripts scans, explicitly including .claude/skills/**, .claude/rules/**, and retained scripts/*.md/test*.md contracts; retarget those references to cli.py or defer deletion/manifest entries until they are gone.
  - From Codex-Pragmatic: Expand the cutover/stale-reference sweep to all tracked files scanned by lint-retired-scripts, or explicitly include root scripts/*.md plus .claude/rules and .claude/skills paths, before manifesting deletions
  - From Codex-Requirements: Extend the sweep and tests to .claude/skills/** and .claude/rules/**, converting absorbed-helper calls to the new cli.py verbs and updating release tests/rule frontmatter accordingly.


### FINDING_3: check-main-sync is incorrectly grouped with always-exit-0 verbs
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Concern**: The edge-case plan mislabels `check-main-sync` as always-exit-0, but existing callers depend on distinct exit codes for blocked and probe-error states.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Edge: Remove check-main-sync from the always-exit-0 list; keep F5 exit 0/1/2 and SYNC_STATUS tokens explicit in git_cli.py and test_git_cli.py


### FINDING_5: Python call sites still invoke bash helpers targeted for absorption
- **Reviewer(s)**: Codex-Innovation, Cursor-Pragmatic
- **Severity**: important
- **Concern**: The call-site inventory omits Python subprocess callers in `python/checks.py` and `python/ci_monitor.py`, leaving live Python paths shelling out to helpers such as `git-commit.sh` and `rebase-push.sh` after the claimed hard cutover.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Include python/checks.py and python/ci_monitor.py in the updated-file list and replace those helper subprocess calls with the new typed functions or cli.py verbs; update their existing pytest expectations
  - From Cursor-Pragmatic: Add python/ci_monitor.py (and python/test_ci_monitor.py) to Files to modify: replace git-commit.sh/rebase-push.sh runner.run calls with importable git/rebase-push parity functions; document that python/ internals import libraries directly not cli.py subprocess


### FINDING_6: create-pr parity is incomplete and omits PR_TITLE/existing-PR semantics
- **Reviewer(s)**: Codex-Pragmatic, Cursor-dyn-kv-emission-split, Codex-dyn-kv-emission-split
- **Severity**: important
- **Concern**: The plan marks `create-pr` as already covered by `pr.ensure_pr`, but that function is ship-pr-specific and does not preserve the standalone `create-pr.sh` CLI/KV contract, including `PR_TITLE`, existing-PR behavior, and exit mapping.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: Mark create-pr partial/gap and add a dedicated create-pr parity function/CLI that accepts the old flags, keeps existing-PR no-body-update behavior, emits PR_NUMBER/PR_URL/PR_TITLE/PR_STATUS, and maps exits 0/1/2
  - From Cursor-dyn-kv-emission-split: Mark **partial**; extend `ensure_pr` or `pr_cli` `create` to emit `PR_TITLE=` on every success path (new + existing PR), including existing-PR title fetch parity
  - From Codex-dyn-kv-emission-split: Carry the title through PrResult or the CLI wrapper and require PR_TITLE emission/tests for created, existing, and create-conflict recovery paths


### FINDING_7: ci behind-count promotion misses fetch/no-fetch and fail-open KV contract
- **Reviewer(s)**: Codex-Pragmatic, Cursor-dyn-kv-emission-split, Codex-dyn-kv-emission-split
- **Severity**: important
- **Concern**: The plan treats `_behind_count` as directly promotable, but the bash helper validates inputs, fetches by default, supports `--no-fetch`, and fails open by emitting `BEHIND_COUNT=0` rather than surfacing probe errors or `None`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: Add a public ci_monitor.behind_count wrapper that validates base labels, performs git fetch unless --no-fetch is set, converts all probe failures/non-integers to 0, and have ci_cli emit BEHIND_COUNT with exit 0
  - From Cursor-dyn-kv-emission-split: Mark **partial/gap**; add a dedicated `behind_count` helper with `--no-fetch`, charset guard, fail-open `0`, usage exit **2**, and KV emission — do not promote `_behind_count` verbatim
  - From Codex-dyn-kv-emission-split: Add a public parity wrapper for ci behind-count that validates base labels, optionally fetches, maps failures to BEHIND_COUNT=0, and always emits the KV contract


### FINDING_8: Files-to-modify omits typed-library modules needed for parity gaps
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Concern**: The plan lists CLI-facing work but omits required updates to `python/push.py`, `python/rebase.py`, and `python/pr.py` for parity gaps such as force-push, rebase-push, create-branch, and create-pr.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Add UPDATED rows for python/push.py (force-push exits) python/rebase.py (F11 rebase-push --continue/--no-push/--skip-if-pushed/--keep-on-conflict primitive) and python/pr.py (F12 create-branch --check/--branch); keep *_cli.py as thin argparse wrappers only


### FINDING_10: Deferred-to-E1 retained bash closure is incomplete
- **Reviewer(s)**: Codex-dyn-call-site-sweep, Cursor-dyn-retention-boundary, Codex-dyn-retention-boundary
- **Severity**: important
- **Concern**: The plan’s retention carve-out names only some direct ship-pr helpers and omits direct/transitive dependencies such as `gh-pr-body-update`, `gh-run-logs`, `github-remote-repo`, `ci-status`, and `ci-decide`. Deleting those before rewiring retained bash callers would break `LARCH_SHIP_PR_IMPL=bash`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-call-site-sweep: Add an explicit call-site cutover/deletion rule for retained absorbed scripts: either repoint scripts/ci-wait.sh to python3 cli.py ci status/decide and scripts/resolve-repo.sh to python3 cli.py gh remote-repo before deleting their dependencies, or defer scripts/ci-status.sh, scripts/ci-decide.sh, and scripts/github-remote-repo.sh to E1 alongside the retained bash callers.
  - From Cursor-dyn-retention-boundary: Add an explicit Deferred-to-E1 table with the full ship-pr transitive closure (direct + one-hop through retained helpers): resolve-repo git-commit git-push create-pr ci-behind-count git-force-push ci-rerun-failed ci-failed-jobs rebase-push git-sync-local-main ci-wait merge-pr gh-pr-body-update gh-run-logs ci-status ci-decide. Require grep of scripts/ship-pr.sh plus every script in that set for $SCRIPT_DIR/*.sh references before any B1 deletion.
  - From Codex-dyn-retention-boundary: Make the deferred set generated from the ship-pr plus retained-helper call graph, or explicitly defer gh-pr-body-update, gh-run-logs, github-remote-repo, ci-status, and ci-decide until E1 unless the retained callers are rewired in B1 before deletion


### FINDING_13: snapshot-untracked is incorrectly described as a status-KV verb
- **Reviewer(s)**: Cursor-dyn-kv-emission-split
- **Severity**: important
- **Concern**: `snapshot-untracked.sh` has a file-only contract and emits no status KVs, so grouping it with always-exit-0 status-KV verbs would create the wrong CLI behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-kv-emission-split: Remove `snapshot-untracked` from the KV status bucket; document file-only contract (always exit **0**, delete output on op failure, no touch on arg errors)


### FINDING_14: git branch-info parity requires exact keys and detached-HEAD support
- **Reviewer(s)**: Cursor-dyn-kv-emission-split, Codex-dyn-kv-emission-split
- **Severity**: important
- **Concern**: The plan marks branch-info as covered by current-branch logic, but the bash contract emits `HEAD_SHA` and `CURRENT_BRANCH`, and supports detached HEAD by emitting an empty `CURRENT_BRANCH`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-kv-emission-split: In `git_cli` `branch-info`, emit exactly `HEAD_SHA` + `CURRENT_BRANCH`; add pytest asserting those keys (not `BRANCH=`)
  - From Codex-dyn-kv-emission-split: Use try_current_branch for branch-info, emit HEAD_SHA and CURRENT_BRANCH, and add detached-HEAD parity coverage


### FINDING_15: ci status lacks gh-pr-checks text fallback parity
- **Reviewer(s)**: Codex-dyn-kv-emission-split
- **Severity**: important
- **Concern**: `ci status` is marked have, but `gather_status` only consumes JSON and omits the bash fallback to plain `gh pr checks` text output, which can change fail/pass/pending decisions.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-kv-emission-split: Change ci status to partial and add the text fallback plus parity tests before exposing the CLI verb


### FINDING_16: ci failed-jobs Python path lacks bash diagnostic sanitization
- **Reviewer(s)**: Codex-dyn-kv-emission-split
- **Severity**: important
- **Concern**: The Python failed-jobs implementation does not preserve bash sanitization of job names and summary lists, allowing control bytes, tabs, or newlines to corrupt TSV/KV output or logs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-kv-emission-split: Port the sanitize_diagnostic_line and sanitize_list behavior into the Python failed-jobs CLI path and test TSV plus FAILED_JOBS_* output with hostile job names




### FINDING_1: Root bash caller sweep is incomplete
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: The plan’s closed list of root bash call sites can miss live callers of absorbed helpers, so deleting the helper scripts after following only the enumerated list could break standalone scripts that still invoke bash paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Replace the enumerative bullet with a mechanical prerequisite: rg all absorbed basenames under scripts/ skills/ .claude/ docs/ Makefile (excluding ship-pr.sh per carve-out), cut over every hit, then run lint-retired-scripts before deletion.


### FINDING_2: Rebase macro structural harness pins are missing from retarget scope
- **Reviewer(s)**: Cursor-Arch, Cursor-Requirements
- **Severity**: important
- **Concern**: The plan omits `scripts/test-implement-rebase-macro.sh` from the structural pin updates, so the CLI cutover can make product code correct while leaving lint red due to stale required strings/counts in that harness.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add scripts/test-implement-rebase-macro.sh (and refresh expected counts/paths for cli.py) to the structural+lint pins section and to the parity gate before deleting rebase-checkpoint-probe.sh / phantom-probe-with-warn.sh.
  - From Cursor-Requirements: Under structural + lint pins, explicitly require retargeting scripts/test-implement-rebase-macro.sh (and its contract doc if present) to the new cli.py push checkpoint-probe invocation form, alongside test-implement-structure.sh


### FINDING_3: Root script CLI path derivation is not cwd/env safe
- **Reviewer(s)**: Codex-Arch, Codex-Edge, Codex-Innovation
- **Severity**: important
- **Concern**: Root bash callers are planned with either a literal `CLAUDE_PLUGIN_ROOT` path or unresolved `python3 cli.py`, but several scripts run standalone or from arbitrary cwd without that env initialized; the cutover can fail before emitting expected contract output.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Amend the plan so root bash callers define PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$SCRIPT_DIR/.." && pwd -P)}" or invoke "$SCRIPT_DIR/../python/cli.py"; keep the literal "${CLAUDE_PLUGIN_ROOT}/python/cli.py" form for skill/doc surfaces where that env is guaranteed.
  - From Codex-Edge: For root bash callers, derive a local plugin root or CLI path from SCRIPT_DIR, e.g. PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$SCRIPT_DIR/.." && pwd -P)}"; python3 "$PLUGIN_ROOT/python/cli.py" ...; reserve the literal CLAUDE_PLUGIN_ROOT form for markdown/orchestrator call sites that guarantee it.
  - From Codex-Innovation: Compute PLUGIN_ROOT from `${CLAUDE_PLUGIN_ROOT:-$(cd "$SCRIPT_DIR/.." && pwd -P)}` and invoke `python3 "$PLUGIN_ROOT/python/cli.py" git count-commits`; keep the cwd-neutral commit-delta test coverage


### FINDING_4: `ci wait` is marked complete but only the inner poll loop exists
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Concern**: The Python `poll_ci` surface does not cover the full `ci-wait.sh` wrapper contract, including atomic output publishing, `.done` sentinel behavior, ordered KVs, suspend-aware iteration accounting, and progress stderr.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Edge: Reclassify ci wait to partial/gap; require ci_cli wait to port scripts/ci-wait.sh end-to-end (including --output-file + .done on trap-deliverable exits) with pytest/harness parity, using poll_ci only as the inner loop


### FINDING_5: `git count-commits` must preserve raw stdout plus status side channel
- **Reviewer(s)**: Cursor-Edge, Cursor-Pragmatic
- **Severity**: important
- **Concern**: `verify-skill-called.sh` depends on `lib-count-commits.sh` printing only the integer count on stdout while reporting status through `COUNT_COMMITS_STATUS_FILE`; a KV-only or stdout-only CLI port would break commit-delta verification.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Edge: Document and test that git count-commits mirrors lib-count-commits.sh env side-channel (write ok/missing_main_ref/git_error to COUNT_COMMITS_STATUS_FILE); extend scripts/test-verify-skill-called.sh Section 5 to assert all three statuses through the CLI path
  - From Cursor-Pragmatic: Define git count-commits as a raw-stdout verb (integer on stdout, status via --status-file or COUNT_COMMITS_STATUS_FILE env) matching the sourced library; do not use quiet_init-only emit_kv on fd3 for the count line; extend F3 tests and test-verify-skill-called.sh Section 5


### FINDING_6: Retained bash deletion closure and reference detection are insufficient
- **Reviewer(s)**: Cursor-Edge, Codex-Requirements, Cursor-dyn-closure-audit
- **Severity**: important
- **Concern**: The plan’s deferred-to-E1 retention and deletion gates can miss retained bash dependencies reached transitively or through `$SCRIPT_DIR/<basename>.sh`/bare invocation forms, allowing B1 to delete helpers still needed by legacy bash paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Edge: Extend Deferred-to-E1 with explicit retention edges (ci-wait→ci-status/ci-decide, resolve-repo→github-remote-repo, create-pr→resolve-repo) and require closure generation to walk one-hop callers among retained scripts, not only ship-pr.sh
  - From Codex-Requirements: Revise the sequence so candidate grep/rg over repo-relative, SCRIPT_DIR, and bare forms is the pre-delete gate, then delete, append the manifest, and run lint-retired-scripts as the post-delete gate; add a pre-retirement lint mode only if the plan wants this automated in migration_lint
  - From Cursor-dyn-closure-audit: Add check-remote-branch to Deferred-to-E1 OR name it in an explicit implement-finalize cutover gate (must repoint before any check-remote-branch deletion); do not rely on the current 17-script list as complete
  - From Cursor-dyn-closure-audit: Implement the planned $SCRIPT_DIR/<basename>.sh detection before any B1 bash deletion; add pytest proving $SCRIPT_DIR/resolve-repo.sh flags scripts/resolve-repo.sh retirement
  - From Cursor-dyn-closure-audit: Build closure by walking all $SCRIPT_DIR/*.sh callees from ship-pr.sh recursively (including implement-finalize.sh and lint-fix-loop.sh), not one-hop through deferred scripts only
  - From Cursor-dyn-closure-audit: Scope bare detection to invocation forms only ($SCRIPT_DIR/<basename>.sh, optional source/. prefix, word-boundary basename.sh not preceded by /); keep cross-directory basename false-positive test


### FINDING_7: `check-main-sync` parity is underspecified and mis-tagged
- **Reviewer(s)**: Cursor-Edge, Cursor-dyn-contract-table
- **Severity**: important
- **Concern**: The plan does not preserve `preflight.sh`’s asymmetric handling of `check-main-sync` exit 2 and `SYNC_STATUS=probe-error`, and one edge-case reference points implementers at the wrong finding ID.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Edge: Add an explicit parity requirement tying git check-main-sync to preflight.sh probe-error fail-open vs fail-closed branches (and port scripts/test-check-main-sync.sh cases that assert exit 2 + SYNC_STATUS=probe-error)
  - From Cursor-dyn-contract-table: Replace `(0/1/2, F3)` with `(0/1/2, F5)` in Edge cases line 188


### FINDING_8: `check-phantom-dirty` and `phantom-probe` contracts are mixed
- **Reviewer(s)**: Codex-Innovation, Codex-Requirements, Codex-dyn-contract-table
- **Severity**: important
- **Concern**: The plan conflates the side-effect-free `check-phantom-dirty` contract with the wrapper-level `phantom-probe`/checkpoint contract, risking wrong KV names, unexpected append side effects, or missed append failure reporting.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Split the contracts explicitly: `git check-phantom-dirty` emits only STATUS/REASON/PHANTOM_COUNT/PHANTOM_PATHS_FILE and never PHANTOM_APPEND_WARN_ERROR; `git phantom-probe` and checkpoint tails emit PHANTOM_* plus optional PHANTOM_APPEND_WARN_ERROR
  - From Codex-Requirements: Remove PHANTOM_APPEND_WARN_ERROR from the check-phantom-dirty row; state that check-phantom-dirty emits only STATUS/REASON/PHANTOM_COUNT/PHANTOM_PATHS_FILE, while phantom-probe and checkpoint-probe emit PHANTOM_STATUS tail plus optional PHANTOM_APPEND_WARN_ERROR
  - From Codex-dyn-contract-table: Separate the edge case by verb: `git check-phantom-dirty` emits `STATUS`/`REASON` plus `PHANTOM_COUNT`/`PHANTOM_PATHS_FILE`; `git phantom-probe` emits `PHANTOM_STATUS`/`PHANTOM_REASON` plus phantom tail keys and optional `PHANTOM_APPEND_WARN_ERROR`.


### FINDING_9: `probe_with_warn` append-warning behavior is unspecified
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: The plan does not specify how Python `phantom.probe_with_warn` writes `execution-issues.md` or folds append failures, so the wrapper can lose `lib-phantom-probe.sh` behavior even if dirty-tree probing works.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Explicitly require phantom.probe_with_warn to subprocess scripts/append-execution-issue.sh (same entry templates and failure folding as lib-phantom-probe.sh) or port that helper with byte-identical behavior; add pytest coverage for append failure


### FINDING_10: `git-push` is marked have without script-parity coverage
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Concern**: Existing Python push code is not equivalent to `scripts/git-push.sh`, so marking it complete can drop required stdout, retry, exit-code, and stderr-dedup semantics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Mark git-push partial/gap; add a typed no-arg git-push parity function and CLI wrapper preserving BRANCH output, detached checks, three attempts, deduped stderr, and final push exit; port scripts/test-git-push.sh semantics to pytest


### FINDING_13: Typed functions for `amend-add` and `rebase-abort` are missing
- **Reviewer(s)**: Codex-dyn-contract-table
- **Severity**: important
- **Concern**: The plan requires thin CLI wrappers but does not add underlying typed functions for two partial git verbs, which can leave them unimplemented or push real logic into `git_cli.py`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-contract-table: Add typed library functions for amend-add and idempotent rebase-abort in `python/git.py` or `python/rebase.py`, then have `git_cli.py` wrap them.


### FINDING_15:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/migration_lint.py:155-159
- **Concern**: [SCOPE-REDUCTION] Land migration_lint $SCRIPT_DIR/bare detection before any manifest append or bash deletion. Scenario: Current lint only substring-matches full paths like scripts/git-commit.sh; ship-pr and others reference $SCRIPT_DIR/git-commit.sh so a domain commit could append+delete while live $SCRIPT_DIR references remain undetected until E1
- **Proposed resolution**: Bind migration_lint.py upgrade + tests as the first B1 commit; gate every later deletion/manifest append on the upgraded linter


### FINDING_17:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/migration_lint.py:UPDATED
- **Concern**: [SCOPE-REDUCTION] bare helper-call matching risks F1 false positives. Scenario: Plan adds bare helper-call detection atop F1 full-path-only lint (python/migrated-scripts.tsv header); bare basename scans can flag unrelated mentions and block lint-retired-scripts like the run-analysis.sh incident
- **Proposed resolution**: Limit new matching to manifest full paths plus $SCRIPT_DIR/<basename>.sh derived from each manifest path; do not add repo-wide bare-basename substring matching; update docs/python-migration.md in the same change to stay consistent


### FINDING_18:
- **Reviewer(s)**: Codex-dyn-closure-audit
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:153-181; scripts/ship-pr.sh:976-978
- **Concern**: [SCOPE-REDUCTION] Deletion gate treats a non-live ship-pr comment as a blocker for git-current-branch.sh. Scenario: scripts/ship-pr.sh is left untouched, but line 976 contains the repo-relative text scripts/git-current-branch.sh. The plan also says migration_lint.py will detect repo-relative forms and make any match in ship-pr block deletion. Deleting scripts/git-current-branch.sh would then make lint-retired-scripts fail even though ship-pr does not invoke that helper; deferring it would under-deliver B1 deletion scope.
- **Proposed resolution**: Constrain the ship-pr deletion blocker to live invocation/source forms, or add a narrow allowlist for this comment, so git-current-branch.sh can be deleted while ship-pr remains untouched.




### FINDING_2: non-root bash callers need local root fallback, not env-only CLI paths
- **Reviewer(s)**: Codex-Arch, Codex-Edge, Codex-Innovation
- **Severity**: important
- **Concern**: The CLI path rule only gives cwd-safe root derivation to root `scripts/*.sh`, while the sweep includes bash helpers under `skills/**` and `.claude/skills/**` that are directly callable and already compute `PLUGIN_ROOT`, `LARCH_ROOT`, or `REPO_ROOT`. Replacing those call sites with literal `${CLAUDE_PLUGIN_ROOT}/python/cli.py` can fail when the env var is unset.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Revise the rule so every bash script caller, root or non-root, uses its existing SCRIPT_DIR/PLUGIN_ROOT/REPO_ROOT fallback to locate python/cli.py; reserve the literal CLAUDE_PLUGIN_ROOT form for markdown/orchestrator prose where the env is guaranteed.
  - From Codex-Edge: Amend the cutover rule so every bash file that already computes PLUGIN_ROOT, LARCH_ROOT, or REPO_ROOT invokes python3 "$PLUGIN_ROOT/python/cli.py" or the equivalent local root path. Reserve literal "${CLAUDE_PLUGIN_ROOT}/python/cli.py" for markdown/orchestrator snippets where rehydration guarantees the env var.
  - From Codex-Innovation: Classify bash files that already derive PLUGIN_ROOT like root scripts; use python3 "$PLUGIN_ROOT/python/cli.py" ... or an equivalent local-root fallback there, and reserve literal ${CLAUDE_PLUGIN_ROOT} for prompt prose/docs where the env is guaranteed




### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: <TMPDIR>/plan.txt:161-167
- **Concern**: Deferred-to-E1 table omits check-remote-branch.sh even though ship-pr still reaches it live via implement-finalize.sh. Scenario: Plan defers deletion unless implement-finalize is repointed (line 167) but implement-finalize.sh is not in Files to modify; only python/finalize.py is. Under LARCH_SHIP_PR_IMPL=bash, premature manifest append/deletion of check-remote-branch.sh breaks Step 8b postbump remote probe
- **Proposed resolution**: Add check-remote-branch.sh to Deferred-to-E1 explicitly; note implement-finalize.sh stays bash until E1; gate deletion on zero live callers including $SCRIPT_DIR/check-remote-branch.sh from implement-finalize.sh


### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-implement-rebase-macro.sh:154-176
- **Concern**: Structural harness still hard-pins deleted bash wrapper internals. Scenario: Plan line 159 says retarget pins to cli.py forms, but section (H) greps rebase-checkpoint-probe.sh for rebase_args and a single rebase-push.sh call. After B1 deletes the wrapper, make lint fails even if SKILL.md/step-7a cutover is correct
- **Proposed resolution**: Rewrite section (H) (and WRAPPER existence checks) to validate push checkpoint-probe CLI contract and SKILL.md/step-7a invocations; drop assertions on bash-only wrapper contents


### FINDING_3:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:110-117
- **Concern**: git count-commits CLI contract underspecified for verify-skill-called.sh side channel. Scenario: verify-skill-called.sh sets COUNT_COMMITS_STATUS_FILE before sourcing lib-count-commits.sh (scripts/verify-skill-called.sh:240-244). Mapping table mentions status-file (line 54) but NEW git_cli.py section does not pin the env var name or always-exit-0 behavior
- **Proposed resolution**: Spell out in git_cli/git.py: honor COUNT_COMMITS_STATUS_FILE exactly, write ok|missing_main_ref|git_error, raw integer stdout, exit 0; update verify-skill-called.sh to invoke CLI with the same env var pattern


### FINDING_5:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: <TMPDIR>/plan.txt:113-114; scripts/lib-phantom-probe.sh:17-33,76-103
- **Concern**: [SCOPE-REDUCTION] Phantom plan permits porting append-execution-issue logic in B1. Scenario: The absorbed surface is phantom probing; current library delegates all execution-issue writes to append-execution-issue.sh. Porting that helper duplicates a security-sensitive markdown mutation path and expands B1 beyond the listed git/gh/ci primitives.
- **Proposed resolution**: Make probe_with_warn call existing scripts/append-execution-issue.sh via proc only; remove the "or ports it byte-identically" option and leave append-execution-issue.sh out of B1.


### FINDING_6:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:85; scripts/gh-run-logs.sh:41-55; scripts/gh-run-logs.md:3-9
- **Concern**: [SCOPE-REDUCTION] gh run-logs adds redaction to a raw stdout contract. Scenario: Legacy gh-run-logs emits the pointer plus the raw last 100 lines and existing callers perform redaction where needed. Moving redaction into the migrated verb changes diagnostic output and can hide data before caller-owned processing.
- **Proposed resolution**: Keep gh run-logs parity to pointer header plus unredacted tail-100 and exits 0/1/3; keep redaction at existing downstream pipes/callers.


### FINDING_7:
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: plan.txt:161-167
- **Concern**: check-remote-branch is absent from the explicit Deferred-to-E1 retention table even though ship-pr still reaches it through implement-finalize.sh. Scenario: An implementer can treat only the 16 listed basenames as ship-pr blockers, delete scripts/check-remote-branch.sh after adding the Python verb, and break LARCH_SHIP_PR_IMPL=bash postbump when implement-finalize.sh still invokes the bash helper
- **Proposed resolution**: Add check-remote-branch to Deferred-to-E1 (or mark it delete-only-after-implement-finalize.sh CLI cutover in that table) and gate manifest append on zero live $SCRIPT_DIR/check-remote-branch.sh references outside ship-pr.sh comments


### FINDING_8:
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Focus area**: architecture
- **Location**: <TMPDIR>/plan.txt:113-114; scripts/append-execution-issue.sh:76-155
- **Concern**: [SCOPE-REDUCTION] The plan allows porting append-execution-issue.sh inside the phantom work even though B1 only absorbs lib-phantom-probe.sh and phantom-probe-with-warn.sh. Scenario: Porting the append helper expands the PR into an unrelated lock/atomic-write migration; a partial reimplementation can corrupt execution-issues.md or lose concurrent warning entries
- **Proposed resolution**: Remove the "or ports it byte-identically" option and require phantom.probe_with_warn to call the existing scripts/append-execution-issue.sh helper; defer that helper's Python migration to a separate issue


### FINDING_10:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/implement-finalize.sh:486-526
- **Concern**: Partial cutover for implement-finalize is implied but not listed in Files to modify/create. Scenario: `check-remote-branch.sh` is the only non-deferred script in implement-finalize's postbump gate; deleting it before repointing this sole live caller breaks `LARCH_SHIP_PR_IMPL=bash` Step 8b while deferred `rebase-push.sh` / `git-force-push.sh` must stay bash until E1
- **Proposed resolution**: Add `scripts/implement-finalize.sh` to UPDATED with an explicit partial cutover: repoint only `check-remote-branch.sh` to `python3 "$PLUGIN_ROOT/python/cli.py" git check-remote-branch`; keep deferred bash invocations unchanged until E1


### FINDING_11:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: plan.txt:113-114
- **Concern**: 1. [SCOPE-REDUCTION] Plan allows porting `scripts/append-execution-issue.sh` inside the phantom Python surface even though B1 only absorbs the listed git/gh/CI helpers. Scenario: Implementer may duplicate or alter the execution-issue append contract while migrating phantom probes, expanding the PR beyond B1 and risking changed warning formatting or failure folding for existing callers
- **Proposed resolution**: Remove the "or ports it byte-identically" option; require `probe_with_warn` to subprocess the existing `scripts/append-execution-issue.sh` and leave that script untouched.


### FINDING_12:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:56-57,161-167;scripts/implement-finalize.sh:486
- **Concern**: check-remote-branch.sh deletion path omits implement-finalize.sh cutover or E1 deferral. Scenario: Plan allows deleting scripts/check-remote-branch.sh after finalize.py gains git.remote_branch_state, but the only live bash caller is implement-finalize.sh postbump (invoked from ship-pr.sh on LARCH_SHIP_PR_IMPL=bash). check-remote-branch is absent from Deferred-to-E1 and implement-finalize.sh is not listed under Files to modify
- **Proposed resolution**: Add check-remote-branch to Deferred-to-E1 (simplest minimum-change) OR add ### UPDATED: scripts/implement-finalize.sh repointing the postbump gate to python3 "$PLUGIN_ROOT/python/cli.py" git check-remote-branch before bash deletion; update scripts/test-implement-finalize.sh stubs accordingly


### FINDING_13:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:178; scripts/ci-decide.sh:41-75; scripts/merge-pr.sh:20-22,83-95; scripts/ci-rerun-failed.sh:20-47; scripts/phantom-probe-with-warn.sh:12-29
- **Concern**: The plan’s “always-exit-0-with-status” list overstates several CLI contracts. Scenario: Following the plan as written can make `merge pr`, `ci rerun-failed`, `ci decide`, or `git phantom-probe` return success on invalid argv, drifting from the retired scripts’ usage-error exits required by exact parity
- **Proposed resolution**: Revise the edge-case table to say these commands exit 0 only after valid-argv status paths; preserve usage exits from the scripts (`merge-pr`/`ci-rerun-failed`/`ci-decide` exit 1, `phantom-probe-with-warn` exits 2) and pin those CLI invalid-argv cases in the new contract tests.


### FINDING_14:
- **Reviewer(s)**: Cursor-dyn-parity-map
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/git.py:575-644
- **Concern**: The push-domain row cites `force_push_recovery` in `push.py`, but the function already lives in `git.py`.. Scenario: An implementer adds a second force-push implementation in `push.py` instead of wiring `git.force_push_recovery` through `push_cli`, duplicating logic and drifting STATUS/exit mapping.
- **Proposed resolution**: Retarget the mapping row and `### UPDATED: python/push.py` note to `git.force_push_recovery`; keep `push_cli` as the thin KV/exit wrapper only.


### FINDING_15:
- **Reviewer(s)**: Cursor-dyn-parity-map
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/git.py:86-103
- **Concern**: The `lib-count-commits` row backs on `rev_count`/`rev_list_count`, but `rev_count` raises via `_ensure_success` on `git rev-list` failure.. Scenario: `scripts/lib-count-commits.sh` always prints an integer and exits 0, writing `git_error` to `COUNT_COMMITS_STATUS_FILE`; wrapping `rev_count` would break `verify-skill-called.sh` semantics.
- **Proposed resolution**: Keep the row **partial** but name the planned `count_commits` helper (main/origin/main fallback, forced 0, status side-channel) as the sole backing—not `rev_count`.


### FINDING_17:
- **Reviewer(s)**: Cursor-dyn-parity-map
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/git.py:558-643
- **Concern**: The `git-force-push` **partial** row lists bash STATUS literals only; `ForcePushResult.status` also emits `detached_head`, `branch_mismatch`, and `status_failed`.. Scenario: Bash maps detached HEAD and porcelain-probe failure to exit **2** with a narrower STATUS set; a CLI that emits only the four documented literals mis-classifies guard failures.
- **Proposed resolution**: Extend the partial row (or `push_cli` contract) with the full Python→bash STATUS/exit map for every `ForcePushResult.status`.


### FINDING_19:
- **Reviewer(s)**: Codex-dyn-parity-map
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:71; python/gh.py:150-164,688-709; scripts/gh-pr-body-update.sh:54-62,94-113; scripts/test-gh-pr-body-update.sh:43-70
- **Concern**: `gh-pr-body-update` is marked have, but `gh.pr_edit_body` is not parity. Scenario: Current Python requires `--repo`, always writes a redacted temp body, and lacks the transient retry pinned by the bash harness; a direct CLI wrapper would change PR body bytes, fail no-repo calls, or lose retry behavior
- **Proposed resolution**: Relabel this row partial and add/update a typed body-update parity function that accepts optional repo, preserves body-file contents, performs transient retry, and emits the existing UPDATED/ERROR exit contract


### FINDING_20:
- **Reviewer(s)**: Codex-dyn-parity-map
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:92; python/ci_monitor.py:273-288,349-356; scripts/ci-status.sh:27-35,76-83,198-203
- **Concern**: `ci-status` partial understates missing fail-open behavior. Scenario: The plan only calls out text fallback, but current `gather_status` returns `status=error` on `gh pr view` failure and can raise during squash-merge race probing, while the shell keeps default output and continues/fails open on those probes
- **Proposed resolution**: Add the ci-status parity work to preserve the shell trap/default contract: always emit the four KVs, reserve `CI_STATUS=error` for argument errors, and treat PR-view/git-log probe failures like the bash path


### FINDING_21:
- **Reviewer(s)**: Codex-dyn-parity-map
- **Severity**: important
- **Focus area**: architecture
- **Location**: plan.txt:58-63,125-126; python/push.py:41-73; python/git.py:575-584
- **Concern**: `git-force-push` is assigned to `push.py`, but the existing backing function is in `git.py`. Scenario: Following the plan literally either duplicates `force_push_recovery` in `push.py` or makes `push_cli` target a function that does not exist there, despite existing `pr.py` callers using `git.force_push_recovery`
- **Proposed resolution**: Revise the mapping and files section so `push force` reuses/extends `python/git.py::force_push_recovery`, or explicitly plan a move plus all import updates


### FINDING_23:
- **Reviewer(s)**: Cursor-dyn-deletion-gate
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:161-167; scripts/implement-finalize.sh:486
- **Concern**: Deferred-to-E1 omits check-remote-branch despite ship-pr closure via implement-finalize. Scenario: Recursive walk from ship-pr.sh reaches implement-finalize.sh postbump which live-invokes "$SCRIPT_DIR/check-remote-branch.sh" (line 486). The explicit retention list (line 165) omits it; line 167 says defer unless implement-finalize is repointed, but Files to modify has no scripts/implement-finalize.sh entry—only python/finalize.py (lines 143-144). An implementer can delete check-remote-branch.sh after Python finalize repoint alone, breaking LARCH_SHIP_PR_IMPL=bash Step 8b force-push gate.
- **Proposed resolution**: [SCOPE-REDUCTION] Add check-remote-branch to the line-165 Deferred-to-E1 list (simplest B1 path). If deletion in B1 is intended, add UPDATED scripts/implement-finalize.sh repointing line 486 to the git check-remote-branch CLI before any bash deletion.


### FINDING_24:
- **Reviewer(s)**: Cursor-dyn-deletion-gate
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:13-19; plan.txt:183; python/migration_lint.py:155-159; docs/python-migration.md:63-66
- **Concern**: migration_lint upgrade spec conflates F17 path precision with F18 ship-pr live-only filtering. Scenario: Line 183 tags both F17 and F18 as live-only migration_lint behavior, but F17 is no bare-basename / manifest+$SCRIPT_DIR-derived matching repo-wide (lines 14, 190-191) while F18 is ship-pr.sh live-invocation-only deletion blocking (lines 15-16). Current migration_lint.py only does full-path substring checks (lines 156-157); docs/python-migration.md still documents full-path-only (lines 63-66). Misread risks shipping substring upgrade without repo-wide $SCRIPT_DIR-derived matching, missing live bash callers like "$SCRIPT_DIR/resolve-repo.sh" after cutover slips.
- **Proposed resolution**: Split the contract in plan + docs/python-migration.md: repo-wide manifest path + $SCRIPT_DIR/<basename>.sh derived patterns for lint-retired-scripts; F18 live-invocation filter only for classifying ship-pr.sh retention/deletion blockers (separate from comment mentions at scripts/ship-pr.sh:976).



