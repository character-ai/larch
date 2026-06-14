### FINDING_1: Collector outer retry must accept `agent launch-review` and invoke Python (with STDERR_SINK parity)
- **Reviewer(s)**: Cursor-Arch, Cursor-Pragmatic, Cursor-dyn-retry-contract, Codex-dyn-retry-contract, Codex-dyn-sidecar-security, Codex-dyn-launcher-parity
- **Severity**: important
- **Concern**: The plan retargets `OUTER_LAUNCHER` to the token `agent launch-review`, but `launch_outer_retry_or_mark` in `scripts/collect-agent-results.sh` still only special-cases `agent launch-codex-exec` and a canonical `launch-review.sh` executable path. The new token hits the default reject arm, and the review retry branch still execs `$META_OUTER_LAUNCHER` as a shell path. Executable-path (`-x`/`-f`) validation also fails for the non-path token even if a Python retry command is added. Separately, the current retry path validates and forwards `STDERR_SINK` into `launch-review`; the proposed Python retry argv omits `--stderr-sink`, breaking retry diagnostics and metadata parity asserted by `test-collect-agent-retry.sh`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Mirror the codex-exec pattern: add a case arm for agent launch-review before basename/executable validation, set _outer_launcher_kind=review, and spawn python3 "$SCRIPT_DIR/../python/cli.py" agent launch-review with the existing retry argv. Update the invalid-metadata error text accordingly.
  - From Cursor-Arch: Branch review retries on _outer_launcher_kind=review (or OUTER_LAUNCHER=agent launch-review) and always invoke python3 ... agent launch-review; never exec META_OUTER_LAUNCHER directly for the new token.
  - From Cursor-Pragmatic: Add an explicit collect-agent-results step: when `OUTER_LAUNCHER` is exactly `agent launch-review`, skip path canonicalization and executable-file probes; validate only prompt file, workdir, and risk, then invoke the documented `python3` retry argv
  - From Cursor-dyn-retry-contract: Add an agent launch-review case arm (mirror agent launch-codex-exec): set _outer_launcher_kind=review, skip executable-path canonicalization, and launch python3 "$SCRIPT_DIR/../python/cli.py" agent launch-review with --tool "$META_TOOL" and the existing pinned --prompt-file / --risk / --stderr-sink args; update the fail-closed error string accordingly
  - From Codex-dyn-retry-contract: Add the existing _outer_sink_args forwarding to the new python3 python/cli.py agent launch-review retry argv, and keep the collect-agent retry sink-forwarding assertions updated for agent launch-review.
  - From Codex-dyn-sidecar-security: Pass the validated --stderr-sink argument in the agent launch-review retry argv, and keep or update the collect-agent-retry sink cases.
  - From Codex-dyn-launcher-parity: Add optional --stderr-sink "$META_STDERR_SINK" to the planned python3 ... agent launch-review retry argv after validation


### FINDING_2: Cursor dirty-tree recovery sidecar drops path streams review-core consumes
- **Reviewer(s)**: Codex-Arch, Codex-dyn-sidecar-security
- **Severity**: important
- **Concern**: The proposed Cursor switch from the baseline sidecar to `dirty-tree checkpoint` leaves `STATUS=dirty` without `TRACKED_PATHS_FILE` or `NEW_UNTRACKED_PATHS_FILE`. `recover_dirty_tree` in `python/legacy_review_shell/review-core.sh` then marks recovery taken but has no paths to discard, so reviewer-created or modified files can remain in the worktree after the launcher reports recovery.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Preserve the existing baseline sidecar contract for Cursor, or update dirty_tree checkpoint and recover_dirty_tree in the same plan to emit and consume equivalent path files before replacing snapshot-untracked
  - From Codex-dyn-sidecar-security: Keep the current baseline sidecar contract for Cursor in the Python launcher, or extend the Python dirty-tree path and review-core tests to emit and consume equivalent tracked/new-untracked path files before deleting the shell launcher.


### FINDING_3: `LARCH_TEST_TRAP_AFTER_INNER_DONE_FILE` hook parity missing on Cursor Python path
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: `scripts/launch-review.sh` sources `LARCH_TEST_TRAP_AFTER_INNER_DONE_FILE` when `LARCH_ALLOW_TEST_HOOKS=1` before `.inner.done` promotion. `test-dispatch-code-voters.sh` and `test-collect-agent-retry.sh` rely on that delayed-promotion race. A Python port without the same gated hook will fail those harnesses.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Port the exact gated source-file hook into the Cursor launch_review_main post-processing path (after inner completion, before .done promotion). Add pytest coverage or keep the existing shell harnesses green via make test-dispatch-code-voters / make test-collect-agent-retry.


