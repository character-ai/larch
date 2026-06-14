### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:114-121
- **Concern**: Step 2/4 SKILL cutover uses bare python3 with CLAUDE_PLUGIN_ROOT instead of the post-Step-0 larch-run launcher. Scenario: After Step 0, orchestrator fences are required to call bash "$IMPLEMENT_TMPDIR/larch-run.sh" python/cli.py ... so plugin root rehydration does not depend on a pre-set CLAUDE_PLUGIN_ROOT; direct python3 implement run-dispatch / implement commit can fail or target the wrong tree on resume or dirty-tree paths
- **Proposed resolution**: Change the planned SKILL.md fences to bash "$IMPLEMENT_TMPDIR/larch-run.sh" python/cli.py implement run-dispatch ... and bash "$IMPLEMENT_TMPDIR/larch-run.sh" python/cli.py implement recovery-paths ... / implement commit ...; keep CLAUDE_PLUGIN_ROOT only in pre-bootstrap fences


### FINDING_2:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/implement_dispatch.py; python/cli.py
- **Concern**: Recovery CLI main is named two different ways. Scenario: The plan defines write_recovery_paths_main but registers recovery_paths_main, so python/cli.py implement recovery-paths can import a missing function
- **Proposed resolution**: Choose one name, preferably recovery_paths_main, and use it consistently in the new module, CLI registry, and tests


### FINDING_3:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/test-token-vendor-scrapers.sh:151-193; scripts/test-cache-key-discipline.sh:178-179; scripts/test-external-tool-registry.sh:158-162; agent-lint.toml:354-364,400-408; .claude/rules/external-tool-launcher-parity.md:2; .claude/rules/launcher-argv-test-coverage.md:2
- **Concern**: Retired path sweep omits non-doc live references. Scenario: The plan appends deleted scripts to python/migrated-scripts.tsv, but tracked tests, lint config, and rules still reference or execute those paths, so make lint-retired-scripts or make lint will fail after deletion
- **Proposed resolution**: Add an explicit stale-reference cutover for every lint-retired-scripts hit, including tests, agent-lint.toml, and .claude/rules, replacing executable calls with the new Python CLI verbs or deleting obsolete exclusions


### FINDING_4:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/cli.py:174-178
- **Concern**: Recovery-paths CLI entry name disagrees with the declared main symbol. Scenario: `cli.py` registers `recovery_paths_main` but the plan names the writer `write_recovery_paths_main` at line 49; a faithful port can ship a broken registry or a missing symbol at import time
- **Proposed resolution**: Standardize on one symbol name in both the `implement recovery-paths` registry row and the `implement_dispatch.py` export (prefer `recovery_paths_main` and drop the duplicate name)


### FINDING_5:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/test-token-vendor-scrapers.sh:151-157
- **Concern**: Token-scraper harness still shells out to deleted implement launchers. Scenario: The plan retargets Makefile targets and `docs/linting.md` prose but not `scripts/test-token-vendor-scrapers.sh`, which hard-codes `launch-cursor-implement.sh` / `launch-codex-implement.sh`; after deletion `make test-token-vendor-scrapers` and `make lint` fail
- **Proposed resolution**: Add an explicit `UPDATED: scripts/test-token-vendor-scrapers.sh` (and sibling `.md` if needed) retargeting smoke calls to `python/cli.py agent launch-cursor-implement` / `launch-codex-implement` with the same argv contract


### FINDING_6:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/test-external-tool-registry.sh:153-159
- **Concern**: Registry harness still executes deleted `step2-implement.sh`. Scenario: Test 14 shells `"$REPO_ROOT/skills/implement/scripts/step2-implement.sh" --coder claude` from a nested cwd; the plan does not list this harness in Makefile/doc retargets or pytest migration, so `make test-external-tool-registry` breaks after cutover
- **Proposed resolution**: Retarget test 14 to `python/cli.py implement step2-dispatch` (or fold the assertion into `python/test_implement_dispatch.py`) and keep the nested-cwd path-resolution check


### FINDING_7:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: .claude/rules/launcher-argv-test-coverage.md:2-20
- **Concern**: Path-triggered rules still cite deleted Step 2 bash stack. Scenario: `launcher-argv-test-coverage.md` and `external-tool-launcher-parity.md` glob and prose still name `run-step2-dispatch.sh`, `step2-implement.sh`, and `launch-codex-implement.sh`; editors keep getting stale harness guidance after the stale-reference sweep
- **Proposed resolution**: Add explicit updates to both `.claude/rules/*` files mapping Step 2 dispatch and implement launchers to `python/cli.py implement run-dispatch`, `implement step2-dispatch`, and `agent launch-{codex,cursor}-implement` plus `python/test_implement_dispatch.py`


