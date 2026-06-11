### FINDING_1: Python checks and CI paths still reference retired launchers
- **Reviewer(s)**: Cursor-Arch, Codex-Innovation, Cursor-Pragmatic, Codex-Pragmatic
- **Severity**: important
- **Concern**: The plan omits Python orchestration paths that still preflight, build argv for, or retry through retired shell launchers. Python lint-fix, CI waterfall, voting retry, checks, and rebase paths can fail once the scripts are deleted.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add `### UPDATED: python/checks.py` (and `python/test_checks.py`) to repoint dispatch to `python3 …/cli.py agent run-external-agent` / `agent launch-codex-exec`, or call ported `agents` functions directly; drop executable-bit guard on deleted paths
  - From Codex-Innovation: Add a targeted runtime call-site sweep outside the current file list and make only direct substitutions to python3 .../cli.py agent ...; update collect-agent-results.sh retry metadata handling for the new launcher entrypoints
  - From Cursor-Pragmatic: Add UPDATED steps for python/agents.py build_launch_argv python/ci_monitor.py python/rebase.py python/checks.py python/voting.py and matching pytest updates in the same PR
  - From Codex-Pragmatic: Add these files to the cutover list and replace each live call with the matching agent CLI verb while preserving existing seams and env overrides, or retain the old executable until no live caller remains


### FINDING_2: Validation failures must remain side-effect free
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Concern**: The plan requires `.done` sidecars on validation exits, which conflicts with the existing reject-before-side-effects contract for invalid argv, unsafe output paths, invalid timeout, invalid inner sentinel, or missing command paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Narrow the sentinel requirement to post-validation failures after a valid output path and trap setup; keep argv-validation and unsafe-output failures side-effect free


### FINDING_3: Preserved sourced launcher libs still call deleted helpers
- **Reviewer(s)**: Codex-Arch, Codex-Innovation, Cursor-Pragmatic, Codex-Pragmatic, Codex-Requirements, Cursor-dyn-caller-sweep, Codex-dyn-caller-sweep
- **Severity**: important
- **Concern**: The plan keeps sourced bash libs while deleting helper executables those libs still call. Surviving consumers can lose Cursor model args or Codex usage recording before the C-phase rewrites run.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Add explicit updates for the preserved libs to call python3 "$PLUGIN_ROOT/python/cli.py" agent model-args and agent parse-codex-usage, or keep those helper scripts until every sourced consumer is retired
  - From Codex-Innovation: Add minimal internal substitutions in the kept libs so their exported functions call the new agent CLI verbs while preserving function names and caller contracts
  - From Cursor-Pragmatic: Add UPDATED steps for lib-cursor-launcher-common.sh (and lib-external-launcher-common.sh:273 for parse-codex-usage) to call python3 cli.py agent verbs or defer executable deletion until C-phase retires the libs
  - From Codex-Pragmatic: Add minimal python3 python/cli.py agent model-args and parse-codex-usage substitutions inside retained libs, or do not delete those helpers until the libs retire
  - From Codex-Requirements: Add scripts/lib-cursor-launcher-common.sh and scripts/lib-external-launcher-common.sh to UPDATED and switch only their internal helper calls to the new agent CLI verbs while preserving exported function names, or defer deleting those helpers until these consumers are updated.
  - From Cursor-dyn-caller-sweep: Either exclude `external-tool-registry.sh` from B4 deletion (sourced-only carve-out) or add minimal `### UPDATED:` entries for `lib-cursor-launcher-common.sh` and `lib-external-launcher-common.sh` (and registry consumers) to call `agent` CLI verbs before deletion
  - From Codex-dyn-caller-sweep: Add these files to Files to modify/create and either switch their helper calls to python3 "$PLUGIN_ROOT/python/cli.py" agent ... or keep external-tool-registry.sh out of migrated-scripts.tsv until its source consumers are rewritten.


### FINDING_4: Collector retry metadata still targets retired launchers
- **Reviewer(s)**: Codex-Arch, Codex-Innovation, Codex-Pragmatic, Codex-Requirements, Codex-dyn-caller-sweep
- **Severity**: important
- **Concern**: Collector retry handling still validates old launcher metadata and replays retries through retired shell entrypoints. Empty-output retry recovery can reject new Python metadata or attempt to execute missing scripts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Add a minimal collector compatibility step: accept the new agent launch-codex-exec metadata shape and replay through python3 "$PLUGIN_ROOT/python/cli.py" agent run-external-agent, or keep the old launcher paths until C1a rewrites the collector
  - From Codex-Innovation: Add a targeted runtime call-site sweep outside the current file list and make only direct substitutions to python3 .../cli.py agent ...; update collect-agent-results.sh retry metadata handling for the new launcher entrypoints
  - From Codex-Pragmatic: Add these files to the cutover list and replace each live call with the matching agent CLI verb while preserving existing seams and env overrides, or retain the old executable until no live caller remains
  - From Codex-Requirements: Add these live callers to the plan with minimal CLI substitutions and collector retry metadata updates, or explicitly keep the required executable until its owning C-phase consumer is cut over.
  - From Codex-dyn-caller-sweep: Add scripts/collect-agent-results.sh to the plan and update retry execution and outer-meta validation to the new agent CLI contracts without porting the whole collector.