### FINDING_4: `CURSOR_DEGRADED_RESPONSE` parity requires `eval validate-research-output` gate
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: Shell `launch-review.sh` only writes `CURSOR_DEGRADED_RESPONSE` after `python3 cli.py eval validate-research-output --validation-mode` fails on a high-token short `.result`. The plan lists the degraded marker but not this validator gate. Omitting the call changes which short Cursor payloads are degraded vs passed through.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Omitting the call changes which short Cursor payloads are degraded vs passed through. Call eval validate-research-output with the same thresholds as scripts/launch-review.sh before writing CURSOR_DEGRADED_RESPONSE; cover in python/test_launch_review.py.


### FINDING_5: `scripts/test-collect-agent-retry.sh` not retargeted for `agent launch-review`
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Cursor-Innovation, Cursor-Pragmatic, Codex-Pragmatic, Codex-Requirements, Cursor-dyn-launcher-parity
- **Severity**: important
- **Concern**: The plan runs `make test-collect-agent-retry` but does not list `scripts/test-collect-agent-retry.sh` for cutover updates. Fixtures still write `OUTER_LAUNCHER=$REPO_ROOT/scripts/launch-review.sh`, assert canonical executable-path validation, and expect the old fail-closed strings. After collector migration to `OUTER_LAUNCHER=agent launch-review` and Python replay, required retry checks fail or keep testing the retired shell contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add ### UPDATED: scripts/test-collect-agent-retry.sh. Rewrite happy-path metadata to OUTER_LAUNCHER=agent launch-review, expect python3 agent launch-review replay, and keep legacy-path negative cases explicit if still supported.
  - From Codex-Arch: Add these harnesses to the update list and retarget their fixtures and expected strings to agent launch-review and the new Codex auth inventory
  - From Cursor-Innovation: Add ### UPDATED: scripts/test-collect-agent-retry.sh: rewrite OUTER_LAUNCHER fixtures to agent launch-review, update expected error strings, and assert retries invoke python3 ... agent launch-review rather than executing a shell path
  - From Cursor-Pragmatic: Add `### UPDATED: scripts/test-collect-agent-retry.sh` (and `scripts/test-collect-agent-retry.md` if needed): fixtures use `OUTER_LAUNCHER=agent launch-review`, drop executable-path checks for review kind, stub via `PATH` + `python3` launcher like other migrated harnesses
  - From Codex-Pragmatic: Add scripts/test-collect-agent-retry.sh to the update list. Retarget valid outer metadata fixtures to OUTER_LAUNCHER=agent launch-review and update fail-closed assertions for the new canonical value.
  - From Codex-Requirements: Add UPDATED sections for these harnesses, retarget outer metadata and expected labels to agent launch-review, and keep codex-exec coverage unchanged
  - From Cursor-dyn-launcher-parity: Add ### UPDATED: scripts/test-collect-agent-retry.sh using OUTER_LAUNCHER=agent launch-review metadata and python3 cli.py retry expectations