### FINDING_8:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:183-194
- **Concern**: Step 2 cutover bypasses the mandated `larch-run.sh` launcher. Scenario: The plan replaces `bash "$IMPLEMENT_TMPDIR/larch-run.sh" …run-step2-dispatch.sh` with bare `python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" …`; `/implement` post-Step-0 fences require `larch-run.sh` for plugin-root rehydration, matching the existing `review-and-fix step5` pattern
- **Proposed resolution**: A cutover fence like `bash "$IMPLEMENT_TMPDIR/larch-run.sh" python/cli.py implement run-dispatch --implement-tmpdir "$IMPLEMENT_TMPDIR" --coder "$coder" [--answers …]`; apply the same pattern to `implement recovery-paths` and `implement commit`


### FINDING_9:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/implement_dispatch.py:39-94
- **Concern**: Plan omits fd-3 `quiet_init` for dispatcher stdout. Scenario: Bash dispatch uses `larch_quiet_init`/`emit_kv`; `python-migration.md` and existing B4 launcher mains require `logging_util.quiet_init` so KV lines stay on the contract stream and progress chatter does not pollute orchestrator parsing
- **Proposed resolution**: Require `quiet_init` at the top of `step2_dispatch_main`, `run_dispatch_main`, `commit_main`, and both new `agents.py` implement launcher mains; add pytest assertions that stderr/progress text never appears on the KV stdout channel


### FINDING_11:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: architecture
- **Location**: skills/implement/references/codex-manifest-schema.md:3-7
- **Concern**: Deleting `step2-implement.md` leaves no authoritative stdout-contract home. Scenario: The plan deletes `step2-implement.md` and only generically says SKILL prose will change; `codex-manifest-schema.md`, SKILL envelope text, and `agent-lint.toml` still point at the bash dispatcher contract, so post-cutover docs drift from behavior
- **Proposed resolution**: Before deleting the bash contract sibling, repoint `codex-manifest-schema.md` (and SKILL cross-refs) to `python/implement_dispatch.py` plus a slim retained reference (or regenerated doc) for the KV envelope; update `agent-lint.toml` S030 pins away from deleted harness paths


### FINDING_12:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:49,174-177
- **Concern**: `implement recovery-paths` has two proposed Python entrypoint names. Scenario: The function list says to add `write_recovery_paths_main`, but the CLI registry imports `recovery_paths_main`; following the first name leaves `python3 python/cli.py implement recovery-paths` broken at runtime.
- **Proposed resolution**: Use one name in both places, preferably `recovery_paths_main`, and update the function list to match the registry and SKILL.md call site.


### FINDING_13:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: .claude/rules/external-tool-launcher-parity.md:2,25-28; .claude/rules/launcher-argv-test-coverage.md:2,18-19; agent-lint.toml:400-408; scripts/test-cache-key-discipline.sh:178-179; scripts/test-token-vendor-scrapers.sh:151-157; scripts/test-external-tool-registry.sh:158-163; scripts/external-tool-registry.md:9-12; scripts/lib-cursor-auth.md:13-17
- **Concern**: Stale-reference sweep omits live non-doc test and lint surfaces for retired paths. Scenario: After the plan appends the retired paths and deletes the shell launchers, `make lint-retired-scripts` and existing make lint harnesses can still fail or invoke deleted scripts.
- **Proposed resolution**: Add these files to the update set, then retarget live tests/config/rules to `python/cli.py` verbs or remove obsolete allowlist/path-trigger entries before appending the retired paths.


### FINDING_14:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/implement/SKILL.md:122-124
- **Concern**: The plan cuts Step 2/4 fences to bare `python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" implement …` instead of the post–Step 0 `larch-run.sh` one-liner.. Scenario: `/implement` Bash fences after Step 0 must delegate through `bash "$IMPLEMENT_TMPDIR/larch-run.sh" python/cli.py …` so `CLAUDE_PLUGIN_ROOT` and `IMPLEMENT_TMPDIR` rehydrate from session artifacts; bare `python3` can exit 2 or run against the wrong plugin root when env is unset.
- **Proposed resolution**: Change the SKILL.md cutover to `bash "$IMPLEMENT_TMPDIR/larch-run.sh" python/cli.py implement run-dispatch|recovery-paths|commit …` and keep the existing foreground/no-polling prose.