### FINDING_5: Live skill and runtime callers are missing from the cutover
- **Reviewer(s)**: Codex-Arch, Codex-Innovation, Cursor-Pragmatic, Codex-Pragmatic, Cursor-Requirements, Codex-Requirements, Cursor-dyn-caller-sweep, Codex-dyn-caller-sweep
- **Severity**: important
- **Concern**: The plan omits direct callers in `/design`, `/review-and-fix`, degraded gate wrappers, `/status`, scout flows, research lanes, and implement helpers. These paths can still invoke retired launchers or stale gate scripts after deletion.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Add these files and the same grep class to UPDATED with minimal CLI substitutions before deleting the scripts; keep the existing seams only when they point at the new Python CLI path
  - From Codex-Innovation: Add a targeted runtime call-site sweep outside the current file list and make only direct substitutions to python3 .../cli.py agent ...; update collect-agent-results.sh retry metadata handling for the new launcher entrypoints
  - From Cursor-Pragmatic: Add UPDATED entries for dispatch-plan-review-panel.sh decompose-panel-dispatch.sh auto-fix-plan-commands.sh review-and-fix.sh design-step0-degraded.sh step-0-degraded-gate.sh status.sh and research-phase.md with python3 cli.py agent substitutions
  - From Codex-Pragmatic: Add these files to the cutover list and replace each live call with the matching agent CLI verb while preserving existing seams and env overrides, or retain the old executable until no live caller remains
  - From Cursor-Requirements: Add explicit UPDATED entries (minimal python3 cli.py agent ... substitutions) for: skills/design/scripts/dispatch-plan-review-panel.sh, decompose-panel-dispatch.sh, auto-fix-plan-commands.sh, revise-plan-with-waterfall.sh, design-step0-degraded.sh; skills/review-and-fix/scripts/review-and-fix.sh; skills/implement/scripts/step-0-degraded-gate.sh and generate-code-flow-diagram.sh; scripts/scout-dynamic-archetypes.sh
  - From Codex-Requirements: Add these live callers to the plan with minimal CLI substitutions and collector retry metadata updates, or explicitly keep the required executable until its owning C-phase consumer is cut over.
  - From Cursor-dyn-caller-sweep: Add `### UPDATED: skills/review-and-fix/scripts/review-and-fix.sh` with the same minimal `python3 …/cli.py agent …` substitutions used in `scripts/lint-fix-loop.sh` and `scripts/launch-review.sh`
  - From Cursor-dyn-caller-sweep: Add `### UPDATED:` subsections for all four scripts; route Claude review through `agent launch-claude-review`, Codex through `agent launch-codex-exec`, Cursor monitor/wrap through `agent run-external-agent` / `agent cursor-wrap-prompt`
  - From Cursor-dyn-caller-sweep: Add `### UPDATED: scripts/scout-dynamic-archetypes.sh` and `### UPDATED: skills/implement/scripts/generate-code-flow-diagram.sh` calling `agent launch-claude-subprocess`
  - From Cursor-dyn-caller-sweep: Extend cutover to the three wrapper scripts and the four SKILL.md fences (or centralize wrappers on `python3 …/cli.py agent degraded-tools-gate` and point SKILL prose at that)
  - From Cursor-dyn-caller-sweep: Add `### UPDATED: skills/research/references/research-phase.md` mirroring the `validation-phase.md` `agent launch-codex-exec` substitution
  - From Codex-dyn-caller-sweep: Add skills/review-and-fix/scripts/review-and-fix.sh to Files to modify/create and replace those three retired-script invocations with the corresponding agent CLI verbs.
  - From Codex-dyn-caller-sweep: Add the listed /design helper files and scripts/scout-dynamic-archetypes.sh to the plan, then make only path substitutions to python3 "$PLUGIN_ROOT/python/cli.py" agent ... .
  - From Codex-dyn-caller-sweep: Add these files to Files to modify/create and substitute python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" agent degraded-tools-gate while preserving the current explicit presence flags.
  - From Codex-dyn-caller-sweep: Add both files to Files to modify/create and substitute the matching agent launch-codex-exec and agent launch-claude-subprocess CLI forms.


### FINDING_6: external-tool-registry is deleted while sourced consumers remain
- **Reviewer(s)**: Codex-Requirements, Cursor-dyn-caller-sweep, Codex-dyn-caller-sweep
- **Severity**: important
- **Concern**: The plan retires `scripts/external-tool-registry.sh` even though surviving collector and implement Step 2 code still source it. Deleting it can break startup and coder/tool validation before Python registry helpers are used.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Either keep external-tool-registry.sh as a sourced compatibility lib for C-phase consumers, or add minimal updates to those consumers to use the Python registry before deleting it.
  - From Cursor-dyn-caller-sweep: Either exclude `external-tool-registry.sh` from B4 deletion (sourced-only carve-out) or add minimal `### UPDATED:` entries for `lib-cursor-launcher-common.sh` and `lib-external-launcher-common.sh` (and registry consumers) to call `agent` CLI verbs before deletion
  - From Codex-dyn-caller-sweep: Add these files to Files to modify/create and either switch their helper calls to python3 "$PLUGIN_ROOT/python/cli.py" agent ... or keep external-tool-registry.sh out of migrated-scripts.tsv until its source consumers are rewritten.