### FINDING_6: Stale-reference sweep incomplete for retired `scripts/launch-review.sh`
- **Reviewer(s)**: Codex-Arch, Codex-Innovation, Cursor-Requirements, Codex-Requirements, Cursor-dyn-launcher-parity, Codex-dyn-launcher-parity
- **Severity**: important
- **Concern**: The feature retires `scripts/launch-review.sh` and appends it to `migrated-scripts.tsv`, but many tracked files still name the deleted launcher or old outer-launcher paths. Omitted surfaces include `AGENTS.md`, `.claude/rules/external-tool-launcher-parity.md`, `.claude/rules/launcher-argv-test-coverage.md`, `docs/installation-and-setup.md`, `docs/run-logs.md`, `docs/vendor-agent-diagnostics-audit.md`, `skills/design/references/plan-review.md`, `scripts/launch-codex-implement.md`, `scripts/launch-cursor-implement.md`, `.gitleaks.toml`, `skills/implement/scripts/test-cursor-implementer.md`, and comment-only lib shells. Testing strategy also omits `make lint-retired-scripts`, so `make lint` / definition-of-done can fail after deletion.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Add these files to the reference-update sweep, replacing active references with python/cli.py agent launch-review or marking only truly historical audit rows as historical
  - From Codex-Innovation: Add a lint-retired-scripts-driven sweep to update or reword every tracked scripts/launch-review.sh reference, including omitted docs/rules and shell harness metadata, or defer the migrated-scripts.tsv append until that sweep is in the same PR.
  - From Cursor-Requirements: Add make lint-retired-scripts to Testing strategy and a sweep step listing every remaining scripts/launch-review.sh and scripts/test-launch-review* reference outside the plan file list
  - From Codex-Requirements: Add these files to the plan's docs/reference update list and replace active script references with python/cli.py agent launch-review or neutral launcher wording where appropriate
  - From Cursor-dyn-launcher-parity: Add explicit sweep step plus ### UPDATED entries for skills/design/references/plan-review.md AGENTS.md docs/installation-and-setup.md scripts/test-lib-external-launcher-common.sh .gitleaks.toml .claude/rules/launcher-argv-test-coverage.md .claude/rules/external-tool-launcher-parity.md skills/implement/scripts/test-cursor-implementer.md docs/run-logs.md docs/vendor-agent-diagnostics-audit.md and comment-only lib shells
  - From Cursor-dyn-launcher-parity: Add ### UPDATED: skills/design/references/plan-review.md replacing launch-review.sh with python/cli.py agent launch-review for launch-failure capture
  - From Cursor-dyn-launcher-parity: Add make lint-retired-scripts to Testing strategy after migrated-scripts.tsv append
  - From Codex-dyn-launcher-parity: Add a targeted stale-reference step for these files; replace active references with python/cli.py agent launch-review or mark audit rows as historical if intentionally retained


### FINDING_7: Cursor dirty-tree detection switches from baseline compare to checkpoint-only (false positives on pre-existing dirt)
- **Reviewer(s)**: Cursor-Innovation, Cursor-Pragmatic
- **Severity**: important
- **Concern**: Current `scripts/launch-review.sh` captures `snapshot-untracked.sh` before launch and writes `MODE=baseline` via dirty-tree baseline at exit; checkpoint only flags any `git status --porcelain` dirt. Pre-existing untracked or dirty tracked state that predates the reviewer run stays non-dirty under baseline but becomes `STATUS=dirty` under checkpoint, so collect-findings sets `DIRTY_DETECTED` and auto-discards valid reviewer output on common dirty worktrees.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Keep Cursor post-run detection on dirty-tree baseline with a pre-launch untracked snapshot (parity with launch-review.sh), or document an explicit contract change and add a harness case for pre-existing worktree dirt
  - From Cursor-Pragmatic: Keep bash parity for Cursor: capture a pre-launch untracked baseline (or call `dirty-tree baseline` with that baseline file) at exit, not bare `dirty-tree checkpoint` alone


### FINDING_8: `scripts/test-dispatch-code-voters.sh` not updated for new parse-rate label
- **Reviewer(s)**: Cursor-Innovation, Cursor-Pragmatic, Codex-Requirements, Cursor-dyn-launcher-parity
- **Severity**: important
- **Concern**: The plan retargets `parse_rate_check_tool_label` in `python/voting.py` but not the dispatch-code-voters shell harness. The harness still greps `launch-review.sh --tool codex (voter parse-rate check)` while `voting.py` will emit `agent launch-review --tool codex`, breaking `make test-dispatch-code-voters` shards.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Add ### UPDATED: scripts/test-dispatch-code-voters.sh (and any stub launch-review hooks) to match the new site label and Python launcher argv shape
  - From Cursor-Pragmatic: Add `### UPDATED: scripts/test-dispatch-code-voters.sh` (and `.md` if assertions are documented there) to expect the new diagnostic label after `python/voting.py` changes
  - From Codex-Requirements: Add UPDATED sections for these harnesses, retarget outer metadata and expected labels to agent launch-review, and keep codex-exec coverage unchanged
  - From Cursor-dyn-launcher-parity: Add ### UPDATED: scripts/test-dispatch-code-voters.sh (and .md if pinned) to expect the new agent launch-review tool label