### FINDING_15:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-external-tool-registry.sh:158-162
- **Concern**: The plan retires `step2-implement.sh` but does not retarget this `make lint` harness, which still executes the deleted script for nested-cwd `claude_fallback` coverage.. Scenario: `make test-external-tool-registry` (harness shard 18) fails immediately after deletion even if `make lint-retired-scripts` is clean.
- **Proposed resolution**: Add an `### UPDATED:` step to repoint the nested-cwd case to `python3 python/cli.py implement step2-dispatch --coder claude …` (or fold the assertion into `python/test_implement_dispatch.py` and drop the shell invocation).


### FINDING_16:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-token-vendor-scrapers.sh:97-200
- **Concern**: The plan updates `docs/linting.md` for `make test-token-vendor-scrapers` but not the harness, which still shells out to `scripts/launch-cursor-implement.sh` and `scripts/launch-codex-implement.sh`.. Scenario: `make test-token-vendor-scrapers` breaks on the same commit that deletes the launcher scripts; vendor `record-vendor` smoke for `raw=cursor_implement` / `raw=codex_implement` is lost.
- **Proposed resolution**: Retarget the harness to `python3 python/cli.py agent launch-cursor-implement` / `launch-codex-implement` (stubbed binaries) or move the smoke into pytest and update the Makefile target accordingly.