### FINDING_13:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: scripts/external-tool-registry.sh:5-10; scripts/collect-agent-results.sh:96-98; skills/implement/scripts/step2-implement.sh:142-147
- **Concern**: [SCOPE-REDUCTION] Plan classifies external-tool-registry.sh as a retired executable even though live bash sources it. Scenario: Deleting the registry without updating these source consumers makes result collection and implement coder validation exit before their workflows start; the file is not executable in the current tree and falls under the sourced-compatibility problem
- **Proposed resolution**: Do not add external-tool-registry.sh or its md sibling to the retired manifest until source consumers are cut over, or add explicit minimal updates for every source consumer in this B4 plan


### FINDING_14:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/collect-agent-results.sh:876
- **Concern**: [SCOPE-REDUCTION] Caller cutover list omits live retry launcher. Scenario: Deleting `run-external-agent.sh` while `collect-agent-results.sh` still shells to it breaks `/design` and `/review` collector retries (C1a defers full port, not this call site)
- **Proposed resolution**: Add `scripts/collect-agent-results.sh` to UPDATED with minimal `python3 …/cli.py agent run-external-agent` substitution; port or drop the harness assertions that hard-require the `.sh` path


### FINDING_15:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/external-tool-registry.sh:1-30
- **Concern**: [SCOPE-REDUCTION] Plan deletes sourced-only external-tool-registry.sh without updating step2-implement or collect-agent-results sourcers. Scenario: /implement Step 2 and review collection fail on missing registry at source time
- **Proposed resolution**: Keep external-tool-registry.sh as a retained sourced artifact per partial-retire pattern; remove from migrated-scripts.tsv until C-phase; or add UPDATED steps for step2-implement.sh and collect-agent-results.sh before deletion


### FINDING_16:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/external-tool-registry.sh:1-39; scripts/collect-agent-results.sh:96-98; skills/implement/scripts/step2-implement.sh:142-148
- **Concern**: [SCOPE-REDUCTION] Plan retires source-only external-tool-registry.sh as an executable. Scenario: The file is non-executable and sourced by surviving bash consumers; deleting it makes collector and Step 2 fail before the new launcher framework can run
- **Proposed resolution**: Keep scripts/external-tool-registry.sh, its .md, and harness out of migrated-scripts.tsv and B4 deletions unless all source consumers are ported in the same plan



### FINDING_1: Status skill cutover targets nonexistent path
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Codex-Innovation, Cursor-Pragmatic, Codex-Requirements
- **Severity**: important
- **Concern**: The plan updates `scripts/status.sh`, but the live `/status` surface is `skills/status/scripts/status.sh` plus `skills/status/SKILL.md`. Deleting `scripts/degraded-tools-gate.sh` without updating the live skill leaves `/status` calling a retired helper.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add `### UPDATED: skills/status/scripts/status.sh` and `### UPDATED: skills/status/SKILL.md`; remove the nonexistent `scripts/status.sh` entry
  - From Codex-Arch: Replace the plan entry with skills/status/scripts/status.sh and update that invocation plus skills/status/SKILL.md to use python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" agent degraded-tools-gate
  - From Codex-Innovation: Change the plan target to skills/status/scripts/status.sh and invoke python3 "$PLUGIN_ROOT/python/cli.py" agent degraded-tools-gate with the same explicit presence flags
  - From Cursor-Pragmatic: Replace scripts/status.sh with skills/status/scripts/status.sh and add skills/status/SKILL.md to the stale-reference sweep
  - From Codex-Requirements: Add UPDATED entries for skills/status/scripts/status.sh and skills/status/SKILL.md, replacing the gate call with python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" agent degraded-tools-gate and updating the prose reference


### FINDING_2: Design dialectic doc still points at retired launchers
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: Runtime `/design` dialectic instructions still reference launcher scripts that B4 deletes, so HARD dialectic flows and stale-reference lint can fail after the cutover.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Add an UPDATED block for dialectic-execution.md replacing executable paths with python3 cli.py agent run-external-agent and agent launch-codex-exec (same contracts as dialectic-protocol.md).


### FINDING_3: Cursor lint-fix path can expand undefined PLUGIN_ROOT
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Concern**: The planned lib-cursor-launcher-common substitution assumes `PLUGIN_ROOT`, but `scripts/lint-fix-loop.sh` sources the lib without defining it. Under `set -u`, Cursor lint-fix can abort before launch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Define PLUGIN_ROOT in lint-fix-loop before sourcing the lib, or make the lib derive a local plugin root from CLAUDE_PLUGIN_ROOT or SCRIPT_DIR