### FINDING_9: `scripts/test-lib-external-launcher-common.sh` auth inventory still pins deleted launcher
- **Reviewer(s)**: Codex-Arch, Cursor-Innovation, Cursor-Pragmatic
- **Severity**: important
- **Concern**: The plan updates Codex auth inventory docs but not the harness that enforces them. `test-lib-external-launcher-common.sh` still requires `launch-review.sh --tool codex` in `docs/external-reviewers.md`, `docs/configuration-and-permissions.md`, `SECURITY.md`, and `scripts/lib-external-launcher-common.md`; `make test-lib-external-launcher-common` fails after doc edits to `python/cli.py agent launch-review`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Add these harnesses to the update list and retarget their fixtures and expected strings to agent launch-review and the new Codex auth inventory
  - From Cursor-Innovation: Add ### UPDATED: scripts/test-lib-external-launcher-common.sh to expect python/cli.py agent launch-review in the inventory string (mirror the doc edits)
  - From Cursor-Pragmatic: Add `### UPDATED: scripts/test-lib-external-launcher-common.sh` to replace `launch-review.sh --tool codex` with `python/cli.py agent launch-review --tool codex` in `_codex_auth_inventory` and any `external_launcher_append_outer_meta` fixtures that still pass a shell path


### FINDING_10: `python/plan_scout.py` default launcher path cannot exec multi-word Python CLI command
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Concern**: If the default becomes `"python/cli.py agent launch-review"` while `subprocess.run` still builds `[launch_review, ...]`, the dynamic archetype Cursor tier tries to exec a filename containing spaces and always falls back or fails.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Require an argv-prefix list for the default, for example [sys.executable, cli.py, agent, launch-review], then append flags. Keep the legacy _SH override as a one-element executable path or add a parsed _CMD override with tests.


### FINDING_11: Cursor auth port omits keychain preread and env normalization
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Concern**: The plan only calls Cursor auth preflight and says `CURSOR_API_KEY` is inherited when set. The current launcher also pre-reads the macOS `cursor-access-token` into `CURSOR_API_KEY` and normalizes exports before spawning cursor. Dropping that step can regress Darwin keychain auth and reintroduce parallel keychain races.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: In the proposed Cursor helper, call cursor_preread_service_token() and cursor_auth_export_env() after cursor_auth_preflight() and before launching cursor.


### FINDING_12: Deleted `test-launch-review.sh` security/isolation coverage lacks planned pytest parity
- **Reviewer(s)**: Codex-dyn-sidecar-security, Codex-dyn-launcher-parity
- **Severity**: important
- **Concern**: The plan deletes `scripts/test-launch-review.sh` but the new pytest list does not replace existing coverage proving `CODEX_HOME` is a per-invocation tmpdir outside the output tree, `OPENAI_API_KEY` does not leak into argv/artifacts, `--codex-add-dir` rejects outside/symlink paths, and parallel Cursor launches get distinct `CURSOR_CONFIG_DIR` values. The Python port could accept unsafe add-dir paths or leak secrets after the shell harness is removed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-sidecar-security: Add focused pytest cases for those existing harness assertions, especially codex add-dir accept/reject, Codex home/config secret handling, and Cursor config-dir isolation.
  - From Codex-dyn-launcher-parity: Add focused python/test_launch_review.py cases for accepted in-output add-dir and rejection of non-directory, symlink, control/.. paths, and outside canonical output dir


### FINDING_13:
- **Reviewer(s)**: Cursor-dyn-sidecar-security
- **Severity**: important
- **Focus area**: security
- **Location**: python/agents.py (planned launch_review Cursor path); python/legacy_review_shell/review-core.sh:442-478
- **Concern**: [SCOPE-REDUCTION] Cursor post-run dirty-tree switches from baseline sidecars with path lists to checkpoint-only sidecars. Scenario: Current `launch-review.sh` Cursor EXIT trap calls `_write_dirty_tree_sidecar` (baseline mode via `lib-dirty-tree-sidecar.sh`), which can emit `TRACKED_PATHS_FILE` / `NEW_UNTRACKED_PATHS_FILE`. Plan routes Cursor post-run through `dirty-tree checkpoint --sidecar`, whose `checkpoint()` output has only `STATUS`/`MODE=checkpoint` and no path lists. `recover_dirty_tree()` auto-discard still reads path files from the launcher sidecar, so a `STATUS=dirty` checkpoint sidecar can set `RECOVERY_TAKEN=true` without reverting reviewer mutations
- **Proposed resolution**: Keep Cursor post-run on the existing baseline sidecar contract (parity with `scripts/launch-review.sh:922` and `scripts/lib-dirty-tree-sidecar.sh:14-21`), or extend checkpoint sidecar emission and/or `recover_dirty_tree()` so dirty Cursor runs still discard concrete paths