### FINDING_17:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: architecture
- **Location**: plan.txt:312-335
- **Concern**: The plan deletes `step2-implement.md` and `run-step2-dispatch.md` without relocating the Step 2 stdout/KV contract that SKILL.md, `codex-manifest-schema.md`, and agent-lint still treat as authoritative.. Scenario: Envelope parsing, `ORCHESTRATOR_EDIT_AUTHORITY` invariants, REASON tokens, and timeout notes remain documented only on paths slated for deletion; post-merge operators and harness authors lose the contract surface `SKILL.md` still cites (e.g. NEVER #8 → `step2-implement.md`).
- **Proposed resolution**: Add a retained contract doc (e.g. `skills/implement/references/step2-dispatch.md` or module docstring exported in docs) and list `### UPDATED:` edits for `skills/implement/references/codex-manifest-schema.md`, SKILL.md registry lines, and `.claude/rules/launcher-argv-test-coverage.md`.


### FINDING_18:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/implement_dispatch.py (proposed §84-85)
- **Concern**: The plan allows calling `launch_codex_implement_main()` / `launch_cursor_implement_main()` in-process while the bash dispatcher isolated launcher KV via a subprocess capture file.. Scenario: Python launchers use `quiet_init` / fd-3 contract output; an in-process call can leak diagnostics onto the dispatcher stdout stream and break the fixed Step 2 KV grammar (`ORCHESTRATOR_EDIT_AUTHORITY`, recovery triplet parsing).
- **Proposed resolution**: Require subprocess invocation of `python3 …/cli.py agent launch-{codex,cursor}-implement` with stdout captured to the same tmpdir file the bash path uses, or explicitly capture the contract stream before emitting dispatcher KVs.


### FINDING_19:
- **Reviewer(s)**: Codex-Pragmatic, Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:49,176
- **Concern**: Recovery CLI main has two names. Scenario: The plan lists write_recovery_paths_main but registers implement recovery-paths to recovery_paths_main, so following the plan literally can leave cli.py pointing at an undefined function
- **Proposed resolution**: Use one name in both places, preferably recovery_paths_main, and align the pytest coverage with that name


### FINDING_20:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: plan.txt:242-254; agents/_implementer-base.md:118; .claude/rules/launcher-argv-test-coverage.md:2-19; skills/implement/references/codex-manifest-schema.md:3-7
- **Concern**: The plan restricts generated implementer prompt changes to frontmatter only, but runtime prompt and rule bodies still name deleted Step 2 shell paths. Scenario: After deleting the shell dispatcher and launchers, implementer prompts can still cite deleted dispatcher line numbers and path-trigger rules can still point at retired scripts; lint-retired-scripts may miss bare basename references in these files
- **Proposed resolution**: Broaden the stale-reference step to update generator source and prompt body path wording, schema docs and digest, and .claude rules to the Python CLI/module surfaces before regenerating prompts


### FINDING_21:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:183-194
- **Concern**: Step 2/4 cutover uses bare python3 instead of larch-run.sh. Scenario: Post-Step-0 fences are required to delegate through bash "$IMPLEMENT_TMPDIR/larch-run.sh" python/cli.py ...; direct python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" bypasses the session launcher and breaks the one-line fence contract.
- **Proposed resolution**: Use bash "$IMPLEMENT_TMPDIR/larch-run.sh" python/cli.py implement run-dispatch|recovery-paths|commit ... for every SKILL.md Step 2 and Step 4 example.


### FINDING_22:
- **Reviewer(s)**: Cursor-dyn-envelope-parity
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/implement_dispatch.py:49,177
- **Concern**: CLI registration names recovery_paths_main but the function list names write_recovery_paths_main. Scenario: cli.py lazy import resolves a missing symbol and implement recovery-paths fails at runtime or during registration
- **Proposed resolution**: Make the symbol name consistent everywhere (function definition and cli.py registry entry)


### FINDING_23:
- **Reviewer(s)**: Cursor-dyn-envelope-parity
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/implement_dispatch.py:39-94,python/agents.py:128-168
- **Concern**: Plan omits quiet_init and logging_util.emit_kv for dispatcher and launcher KV stdout. Scenario: Bash uses lib-quiet.sh FD-3 contract stream; ad-hoc print() can mix diagnostics into stdout and break SKILL.md Step 2.1.5 envelope parsing
- **Proposed resolution**: Require quiet_init plus emit_kv on every orchestrator-facing KV path per docs/python-migration.md, matching B4 launcher mains


### FINDING_24:
- **Reviewer(s)**: Cursor-dyn-envelope-parity
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/test_implement_dispatch.py:116-124
- **Concern**: Pytest scope claims all bail reasons and envelope invariants but does not enumerate harness cases that pin them. Scenario: test-step2-dispatch.md leaves commit-failed and other mechanical bails out of scope; vague porting drops Test 11 exact AUTH count, Test 13b WARN plus AUTH count, Tests M1-M19 recovery matrix, Tests 13a-scout*, Tests 22-25 stderr-tail bails
- **Proposed resolution**: Replace the broad claim with an explicit 1:1 port list keyed to existing harness test ids and assert_recovery_envelope semantics


### FINDING_25:
- **Reviewer(s)**: Cursor-dyn-envelope-parity
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/implement_dispatch.py:64-94
- **Concern**: implement step2-dispatch port list omits SCOUT_CODER_MANIFEST and SCOUT_CODER_STATUS on complete and needs_qa stdout. Scenario: step2-implement.sh emits both keys at lines 1208-1225; dropping them breaks Step 5 scout eligibility and fails Tests 13a-scout*
- **Proposed resolution**: Add explicit preservation of SCOUT_CODER_MANIFEST and SCOUT_CODER_STATUS on external complete and needs_qa envelopes


### FINDING_26:
- **Reviewer(s)**: Cursor-dyn-envelope-parity
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/migrated-scripts.tsv:214-218,skills/implement/SKILL.md:46,359,381
- **Concern**: Plan deletes step2-implement.md and run-step2-dispatch.md without relocating the stdout contract. Scenario: Approved outline required UPDATE; SKILL.md and codex-manifest-schema.md still cite step2-implement.md as the dispatcher grammar authority
- **Proposed resolution**: Relocate the stdout contract to a surviving surface (for example python/implement_dispatch.md or module docstring) and retarget SKILL.md and codex-manifest-schema.md edit-in-sync pointers before deletion


### FINDING_27:
- **Reviewer(s)**: Cursor-dyn-envelope-parity
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: agent-lint.toml:400-408
- **Concern**: Plan does not update agent-lint allowlist after deleting launch-codex-implement.sh. Scenario: Stale G004 allowlist entry references a deleted script and can fail agent-lint or mask a missing python/agents.py pin
- **Proposed resolution**: Add agent-lint.toml to UPDATED files; repoint the allowlist to python/agents.py launch_codex_implement_main


### FINDING_28:
- **Reviewer(s)**: Codex-dyn-envelope-parity
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:196-206; scripts/test-token-vendor-scrapers.sh:97-157; scripts/test-cache-key-discipline.sh:178-179
- **Concern**: The plan retargets only the five absorbed harness targets, but two live harnesses still point at the shell implement launchers the plan deletes.. Scenario: After scripts/launch-codex-implement.sh and scripts/launch-cursor-implement.sh are removed, test-token-vendor-scrapers still executes those paths for record-vendor smoke and test-cache-key-discipline still reads those files, so make lint cannot meet the DoD.
- **Proposed resolution**: Add explicit updates for these non-absorbed launcher consumers: switch their smoke and structure checks to python/cli.py agent launch-codex-implement and python/cli.py agent launch-cursor-implement, or move that coverage into the new pytest surface.


### FINDING_29:
- **Reviewer(s)**: Cursor-dyn-security-boundary
- **Severity**: important
- **Focus area**: security
- **Location**: python/implement_dispatch.py (planned); skills/implement/scripts/step2-implement.sh:963-967
- **Concern**: Plan omits explicit NUL-byte rejection for manifest paths when porting Step 7a validation to Python. Scenario: Bash relies on an explicit jq `\u0000` predicate because Python/json string handling will not truncate at NUL; a manifest path like `safe\u0000../evil` can pass `..`/absolute checks and reach `git add -A`
- **Proposed resolution**: Port the jq NUL guard verbatim: reject any `files_touched[].path` or `tests_added_or_modified[]` entry containing `\x00` before commit-on-behalf; add a pytest vector in `python/test_implement_dispatch.py`


### FINDING_30:
- **Reviewer(s)**: Cursor-dyn-retirement-sweep
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-external-tool-registry.sh:158-162
- **Concern**: Plan omits retargeting nested-cwd Step 2 probe that still executes step2-implement.sh. Scenario: After step2-implement.sh is deleted make test-external-tool-registry fails at the nested-cwd path-resolution case even if pytest dispatch tests pass
- **Proposed resolution**: Add an UPDATED subsection retargeting this harness to python/cli.py implement step2-dispatch --coder claude with the same tmpdir fixtures


### FINDING_31:
- **Reviewer(s)**: Codex-dyn-retirement-sweep
- **Severity**: important
- **Focus area**: correctness
- **Location**: Makefile:91-93,118,245-246,313-314,985-986; scripts/test-cache-key-discipline.sh:177-179; scripts/test-token-vendor-scrapers.sh:146-193; scripts/test-external-tool-registry.sh:153-163
- **Concern**: Non-retargeted Makefile shard harnesses still dereference deleted Step 2 launcher files. Scenario: make lint runs test-harnesses-4/5/18 and these scripts read or execute deleted launchers after the plan deletes them, so verification fails before the new pytest coverage matters
- **Proposed resolution**: Retarget these harnesses to python3 python/cli.py agent launch-codex-implement, python3 python/cli.py agent launch-cursor-implement, or python3 python/cli.py implement step2-dispatch, or move the checks into python/test_implement_dispatch.py and retarget the Makefile targets


### FINDING_32:
- **Reviewer(s)**: Codex-dyn-retirement-sweep
- **Severity**: important
- **Focus area**: correctness
- **Location**: agent-lint.toml:354-364,400-408,1213-1220,1366-1373; python/lint_codex_exec_auth.py:14-18
- **Concern**: The plan removes the Codex exec-auth allowlist but misses agent-lint stale allowlist entries for the same retired paths. Scenario: After python/migrated-scripts.tsv adds the retired paths, make lint-retired-scripts scans tracked files and reports these full-path allowlist comments and entries, so the requested stale-reference sweep and make lint cannot pass
- **Proposed resolution**: Remove or rewrite the agent-lint allowlist entries and comments for deleted Step 2 scripts and harnesses while applying the planned python/lint_codex_exec_auth.py allowlist cutover


### FINDING_33:
- **Reviewer(s)**: Codex-dyn-retirement-sweep
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: .claude/rules/external-tool-launcher-parity.md:2,25-28; .claude/rules/launcher-argv-test-coverage.md:2,9,18-19; scripts/external-tool-registry.sh:5-10; scripts/external-tool-registry.md:12,47; scripts/lib-cursor-auth.md:16-26; scripts/lib-cursor-launcher-common.md:3-5; scripts/lib-external-launcher-common.md:13,29; skills/implement/references/codex-manifest-schema.md:3-7,150; skills/implement/scripts/materialize-manifest-oos.md:24
- **Concern**: Stale-reference sweep omits path-trigger rules and shared launcher docs or comments that still name retired launcher paths. Scenario: The plan appends retired paths to the manifest, but these tracked surfaces keep directing maintainers to deleted files; full-path entries also trip lint-retired-scripts where the retired repo-relative path remains present
- **Proposed resolution**: Extend the stale-reference sweep to these rule, doc, and comment surfaces, and replace only the deleted paths with the new python/cli.py verbs or python/agents.py locations




### FINDING_1: Recovery-paths SKILL cutover omits full six-flag argv
- **Reviewer(s)**: Cursor-Arch, Cursor-Requirements
- **Severity**: important
- **Concern**: The Step 2.4 malformed-manifest recovery recompute is cut over to `implement recovery-paths` with `...` or otherwise unspecified flags instead of the full `compute-step2-recovery-paths.sh` contract. Step 2.4 may omit required flags (`--repo-root`, `--tmpdir`, `--prelaunch-porcelain`, `--postlaunch-porcelain`, `--prelaunch-digests`, `--out-file`) and commit the wrong NUL path list after lint-fix edits.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Pin the full `bash "$IMPLEMENT_TMPDIR/larch-run.sh" python/cli.py implement recovery-paths --repo-root "$REPO_ROOT" --tmpdir "$IMPLEMENT_TMPDIR" --prelaunch-porcelain "$IMPLEMENT_TMPDIR/step2-prelaunch-porcelain.nul" --postlaunch-porcelain "$IMPLEMENT_TMPDIR/step2-postlaunch-porcelain.nul" --prelaunch-digests "$IMPLEMENT_TMPDIR/step2-prelaunch-content-digests.txt" --out-file "$IMPLEMENT_TMPDIR/step2-recovery-paths-final.nul"` invocation in the SKILL.md update section
  - From Cursor-Requirements: Document implement recovery-paths flags (--repo-root --tmpdir --prelaunch-porcelain --postlaunch-porcelain --prelaunch-digests --out-file) in implement_dispatch.py and pin the full larch-run.sh fence in SKILL.md


### FINDING_2: Launcher subprocesses use cwd-relative `python/cli.py`
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Codex-Generic
- **Severity**: important
- **Concern**: Launcher subprocess examples/specs invoke bare or cwd-relative `python/cli.py`. The dispatcher runs from the consumer repo cwd (including nested-cwd cases such as `scripts/test-external-tool-registry.sh` with `cd /tmp`), so path resolution can miss the plugin CLI or resolve the wrong file.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Spawn launchers with `[sys.executable, str(plugin_root / "python/cli.py"), "agent", "launch-<tool>-implement", ...]` using `LARCH_CLAUDE_PLUGIN_ROOT` from session-env; never a bare relative `python/cli.py`
  - From Cursor-Innovation: Spawn launchers with sys.executable plus Path(plugin_root)/python/cli.py (from LARCH_CLAUDE_PLUGIN_ROOT), matching plan_scout.py and the registry harness REPO_ROOT pattern
  - From Codex-Generic: Resolve the plugin CLI once from __file__ or LARCH_CLAUDE_PLUGIN_ROOT and use sys.executable plus that absolute path for all child CLI calls


### FINDING_3: External scout state artifacts omitted from port spec
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: The port spec omits `step2-external-scout-eligible.txt` and `clear_external_scout_state`. Claude/cursor-fallback or stale marker paths can leave scout sidecars eligible; Step 5 external scout pre-scout (`review_and_fix.py` reads `step2-external-scout-eligible.txt`) may misroute.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add `step2-external-scout-eligible.txt` to preserved artifacts; document atomic write after successful scout normalization and `clear_external_scout_state()` on claude_fallback and cursor-presence fallback before emitting the envelope


### FINDING_4: OOS materialization lacks fail-closed bail semantics on complete path
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation
- **Severity**: important
- **Concern**: The plan only says to preserve the `materialize-manifest-oos.sh` call, not the full fail-closed semantics. When a manifest carries OOS observations and materialization fails (`REASON=manifest-oos-materialization-failed`, harness Test 26), a thin Python wrapper can drop failures silently on `STATUS=complete`, leaving unmaterialized OOS and breaking Step 9a.1 disposition.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Port the complete-path block from `step2-implement.sh` (~1152-1193): `--count-only` precheck, materialize invocation, `run-log append-failure` on failure, and `emit_bailed manifest-oos-materialization-failed` when OOS count > 0; pin Test 26 in pytest port list
  - From Cursor-Innovation: Add explicit port checklist for materialize-manifest-oos.sh argv, count-only probe, and run-log append-failure contract in step2-dispatch.md or implement_dispatch.py notes


### FINDING_5: Recovery-paths stdout KV contract mismatches silent bash behavior
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: The `implement recovery-paths` spec requires KV stdout, but the absorbed bash script `compute-step2-recovery-paths.sh` emits none (exit 0/1 only). Adding KVs changes the contract and can break quiet-stream expectations.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Change recovery_paths behavior to match bash: write only `--out-file`, no stdout; exit 0 when candidates exist and 1 when empty; drop "Emit only contract KVs on stdout"


### FINDING_6: Step2-dispatch omits fixed timeout and token-budget-cap forwarding
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: The `implement step2-dispatch` behavior list omits fixed `--timeout 7200` and optional `--token-budget-cap` forwarding. Harness Test 17 and production runs can inherit a shorter default timeout or skip cap-hit short-circuit (Test 14), causing premature bail or unbounded spend.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Explicitly port `LAUNCHER_TIMEOUT=7200`, always pass `--timeout 7200` to launchers, forward `--token-budget-cap` when `LARCH_TOKEN_BUDGET_CAP_IMPLEMENT` is set, and map launcher `STATUS=cap_hit` to `REASON=cap_hit` without retry


### FINDING_7: Codex auth inventory harness not included in stale-reference sweep
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: Hardcoded Codex auth inventory in `scripts/test-lib-external-launcher-common.sh` still requires `launch-codex-implement.sh` in four docs. The plan retargets those docs to Python verbs but omits this harness; `make test-lib-external-launcher-common` (test-harnesses-11) asserts the exact inventory substring and will fail after doc retarget.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Add scripts/test-lib-external-launcher-common.sh to the stale-reference sweep; replace launch-codex-implement.sh with python/cli.py agent launch-codex-implement in _codex_auth_inventory


### FINDING_8: `codex-manifest-schema.digest.md` not updated with dispatcher cutover
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: The digest still names `step2-implement.sh` but the plan only updates `codex-manifest-schema.md`. Because digest sync is required, bail-token prose will still point at a deleted script after cutover.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Add ### UPDATED codex-manifest-schema.digest.md to retarget dispatcher references to skills/implement/references/step2-dispatch.md and python/implement_dispatch.py


### FINDING_9: Branch-gate and issue-anchor rules omitted from preserved path list
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: The preserved path list omits issue-anchor and `FORKED_TARGET` branch-gate rules. A port that only checks branch name will block unanchored main spawns (test 19d) or block forked main runs (test 19c).
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Add explicit port steps: read parent-issue.md ISSUE_NUMBER and/or session-env presence for issue-anchored fail-closed; read FORKED_TARGET from session-env to skip main/master and detached-head bails; pin harness cases 19b-19e in pytest


### FINDING_10: Stale-reference sweep omits tracked shell sources with retired basenames
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Concern**: The stale-reference sweep lists `.md` contract updates but omits live shell files that still contain retired basenames. Deleting `launch-cursor-implement.sh` / `step2-implement.sh` / `launch-codex-implement.sh` leaves full-path literals in tracked `.sh` sources; `make lint-retired-scripts` fails and Codex-auth inventory docs stay wrong.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Add these shell files to the sweep with the same Python CLI replacements used elsewhere: scripts/launch-review.sh, scripts/lib-cursor-auth.sh, scripts/external-tool-registry.sh, scripts/lib-cursor-launcher-common.sh, scripts/test-lib-external-launcher-common.sh




### FINDING_5: Plan omits needs_qa items[]→questions[] repair (Test 16)
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: The plan omits the `needs_qa` qa-pending `items[]`→`questions[]` repair path pinned by harness Test 16. When a manifest has `status=needs_qa` but no `needs_qa.questions` and `qa-pending.json` uses `items[]`, bash normalizes and emits `STATUS=needs_qa`; without the port, the dispatcher will bail `qa-pending-missing` instead, breaking the Step 2.3 Q/A redispatch loop.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Add explicit step2-dispatch port + pytest coverage for Test 16 repair semantics in implement_dispatch.py and skills/implement/references/step2-dispatch.md


### FINDING_6: step2-dispatch CLI argv surface narrower than step2-implement.sh
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Concern**: The planned `implement step2-dispatch` section documents only `--coder` and deprecated `--codex-available`, not the full `step2-implement.sh` argv surface (`--tmpdir`, `--plan-file`, `--feature-file`, `--cursor-present`, `--answers`, mutual exclusion with `--codex-available`, bad enum exit 2). `scripts/test-external-tool-registry.sh` calls the dispatcher from a nested cwd with all five path/coder flags; a Python CLI accepting only `--coder` breaks that harness and other direct callers after shell deletion.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Document and implement the same argv contract as `step2-implement.sh` on `implement step2-dispatch`, and have `run_dispatch_main` forward the derived tmpdir/plan/feature/cursor-present/answers values in-process.




### FINDING_3: OOS materialization fail-closed guard omits `--count-only` precheck failure branch
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: When `materialize-manifest-oos.sh --count-only` exits non-zero and the materialize call also fails, Bash still emits `REASON=manifest-oos-materialization-failed` (`step2-implement.sh:1173-1175`). The plan only covers bail when `count>0` and materialization fails, so a Python port may fail open on count-precheck failure alone.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Pin the Bash guard: bail when materialization_rc!=0 and (count_precheck_rc!=0 or count>0). Port Test 26 and add a count-precheck-failure pytest


### FINDING_4: Step 7a.1 undeclared working-tree diagnostic omitted from port plan
- **Reviewer(s)**: Cursor-Requirements, Codex-Generic
- **Severity**: important
- **Concern**: On complete external-implementer runs, Bash logs a Warnings entry when working-tree paths are not declared in manifest `files_touched` / `tests_added_or_modified` before commit-on-behalf (`test-step2-dispatch.sh` Test 18; `step2-implement.sh:973-1009`). The plan lists many preserved Step 2 behaviors but is silent on 7a.1, and its explicit harness port list skips Test 18. A literal port can drop this scope-drift breadcrumb and still pass the listed pytest matrix.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Add 7a.1 preservation to `implement step2-dispatch`, `skills/implement/references/step2-dispatch.md`, and `python/test_implement_dispatch.py` (port Test 18: undeclared path → Warnings in `execution-issues.md`, commit still proceeds).
  - From Codex-Generic: Add the Step 7a.1 warning behavior to python/implement_dispatch.py and port the existing undeclared-change pytest case


### FINDING_5: Stale-reference sweep omits `SECURITY.md`
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Concern**: After deletion, `SECURITY.md` still references retired Step 2 surfaces (`scripts/launch-codex-implement.sh`, `scripts/launch-cursor-implement.sh`, `skills/implement/scripts/step2-implement.sh`) in delegation, outer-launcher, Codex-auth, and stderr-tail sections. The plan adds only a short note and does not list `SECURITY.md` in its sweep checklist. `make lint-retired-scripts` fails until those lines are retargeted.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Add SECURITY.md to the stale-reference sweep and extend its UPDATED section to retarget existing implement/dispatcher path literals to `python/cli.py agent launch-{codex,cursor}-implement` and `python/cli.py implement {run-dispatch,step2-dispatch}` / `python/implement_dispatch.py`, not only append a new note.


### FINDING_7: Absorbed launcher argv surface omits `--timing-task-kind` contract
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Concern**: Existing implement launcher callers or harnesses that pass empty or flag-shaped timing kinds rely on `--timing-task-kind` validation in `launch-codex-implement.sh:84-85` and `launch-cursor-implement.sh:84-85` (exit 2 on invalid values). The Python port plan does not preserve this argv surface, risking argv-shape collapse and incorrect timing attribution.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Generic: Preserve --timing-task-kind in the shared Python launcher parser with the same CLI validation and env fallback, and port the existing Codex Test 13 and Cursor K4 cases



### FINDING_1: Step 2 contract doc must fully absorb deleted bash dispatcher authorities
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation
- **Severity**: important
- **Concern**: The planned `skills/implement/references/step2-dispatch.md` is described as a short bullet checklist, not a full port of the load-bearing contracts in `step2-implement.md` and `run-step2-dispatch.md`. Deleting those bash authorities without carrying over normative detail (spawn baselines, per-tool filenames, `codex-step2-out` layout, scout eligibility, retry/clean-state rules, recovery triplet rules, orchestrator foreground-wait / no-`ScheduleWakeup` notes, implementer-coder set, `TOOL_TAG` paths, stdout `MANIFEST` omission rules, launcher retry guards, bail-reason cross-refs) would leave `SKILL.md` NEVER #8, `codex-manifest-schema.md`, and agent-lint / harness edit-in-sync pins without a complete replacement. C4b would be the first migration to ship without a surviving full Step 2 contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Require step2-dispatch.md to absorb the full bodies of step2-implement.md and run-step2-dispatch.md with path retargets only, or explicitly state that step2-dispatch.md plus python/implement_dispatch.py plus python/test_implement_dispatch.py are jointly authoritative and list every invariant that must be copied verbatim.
  - From Cursor-Innovation: Require step2-dispatch.md to carry over the surviving invariants from step2-implement.md (update path names to python/implement_dispatch.py and python/cli.py verbs), not only the abbreviated Include list in the plan


### FINDING_4: `implement run-dispatch` must validate `CURSOR_PRESENT` as `true|false` before dispatch
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Concern**: `run-step2-dispatch.sh` rejects `CURSOR_PRESENT` values other than `true`/`false` with exit 2 before dispatch. The plan only requires cursor fail-closed when `CURSOR_PRESENT!=true`, so corrupted values like `yes` could reach `step2-dispatch` and change fallback or error semantics relative to bash.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Add the same `true|false` guard to `run_dispatch_main` (exit 2 with the current diagnostic) before calling the shared dispatcher; port the existing harness case in pytest