### FINDING_4: External-tool-registry retained surfaces still reference retired scripts
- **Reviewer(s)**: Codex-Innovation, Codex-dyn-retire-scope-gap
- **Severity**: important
- **Concern**: Retained external-tool-registry shell, docs, and harness surfaces still reference or execute retired paths such as `scripts/agent-model-args.sh` and `scripts/run-external-agent.sh`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Add these retained harness sections to the plan; call the new agent CLI verbs, remove cases already moved to pytest, and build any retired path fixtures programmatically
  - From Codex-dyn-retire-scope-gap: Add UPDATED entries for scripts/external-tool-registry.sh, scripts/external-tool-registry.md, and scripts/test-external-tool-registry.sh. Rewrite retained contract prose to point at the new agent CLI or Python registry without retired path literals. Change the retained harness to exercise python3 python/cli.py agent model-args or the new importable registry function.


### FINDING_5: Cursor auth harness still executes retired cursor-auth-flags
- **Reviewer(s)**: Codex-Innovation, Cursor-Requirements
- **Severity**: important
- **Concern**: Retained cursor-auth test coverage still shells out to `scripts/cursor-auth-flags.sh`, so deleting that script can break the retained Makefile shard.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Add these retained harness sections to the plan; call the new agent CLI verbs, remove cases already moved to pytest, and build any retired path fixtures programmatically
  - From Cursor-Requirements: Repoint scripts/test-lib-cursor-auth.sh (and its .md contract if needed) to python3 .../cli.py agent cursor-auth-preflight while preserving rc/stdout contracts


### FINDING_6: Lib-external parse-codex-usage tests still assume retired shell helper
- **Reviewer(s)**: Codex-Innovation, Cursor-Requirements
- **Severity**: important
- **Concern**: Retained lib-external-launcher-common tests still stub or assert behavior for `scripts/parse-codex-usage.sh`, while the plan moves the live path to the Python agent CLI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Add these retained harness sections to the plan; call the new agent CLI verbs, remove cases already moved to pytest, and build any retired path fixtures programmatically
  - From Cursor-Requirements: Add an explicit plan step to update scripts/test-lib-external-launcher-common.sh for the Python parse-codex-usage call and revised fail-closed diagnostics


### FINDING_7: Relevant-checks still emits deleted B4 harness targets
- **Reviewer(s)**: Codex-Pragmatic, Cursor-Requirements
- **Severity**: important
- **Concern**: `scripts/relevant-checks.sh` still maps B4 changed or deleted files to shell harness targets that the plan removes, so the required relevant-checks gate can fail post-cutover.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: Add scripts/relevant-checks.sh to the plan and retarget these cases to the new pytest coverage, or keep Makefile compatibility aliases for the emitted target names
  - From Cursor-Requirements: Update scripts/relevant-checks.sh mappings to python/test_agents.py (or retained harnesses only) and drop routes for retired executables and their deleted harnesses


### FINDING_8: Codex exec auth lint still allowlists and recommends deleted launchers
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Concern**: The unwired-codex-exec lint still names deleted shell launchers in its allowlist and violation guidance, causing post-cutover lint guidance and tests to drift from the no-shim Python surface.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Extend the plan with python/lint_codex_exec_auth.py and python/test_lint_codex_exec_auth.py: refresh allowlist/error strings to agent launch-codex-exec (and other surviving wired entrypoints)


### FINDING_9: Token vendor scraper harness still shells out to parse-codex-usage
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Concern**: The retained token scraper harness still calls `scripts/parse-codex-usage.sh`, so deleting that helper can break shard 6 even if the parser logic moves to Python.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Repoint the harness to python3 .../cli.py agent parse-codex-usage (or import python.agents) and keep the existing KV assertions


### FINDING_10: Review skill still references retired gate and launcher paths
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Concern**: `/review` prompt prose still instructs agents to run deleted degraded-gate and launcher helpers, leaving live workflow documentation stale after B4.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Add UPDATED: skills/review/SKILL.md and route the degraded gate to the new agent CLI; adjust live launcher references to the new CLI verbs or surviving wrapper surfaces


### FINDING_11: Codex-exec outer retry protocol is not fully pinned after launcher deletion
- **Reviewer(s)**: Cursor-dyn-collector-protocol, Codex-dyn-collector-protocol
- **Severity**: important
- **Concern**: The plan deletes `scripts/launch-codex-exec.sh`, but retained collector retry logic still validates and replays codex-exec outer metadata against that canonical executable shape. The Python producer and collector need an explicit compatible metadata and replay contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-collector-protocol: Extend the `scripts/collect-agent-results.sh` plan step to mirror the `run-external-agent` change: replay codex-exec outer retries through `python3 "$PLUGIN_ROOT/python/cli.py" agent launch-codex-exec`, relax the executable-bash gate for that kind, and document the post-cutover `OUTER_LAUNCHER` value the Python producer will emit
  - From Cursor-dyn-collector-protocol: Spell out in the `python/agents.py` plan that `agent launch-codex-exec` must append the same nine-field outer block (including compact `OUTER_LAUNCHER_ADD_DIRS_JSON`) and keep `OUTER_LAUNCHER_PROMPT_FILE=${output}.prompt`; pair with the collector replay change in finding 1
  - From Codex-dyn-collector-protocol: Specify the exact Python codex-exec outer metadata accepted by the collector. Keep launch-review.sh on the existing shape, but route codex-exec outer retries through python3 "$PLUGIN_ROOT/python/cli.py" agent launch-codex-exec using the existing prompt/workdir/sandbox/effort/usage/timing/add-dir fields.