### FINDING_1: Approach conflates `dirty-tree checkpoint` with review baseline capture
- **Reviewer(s)**: Cursor-Arch, Cursor-Pragmatic, Cursor-Requirements
- **Severity**: important
- **Concern**: The plan’s Approach sketch says to replace `snapshot-untracked.sh` calls with `python/cli.py dirty-tree checkpoint`, but review launch dirty-tree handling is a two-phase flow, not a checkpoint-only flow. Cursor review needs a pre-launch NUL untracked snapshot plus a post-launch `dirty-tree baseline` comparison (`scripts/launch-review.sh` around 521–522 and 987–988; `scripts/lib-dirty-tree-sidecar.sh` routes post-run work through `dirty-tree baseline --baseline`). `dirty-tree checkpoint` only tests current porcelain cleanliness and does not write `UNTRACKED_BASELINE` or the `TRACKED_PATHS_FILE` / `NEW_UNTRACKED_PATHS_FILE` streams that `dirty_tree.baseline()` and `recover_dirty_tree` depend on (`python/dirty_tree.py` around 80–84 vs 87–171). Codex read-only is separate: it emits a static clean sidecar and does not use checkpoint (`scripts/launch-review.sh` around 285–287). Following the Approach bullet risks false positives on pre-existing dirt, missing path streams, or broken recovery.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Replace line 21 with: Cursor uses python/cli.py git snapshot-untracked (or dirty-tree baseline with a snapshot file) pre-launch and dirty-tree baseline post-launch; Codex read-only uses the static clean sidecar only. Name these APIs in _review_capture_cursor_dirty_baseline and _review_write_cursor_dirty_tree_from_baseline.
  - From Cursor-Pragmatic: State explicitly: capture baseline via python/cli.py git snapshot-untracked --nul (or in-process git.snapshot_untracked); post-run sidecar via dirty-tree baseline --baseline. Reserve dirty-tree checkpoint for unrelated checkpoint-only callers. Remove or rewrite line 21.
  - From Cursor-Requirements: Fix Approach: pre-launch writes the NUL untracked list (snapshot-untracked.sh equivalent); post-launch calls dirty_tree.baseline() in-process. Do not route baseline work through dirty-tree checkpoint


### FINDING_2: Collector retry has no Python replay shim for legacy `OUTER_LAUNCHER` review paths
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: After `scripts/launch-review.sh` is deleted, `collect-agent-results.sh` outer retry still canonicalizes `OUTER_LAUNCHER` to that shell path and requires it to exist as a regular executable file (`scripts/collect-agent-results.sh` around 712–746, 767–787). In-flight or pre-cutover `.meta` files that record `OUTER_LAUNCHER=<repo>/scripts/launch-review.sh` will fail metadata validation or execution even when prompt sidecars remain valid, so collector outer retries fail closed with no Python replay path (unlike the existing `agent launch-codex-exec` arm at 788–797).
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Add a review retry arm for canonical `launch-review.sh` paths (keep existing canonical-path checks) that replays through `python3 "$SCRIPT_DIR/../python/cli.py" agent launch-review` with the same forwarded flags; do not execute `META_OUTER_LAUNCHER` directly and do not require the deleted script to exist



### FINDING_1: Review launcher needs shell transient-retry loops and `run_external_agent` wrapper, not auth-only retries alone
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation
- **Severity**: important
- **Concern**: The plan treats `_run_external_agent_with_auth_retries` as sufficient for Codex/Cursor review launch. Shell `launch-review.sh` runs separate transient loops (quota skip, sidecar history reset, Cursor empty-`.result` retry, jittered backoff) around `run-external-agent`, while `_run_external_agent_with_auth_retries` only handles auth retries. Routing vendor execution without the in-process `run_external_agent` wrapper can omit `.meta` TOOL/TIMEOUT, `inner.done`, timeout, and stall handling that collectors and retries depend on.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Make launch_review_main use explicit review-specific retry loops (mirror scripts/launch-review.sh) and call run-external-agent per attempt; do not wire the whole path through _run_external_agent_with_auth_retries alone
  - From Cursor-Innovation: Route vendor execution through in-process run_external_agent with .inner.done; Cursor uses capture_stdout_only; add review transient-retry loop outside auth-only retries


### FINDING_2: `plan_quality` test-launch override wording conflicts with existing `LARCH_TEST_LAUNCH_*` tests
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: Plan wording says parse overrides as argv prefixes, but tests set a single fake executable and rely on `[--fake, --tool, codex|cursor, ...]` from appending `--tool` after the override.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Spell out in plan_quality.py: default is [sys.executable, cli.py, agent, launch-review, --tool, <tier>]; when LARCH_TEST_LAUNCH_*_REVIEW is set, replace only the launcher executable prefix and still append --tool <tier> (do not treat the env var as the full argv list)


### FINDING_3: Cursor terminal step order must match shell launcher sequence
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: Planned Cursor terminal step order does not match the shell launcher. Plan bullet order places dirty-tree before test trap; shell runs outer meta, then trap, then JSON post-processing, then dirty-tree, then `.done` promotion.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Document exact order from scripts/launch-review.sh:1143-1303 and implement to that sequence


### FINDING_4: Codex EXIT-trap dirty-tree and `.done` promotion parity omitted
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: Codex EXIT-trap dirty-tree and `.done` promotion are omitted from the plan. Without trap/finally parity, outer meta and usage can run after `.done` or skip read-only dirty-tree sidecar on exit.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Pin Codex flow to shell _codex_exit_dispatcher: post-loop meta and usage then EXIT hook writes dirty-tree and promotes .inner.done


### FINDING_5: Tool-specific preflight and `cap_hit` process exit-code parity omitted
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: Plan omits tool-specific preflight and `cap_hit` process exit-code parity. Shell exits 0 for Codex auth-setup failure and token `cap_hit` while writing non-zero or `cap_hit` into `.done`; Cursor auth and Codex model-args failures exit non-zero. A uniform non-zero exit in Python changes `dispatch-with-waterfall` wait/rc handling and scout failure classification versus today.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Document and test the exact exit-code matrix in `launch_review_main` (mirror `scripts/launch-review.sh` Codex auth exit 0, cap_hit exit 0, Cursor/Codex model-args and Cursor auth exit rc) and add pytest cases alongside the preflight bundle tests.


### FINDING_7: Retired `scripts/launch-review.sh` literals will fail `lint-retired-scripts` after migration
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Concern**: Plan permits exact retired-path literals after adding them to `migrated-scripts.tsv`. After `scripts/launch-review.sh` is appended to `python/migrated-scripts.tsv`, `make lint-retired-scripts` flags any tracked-file substring match for that retired path. Proposed legacy fixtures, docs, and "historical" retained references can make the required lint fail.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Generic: Require zero exact `scripts/launch-review.sh` literals outside the manifest. Build legacy test fixture paths programmatically, construct collector compatibility paths without `$SCRIPT_DIR/launch-review.sh` literals, and describe legacy metadata without the contiguous retired repo-relative path.




### FINDING_1: Codex auth-setup failure dirty-tree contract conflicts with bash and across reviewers
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic
- **Severity**: important
- **Concern**: Codex auth-preflight can exit before any agent runs while an EXIT trap may still emit a `.dirty-tree` sidecar. Bash sets `CODEX_SANDBOX_MODE=read-only` and the Codex EXIT dispatcher writes `STATUS=clean` / `REASON=codex-sandbox-read-only` when no sidecar was written yet (see `scripts/launch-review.sh` around the auth-preflight `exit 0` path and `_codex_exit_dispatcher`). Plan/pytest material that expects `STATUS=unknown` on auth failure, or edge-case prose that forbids `STATUS=clean` when auth preflight never reached the agent, diverges from current bash. Reviewers disagree on the port target: match bash’s static clean read-only sidecar vs disable the trap and emit explicit `STATUS=unknown` so consumers do not treat auth short-circuits as launcher-verified clean trees.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Align the Codex auth-setup test and edge-case prose with bash: expect clean static read-only dirty-tree (no unknown), and narrow the "no clean preflight sidecar" rule to Cursor/model-args paths that never ran the vendor.
  - From Cursor-Innovation: Align Codex auth-setup failure with bash: static clean read-only dirty-tree sidecar; reserve unknown sidecars for Cursor auth and model-args preflight only; fix edge case 730 tool split
  - From Cursor-Pragmatic: On auth/model preflight short-circuits, disable the Codex finally/trap dirty-tree writer (same pattern as model-args preflight `trap - EXIT` at `scripts/launch-review.sh:552`), write explicit `STATUS=unknown` sidecars, and add a pytest asserting auth failure never emits `STATUS=clean`