### FINDING_2: Cursor CI Python launcher omits stall and private-config contracts
- **Reviewer(s)**: Codex-Arch, Codex-Pragmatic
- **Severity**: important
- **Concern**: The Cursor CI cutover may lose existing stall detection, diagnostics, child-first kill behavior, sidecar emission, and private `CURSOR_CONFIG_DIR` isolation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Add the Cursor CI stall monitor behavior to agent launch-cursor-ci and port the current stall fixtures into python/test_agents.py
  - From Codex-Pragmatic: Port cursor_launcher_setup_private_config_dir cleanup and cursor_launcher_run_stall_monitor behavior into the Python cursor CI launcher, or keep the shell path until those contracts are preserved with focused tests


### FINDING_3: Claude read-tools scoped mode is missing from the Python port
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Concern**: The Claude subprocess/review launcher port may drop `--read-tools` and `--read-tools-add-dir` behavior, regressing scoped read-only plan-voter and scout fallback launches.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Add --read-tools and --read-tools-add-dir support to the Python Claude subprocess path, including session-root validation and CMD_JSON allowlist tests


### FINDING_5: Retained tests and fixtures still assume deleted launcher scripts
- **Reviewer(s)**: Cursor-Innovation, Cursor-Requirements, Codex-dyn-call-site-completeness, Cursor-dyn-retire-boundary
- **Severity**: important
- **Concern**: Retained dispatch, launch-review, scout, design, implementer, and validate-plan-command harnesses still stub, call, or assert diagnostics for deleted launcher scripts, which can make `make lint` or targeted harness shards fail after the cutover.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Add `### UPDATED: scripts/test-dispatch-code-voters.sh` and `### UPDATED: scripts/test-dispatch-plan-voters.sh`: extend existing `python/cli.py` stubs to handle `agent launch-claude-review` (and any other cutover verbs those harnesses intercept)
  - From Cursor-Requirements: In launch-review.sh codex model-args preflight, preserve the existing FAILURE_REASON=agent-model-args.sh failed (exit …) sidecar text when switching to python3 cli.py agent model-args, or add scripts/test-launch-review.sh to B4 with updated assertions
  - From Codex-dyn-call-site-completeness: Add these retained tests and fixtures to the plan and update their stubs/assertions to the new agent CLI surface, while deleting only the executable-specific harnesses that the plan intentionally ports to python/test_agents.py.
  - From Cursor-dyn-retire-boundary: Add skills/design/scripts/test-validate-plan-commands.sh, skills/design/scripts/fixtures/validate-plan-commands/launch-context-plan.md, and any validate-plan-commands allowlist/help-probe logic to the cutover; repoint the fixture to the post-B4 agent CLI or a surviving wrapper and update the regression expectations


### FINDING_7: review-and-fix Codex path still calls agent-model-args.sh
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Concern**: The Codex review-and-fix dispatch path still resolves model args through the soon-to-be deleted `scripts/agent-model-args.sh`, so Codex review-fix rounds can fail before launch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Add this call to the review-and-fix cutover and route it through python3 "$PY_CLI" agent model-args --tool codex --with-effort.


### FINDING_8: Stale-reference sweep omits tracked retired-script references
- **Reviewer(s)**: Codex-Innovation, Codex-Requirements, Codex-dyn-call-site-completeness
- **Severity**: important
- **Concern**: Tracked docs, rules, comments, and contract files outside the modified-file set still contain retired executable path literals or live launcher contract text, so `lint-retired-scripts` and operator-facing documentation can fail or become stale after migration.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Expand the stale-reference update step to all tracked files scanned by lint-retired-scripts, or explicitly add the omitted retained docs/comments to the update list and replace full retired path literals with the new agent CLI surface or non-matching historical wording.
  - From Codex-Requirements: Add an UPDATED entry for .claude/rules/external-tool-launcher-parity.md and include .claude in the stale-reference sweep; replace the retired run-external-agent references with the Python agent surface or a surviving integration surface
  - From Codex-dyn-call-site-completeness: Add the listed files to Files to modify/create and replace each live reference with the matching python3 python/cli.py agent verb or remove the obsolete contract text when the referenced executable is retired.
  - From Codex-dyn-call-site-completeness: Add these retained docs and comments to the stale-reference sweep and update them to the new agent CLI wording, preserving only historical references that are explicitly marked non-live.