### FINDING_2: Cursor dirty-tree baseline helpers must pin canonical Python/git APIs
- **Reviewer(s)**: Cursor-Arch, Cursor-Pragmatic
- **Severity**: important
- **Concern**: The plan names `_review_capture_cursor_dirty_baseline` and `_review_write_cursor_dirty_tree_from_baseline` without binding them to the same APIs bash already uses (`snapshot-untracked.sh --nul` for baseline capture; `python/cli.py dirty-tree baseline` for post-run sidecar emission). The approved outline also sketches replacing snapshot-untracked with `dirty-tree checkpoint`, which reviewers treat as forbidden for this launcher surface. Unspecified helpers risk reimplementing git logic, calling `checkpoint`, shelling out to deleted scripts, or omitting `TRACKED_PATHS_FILE` / `NEW_UNTRACKED_PATHS_FILE` streams—producing false positives on pre-existing dirt or missing reviewer-created untracked files.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Pin `_review_capture_cursor_dirty_baseline` to `git.snapshot_untracked` (or `python/cli.py git snapshot-untracked`) and `_review_write_cursor_dirty_tree_from_baseline` to `dirty_tree.baseline()`; keep Codex on `_review_write_clean_readonly_dirty_tree` matching the read-only EXIT trap.
  - From Cursor-Pragmatic: Pin capture to in-process `git.snapshot_untracked(..., nul=True)` or `python/cli.py git snapshot-untracked --output <baseline> --nul`, and post-run sidecar emission to `python/cli.py dirty-tree baseline --baseline <baseline> --sidecar <output>.dirty-tree` (matching `scripts/lib-dirty-tree-sidecar.sh`)


### FINDING_3: Claude Code rule `paths:` globs will miss Python launch-review surfaces after shell retirement
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: `.claude/rules/launcher-argv-test-coverage.md` frontmatter still keys off `scripts/launch-*.sh` and `scripts/test-launch-*.sh`. After deleting `scripts/launch-review.sh` and `scripts/test-launch-review.sh`, edits to `python/agents.py`, `python/test_launch_review.py`, or the `python/cli.py agent launch-review` verb will not inject the argv-coverage reminder. `.claude/rules/external-tool-launcher-parity.md` still lists `scripts/launch-review.sh` explicitly.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add `python/agents.py`, `python/test_launch_review.py`, and `python/cli.py agent launch-review` to the rule `paths:` list; drop retired `scripts/launch-review.sh` / `scripts/test-launch-review.sh` entries. Mirror the same cleanup in `.claude/rules/external-tool-launcher-parity.md`.


### FINDING_4: Makefile harness shards still depend on per-section shell launch-review targets
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: `test-harnesses-9`, `test-harnesses-18`, and `test-harnesses-20` depend on `test-launch-review-cursor-core`, `test-launch-review-cursor-retry`, and `test-launch-review-codex`, not only the umbrella `test-launch-review`. Removing only the umbrella target leaves shard prerequisites broken or review-launcher coverage untested in CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Explicitly remove the three subsection targets and their shard prerequisites; wire shard coverage to `python3 -m pytest python/test_launch_review.py` (directly or via a single Make target) and update `scripts/test-harness-shards-coverage.sh` carve-outs accordingly.


### FINDING_5: Plan omits `python/test_plan_quality.py` while changing revise-waterfall launcher defaults
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: Retargeting `plan_quality.py` revise-waterfall launcher defaults to a multi-element `python/cli.py agent launch-review` argv prefix without listing `python/test_plan_quality.py` under **Files to modify/create**. Those tests stub launchers via `LARCH_TEST_LAUNCH_CODEX_REVIEW` / `LARCH_TEST_LAUNCH_CURSOR_REVIEW` (and related env vars). If override or prefix-replacement logic drifts during the port, revise-waterfall tests can fail or silently invoke the real launcher.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Add `### UPDATED: python/test_plan_quality.py` and pin that overrides still replace the full default argv prefix with the single fake executable while preserving `--tool <tier>` suffix behavior


### FINDING_6: Serial lock must wrap every external agent spawn, not only auth retries
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Concern**: Current bash reacquires the external serial lock before every Codex/Cursor vendor spawn, including transient retries and Cursor empty-result retries. A Python port that locks only around auth attempts can allow concurrent Codex/Cursor runs across slots and reintroduce CLI startup races.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Generic: Wrap external_serial_lock_acquire/release around every run_external_agent call, including auth, transient, and Cursor empty-result retries; add a parity test for transient retry lock reacquisition


### FINDING_8:
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Focus area**: architecture
- **Location**: scripts/collect-agent-results.sh:717-786
- **Concern**: [SCOPE-REDUCTION] Legacy retired launch-review.sh metadata replay adds a compatibility branch beyond the requested direct cutover. Scenario: The feature only needs new metadata generated as OUTER_LAUNCHER=agent launch-review; retaining path-canonicalization for a deleted launcher increases tamperable retry surface and test burden without completing the port
- **Proposed resolution**: Remove the legacy review-launcher compatibility arm and related fixtures; fail closed on retired launch-review.sh metadata after cutover, while keeping agent launch-review and agent launch-codex-exec retries




### FINDING_6: Python port omits LARCH_TOKEN_BUDGET_CAP_REVIEW env fallback
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Concern**: `python/agents.py` `launch-review` omits `LARCH_TOKEN_BUDGET_CAP_REVIEW` env fallback. Bash applies `LARCH_TOKEN_BUDGET_CAP_REVIEW` when `--token-budget-cap` is absent (`scripts/launch-review.md` contract; `scripts/test-launch-review.sh` cap-hit coverage). The plan only lists `--token-budget-cap` parsing and cap-hit sidecars, so the Python port can skip env-driven caps and spawn vendors when operators rely on the env knob.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: In _review_effective_token_cap (or equivalent), mirror bash: when args lack --token-budget-cap, accept only positive integer LARCH_TOKEN_BUDGET_CAP_REVIEW; add pytest for env-only cap hit.


### FINDING_7: Python port omits DESIGN_TMPDIR session-id token binding
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Concern**: `python/agents.py` `launch-review` omits `DESIGN_TMPDIR` session-id token binding. Bash exports `LARCH_TOKEN_SESSION_ID` from `DESIGN_TMPDIR/session-id` when `IMPLEMENT_TMPDIR/session-id` is absent (`launch-review.md` invariant). The plan names `_review_apply_session_token_env()` but never requires `DESIGN_TMPDIR` handling, so standalone `/design` review launches can lose token-session attribution.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Specify _review_apply_session_token_env: IMPLEMENT_TMPDIR/session-id first, else DESIGN_TMPDIR/session-id; add pytest for DESIGN-only binding.


### FINDING_8: Launch-failure logging lacks DESIGN_TMPDIR and vendor-diagnostics parity
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Concern**: `_review_append_launch_failure` plan omits `DESIGN_TMPDIR` logging and vendor-failure diagnostics parity. Bash `append_launch_failure` logs to `DESIGN_TMPDIR/execution-issues.md` when `IMPLEMENT_TMPDIR` is unset (#3378) and calls `append_vendor_failure_diagnostics` for `IMPLEMENT_TMPDIR` vendor-failure batches (#3713). The plan tests only run-log append-failure with site review Step 2, so `/design` failures and implement vendor-failure-diagnostics batches can regress silently.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Implement _review_append_launch_failure via agents._resolve_execution_issues_log(), call run-log append-failure with verdict/retry metadata, and call agents._append_vendor_failure_diagnostics when IMPLEMENT_TMPDIR is set; add pytest for DESIGN_TMPDIR log target and vendor-diagnostics staging.


### FINDING_9:
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Focus area**: architecture
- **Location**: python/plan_scout.py:464
- **Concern**: [SCOPE-REDUCTION] Plan adds a new SCOUT_DYNAMIC_ARCHETYPES_LAUNCH_REVIEW_CMD override for scout review launches. Scenario: The scope anchor says no new launcher features beyond bash parity, and the existing SCOUT_DYNAMIC_ARCHETYPES_LAUNCH_REVIEW_SH hook already covers the fake executable override used by tests; adding a second override creates a new config contract unrelated to the cutover
- **Proposed resolution**: Keep the existing SCOUT_DYNAMIC_ARCHETYPES_LAUNCH_REVIEW_SH override as the only test hook, change only the default argv prefix to python/cli.py agent launch-review --tool cursor, and remove the new CMD variable and related tests