### FINDING_10: Codex-exec preflight bundle and wrapper-exit contract are not pinned
- **Reviewer(s)**: Cursor-dyn-contract-inventory, Codex-dyn-contract-inventory
- **Severity**: important
- **Concern**: The Codex-exec Python port may fail to preserve auth/model-args preflight behavior: process exit 0, fd-3 `LAUNCHER_EXIT`, failed diagnostics, stub metadata, `.done` output, and prompt sidecar ordering.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-contract-inventory: Add edge-case + python/test_agents.py bullet: preflight failures exit 0, emit LAUNCHER_EXIT on fd-3, write STATUS=FAILED diag and .done with auth/model-args RC
  - From Codex-dyn-contract-inventory: Add python/test_agents.py cases for auth-prep and model-args preflight failures: process rc 0, LAUNCHER_EXIT from the failed helper, OUTPUT emitted, output file plus .diag .meta CMD_JSON=[] and .done written, and prompt sidecar behavior preserved if retaining the current ordering


### FINDING_11: run-external-agent health gate coverage is missing
- **Reviewer(s)**: Codex-dyn-contract-inventory
- **Severity**: important
- **Concern**: The Python `run-external-agent` port may omit launch-time health-gate behavior, allowing unhealthy Codex or Cursor children to spawn instead of fast-failing with the expected diagnostics, `.done` values, and opt-out semantics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-contract-inventory: Add an explicit port and pytest bullet for external_launch_health_gate behavior: unhealthy codex exit 7, unhealthy cursor exit 8, child not spawned, .diag health-probe text, .done value, timeout opt-out 0, and fail-open on unparseable probe output


### FINDING_12:
- **Reviewer(s)**: Codex-dyn-contract-inventory
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/run-external-agent.sh:147-162,198-235,301-313
- **Concern**: [SCOPE-REDUCTION] Plan adds side-effect-free missing command-path validation that the current wrapper does not have. Scenario: Missing child commands currently pass post-validation setup, write .meta and .done, then fail as a launch exit; pre-validating them before artifacts would remove completion and retry sidecars for a valid output path
- **Proposed resolution**: Mimic the shell contract for missing child executables by treating Popen FileNotFoundError as a post-validation launch failure, likely 127, with .meta .done and failure diagnostics; keep command-v preflights only where current launchers already have them




### FINDING_2:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/check-reviewers.md:28-29, scripts/run-negotiation-round.md:3-33, scripts/lint-fix-loop.md:73-103, scripts/ship-pr.md:116-122, scripts/dispatch-with-waterfall.md:20, scripts/dispatch-plan-voters.md:3-22, scripts/dispatch-code-voters.md:5-59, scripts/collect-agent-results.md:38, scripts/launch-review.md:18-158, scripts/scout-dynamic-archetypes.md:14-19
- **Concern**: Retained sibling contract docs with full retired launcher paths are omitted from the plan. Scenario: After migrated-scripts.tsv adds the retired launcher paths, make lint-retired-scripts can fail on these docs, and operator-facing contracts still point at deleted helpers
- **Proposed resolution**: Add UPDATED entries for the retained sibling docs that mention retired helper paths, and replace live references with the matching python3 python/cli.py agent verbs while preserving any explicitly historical references only where allowed


### FINDING_3:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/review-and-fix/scripts/review-and-fix.sh:319-358,1343
- **Concern**: Plan swaps script paths but leaves monolithic "$RUN_EXTERNAL_AGENT_SH" / "$SCRIPT_DIR/cursor-wrap-prompt.sh" / "$SCRIPT_DIR/agent-model-args.sh" calls and [[ -x "$RUN_EXTERNAL_AGENT_SH" ]] preflight. Scenario: After deleting the shell executables, Step 5 review-and-fix exits 2 at preflight or cannot invoke python3 cli.py agent verbs (not a single -x file)
- **Proposed resolution**: Specify argv-array cutover (python3 "$PY_CLI" agent run-external-agent / cursor-wrap-prompt / model-args), replace -x guard with [[ -f "$PY_CLI" ]] like WRITE_TALLY_CMD, and add skills/review-and-fix/scripts/test-review-and-fix.sh to the file list


### FINDING_4:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/agents.py planned; scripts/launch-codex-ci.sh:220-221; scripts/launch-cursor-ci.sh:202-203; scripts/launch-codex-exec.sh:199-200
- **Concern**: The plan omits the existing Darwin per-tool serial lock from the Python launcher port. Scenario: After deleting the shell launchers, Python codex/cursor CI and codex-exec entrypoints can start concurrent CLI processes without the current startup mutex, reintroducing the keychain/config race protection the launchers currently provide
- **Proposed resolution**: Port external_serial_lock_acquire/release semantics into python/agents.py and wrap the ported Codex/Cursor spawn attempts with the same LARCH_EXTERNAL_SERIAL_LOCK_* behavior


### FINDING_6:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/lint-fix-loop.sh:503
- **Concern**: skills/review-and-fix/scripts/review-and-fix.sh:1343. Scenario: -x preflight still gates run-external-agent after Python cutover
- **Proposed resolution**: Replacing RUN_EXTERNAL_AGENT_SH with python3 …/cli.py agent run-external-agent makes [[ -x … ]] fail; lint-fix-loop returns missing-run-external-agent and review-and-fix exits 2 before any external repair In both files replace the -x guard with a PY_CLI readability check and invoke run-external-agent as a python3 argv array (match the pattern python/checks.py will use)


### FINDING_7:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/scripts/test-codex-implementer.sh:678-1349
- **Concern**: skills/implement/scripts/test-cursor-implementer.sh:451-996. Scenario: Implementer harnesses not listed for diagnostic string updates
- **Proposed resolution**: B4 only minimally retargets launch-codex-implement.sh and launch-cursor-implement.sh; retained harnesses grep parse-codex-usage.sh agent-model-args.sh and cursor-wrap-prompt.sh in sidecars/transcripts; Python substitutions change producer wording and make test-harnesses-13/18 red Add explicit UPDATED entries for test-codex-implementer.sh and test-cursor-implementer.sh to repoint assertions to post-cutover diagnostics (or stable error tokens), not deleted script basenames


### FINDING_8:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/review-and-fix/scripts/test-review-and-fix.sh:888-891
- **Concern**: Retained review-and-fix harness grep pins missing from plan. Scenario: review-and-fix.sh will call Python agent verbs and lib-external-launcher-common will call agent parse-codex-usage; harness still requires parse-codex-usage.sh: in wrapper.log/sidecar, so make lint can pass script cutover while harnesses-5 review-and-fix tests fail
- **Proposed resolution**: Add skills/review-and-fix/scripts/test-review-and-fix.sh to Files to modify/create with updated grep expectations and stub wiring for the Python agent surface


### FINDING_10:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/launch-codex-drafter.sh:182-191; scripts/launch-codex-exec.sh:31,78,116-130
- **Concern**: Port plan omits launch-codex-exec --trusted-instructions-file. Scenario: The retained Codex drafter passes --trusted-instructions-file to launch-codex-exec. If agent launch-codex-exec does not preserve that public flag, the drafter either fails with an unknown flag or runs without the trusted output-contract override.
- **Proposed resolution**: Add --trusted-instructions-file to agent launch-codex-exec with the existing validation and temp CODEX_HOME config behavior, including stripping existing top-level instructions from copied config.


### FINDING_11:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/scripts/test-codex-implementer.sh:1349-1349
- **Concern**: Retained Codex implementer harness still requires agent-model-args.sh in stderr-tail diagnostics. Scenario: After launch-codex-implement.sh routes model-args through python3 cli.py agent model-args failure text may no longer contain agent-model-args.sh and shard-13 test-codex-implementer fails despite minimal implementer cutover
- **Proposed resolution**: Add explicit UPDATED blocks for skills/implement/scripts/test-codex-implementer.sh and test-codex-implementer.md (and mirror for test-cursor-implementer*) updating assertions and contract prose to the Python agent surface or pin equivalent diagnostic tokens in the implementer launcher


### FINDING_12:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/launch-cursor-ci.sh:201-203; scripts/launch-codex-ci.sh:217-221; scripts/launch-codex-exec.sh:196-200
- **Concern**: Plan omits the Darwin serial-lock contract for Python launchers. Scenario: The retired CI and codex-exec launchers currently acquire external_serial_lock_acquire before spawning cursor or codex. The proposed python/agents.py port lists auth retries, private Cursor config, and health gate, but never ports or tests the lock. Parallel Darwin launches can reintroduce the startup/keychain race the lock prevents.
- **Proposed resolution**: Port the Darwin-only serial lock helper into python/agents.py and wrap the codex/cursor spawn attempts in agent launch-codex-ci, launch-cursor-ci, and launch-codex-exec. Add one focused pytest for lock acquisition/release sequencing via injected hooks.


### FINDING_13:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: security
- **Location**: scripts/run-external-agent.sh:47-108; scripts/collect-agent-results.sh:819-826; scripts/launch-codex-implement.sh:400-404
- **Concern**: Plan omits the --stderr-sink run-external-agent contract. Scenario: Surviving callers will route through agent run-external-agent but still pass --stderr-sink, and collector retries forward STDERR_SINK from .meta. If the Python verb only implements the plan's listed output-path validation and metadata keys, these callers either fail on an unknown flag or lose the explicit stderr source and retry metadata.
- **Proposed resolution**: Include --stderr-sink in the Python argv grammar, validate it with the same [A-Za-z0-9._/-] allowlist before side effects, write STDERR_SINK only when set, and cover acceptance, rejection, and retry forwarding in python/test_agents.py.


### FINDING_14:
- **Reviewer(s)**: Cursor-dyn-sourced-compat
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/lib-cursor-launcher-common.sh:19-19
- **Concern**: Plan lib-cursor-launcher-common bullet omits required model-args flags. Scenario: The current call is `"$SCRIPT_DIR/agent-model-args.sh" --tool cursor --with-effort`. Plan line 273 only says `agent model-args` with no flags. After cutover, Cursor launches from launch-review, launch-cursor-implement, lint-fix-loop, and auto-fix-plan-commands can lose `--with-effort` and use wrong defaults.
- **Proposed resolution**: Add to the `### UPDATED: scripts/lib-cursor-launcher-common.sh` bullet an exact replacement: `python3 "$plugin_root/python/cli.py" agent model-args --tool cursor --with-effort`, preserving the line-token stdout contract.


### FINDING_15:
- **Reviewer(s)**: Cursor-dyn-sourced-compat
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-external-tool-registry.sh:132-150
- **Concern**: Registry harness still probes deleted agent-model-args.sh. Scenario: Section 14b calls `"$REPO_ROOT/scripts/agent-model-args.sh" --tool "$tool"` to ensure every registered external tool returns non-empty model argv. Plan `### UPDATED: scripts/test-external-tool-registry.sh` only mentions `agent external-tool-registry`, which does not replace that per-tool model-args probe. After deleting `agent-model-args.sh`, section 14b breaks even if the bash registry taxonomy stays.
- **Proposed resolution**: Repoint section 14b to `python3 "$REPO_ROOT/python/cli.py" agent model-args --tool "$tool"` (add `--with-effort` for codex if parity requires it). Keep `agent external-tool-registry` coverage separate.


### FINDING_16:
- **Reviewer(s)**: Cursor-dyn-meta-ordering
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/launch-codex-exec.sh:108-162
- **Concern**: Plan omits `--trusted-instructions-file` and its CODEX_HOME config.toml merge despite live launcher support. Scenario: Port drops trusted-instructions behavior; `scripts/test-launch-codex-exec.sh` cases at 389+ fail
- **Proposed resolution**: Add the flag to `agent launch-codex-exec` scope and document prepending trusted instructions plus stripping `~/.codex/config.toml` instructions before auth/model-args preflight


### FINDING_18:
- **Reviewer(s)**: Codex-dyn-meta-ordering
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/launch-codex-exec.sh:203-273; scripts/test-launch-codex-exec.sh:194-265
- **Concern**: 2. Codex-exec public .done promotion order is under-specified. Scenario: Current bash keeps run-external-agent on .inner.done, finishes retries, records usage, appends OUTER_LAUNCHER metadata, then promotes .inner.done to .done and emits LAUNCHER_EXIT then OUTPUT. If Python promotes .done before usage or outer metadata, collect-agent-results can observe completion and read incomplete retry metadata.
- **Proposed resolution**: Add an explicit post-child sequence: keep public .done absent during retries and post-processing; record timing and usage; append codex-exec outer metadata; promote .inner.done to .done; emit LAUNCHER_EXIT then OUTPUT.


### FINDING_19:
- **Reviewer(s)**: Codex-dyn-meta-ordering
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/run-external-agent.sh:167-198; scripts/run-external-agent.md:101-110; scripts/test-run-external-agent.sh:627-644
- **Concern**: 3. run-external-agent failure carrier ordering is missing from the plan. Scenario: The shell EXIT trap composes ${output}.failure-diag before writing .done, and the contract says visible .done implies the carrier exists for failures. The plan mentions carrier behavior but not the carrier-before-sentinel ordering. A Python port could write .done first and race collectors or log publishers.
- **Proposed resolution**: Add the trap-equivalent ordering to the plan and pytest: on nonzero post-validation exits, compose .failure-diag before .done; on success, clear stale .failure-diag before .done.




### FINDING_3: Claude subprocess context redaction contract is not pinned
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Concern**: The Python port and tests do not explicitly preserve the existing Claude context rendering protections. A port that keeps only path validation, symlink rejection, and size caps can leak secrets or let context bytes appear as trusted prompt structure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Add explicit python/agents.py port steps and python/test_agents.py coverage for context block rendering: XML-escaped path attributes, untrusted-data preamble, secret redaction, body escaping, and no unredacted secret leakage before deleting launch-claude-subprocess.sh.


### FINDING_4: Auth lint must scan new Python Codex exec call sites
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Concern**: The plan moves raw `codex exec` dispatch into Python, but the fail-closed auth lint currently scans only shell and markdown. New Python Codex exec call sites could become invisible to the guard.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: Extend lint-codex-exec-auth to scan Python launcher call sites and allowlist only the wired python/agents.py surface plus intentional tests.


### FINDING_8: parse-codex-usage replacement omits events-file argument
- **Reviewer(s)**: Cursor-dyn-compatibility-boundary, Codex-dyn-compatibility-boundary
- **Severity**: important
- **Concern**: The plan’s replacement argv for `parse-codex-usage` omits the positional events JSONL path. If implemented literally, retained usage recording can call the Python verb without input and lose token sidecars or ledger rows.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-compatibility-boundary: Add to `### UPDATED: scripts/lib-external-launcher-common.sh` the full replacement: `usage_blob=$(python3 "$plugin_root/python/cli.py" agent parse-codex-usage "$events_file" 2>"$usage_err")` (preserve stderr capture and existing usage KV parsing).
  - From Codex-dyn-compatibility-boundary: Specify the full replacement call: usage_blob=$(python3 "$plugin_root/python/cli.py" agent parse-codex-usage "$events_file" 2>"$usage_err") || usage_blob=""



