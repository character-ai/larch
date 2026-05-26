### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/implement/scripts/test-step-7a.sh:464-470
- **Concern**: Plan adds call-log coverage for `--base-remote origin --base-ref main` on the non-fork `green` path only; existing `forked-target` still asserts rebase argv but not generator argv. Scenario: Fork-mode generation can regress to `origin/main` in `generate-code-flow-diagram.sh:58` while `diagram-skip-forked` and rebase assertions stay green; fork PRs get wrong prompt diffs with no harness failure
- **Proposed resolution**: Extend `forked-target` (or add a forked generation case) with `assert_contains` for `generate-code-flow-diagram.sh` and `--base-remote upstream --base-ref main` in `calls.log`, mirroring the planned `green` assertion

### FINDING_2:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/scripts/test-step-7a.sh:464-470
- **Concern**: The proposed tests never prove the forked runtime generation path passes upstream/main into generate-code-flow-diagram.sh. Scenario: The new diagram-skip-forked case intentionally skips generation, the green assertion only covers --forked-target false, and the existing forked-target case only asserts rebase-checkpoint-probe args; step-7a could still pass origin/main to the generator for forked runtime changes without the planned tests failing
- **Proposed resolution**: Augment the existing forked-target case, or add a non-skip forked runtime case, to assert calls.log contains generate-code-flow-diagram.sh ... --base-remote upstream --base-ref main

### FINDING_3:
- **Reviewer(s)**: Codex-Arch
- **Severity**: latent
- **Focus area**: architecture
- **Location**: generate-code-flow-diagram.sh:28-35,58
- **Concern**: The plan adds public base-ref flags without the validation pattern already used by sibling base-ref scripts. Scenario: Empty or whitespace base values are not rejected by the current fail_usage count checks despite the plan claiming they are; if the new merge-base line uses ${BASE_REMOTE}/${BASE_REF} unquoted, bad values can split into unintended git argv and make the generator diff against the wrong or fallback range
- **Proposed resolution**: Follow scripts/rebase-push.sh and scripts/ci-status.sh: validate BASE_REMOTE and BASE_REF as non-empty ^[A-Za-z0-9._/-]+$, build BASE_TARGET="${BASE_REMOTE}/${BASE_REF}", and quote "$BASE_TARGET" in the git merge-base call

### FINDING_4:
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/implement/scripts/test-step-7a.sh:464-470
- **Concern**: Plan augments `green` for `--base-remote origin` on the generator stub but leaves the existing `forked-target` case without a symmetric assertion. Scenario: With `--forked-target true`, `CASE_DIR` has no git repo so the classifier always falls through to generation; a regression that drops `--base-remote upstream --base-ref main` on the `generate-code-flow-diagram.sh` call still passes `forked-target passes upstream argv` (rebase-only)
- **Proposed resolution**: Extend `forked-target` (or add a forked generate case) to assert `generate-code-flow-diagram.sh` in `calls.log` includes `--base-remote upstream --base-ref main`

### FINDING_5:
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/scripts/test-step-7a.sh:464-470
- **Concern**: Fork-mode generator pass-through is still untested. Scenario: The proposed diagram-skip-forked case proves the classifier uses upstream/main, but it skips generator execution; the augmented green case only proves origin/main is passed in non-fork mode, so a regression that keeps forked generator calls on origin/main would pass the planned tests
- **Proposed resolution**: Add an assertion to the existing forked-target case, or add a runtime-change fork fixture, verifying generate-code-flow-diagram.sh is invoked with --base-remote upstream --base-ref main when --forked-target true

### FINDING_6:
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Focus area**: security
- **Location**: skills/implement/scripts/generate-code-flow-diagram.sh:28-58
- **Concern**: Generator base-ref argv lacks validation despite being used to build a git ref. Scenario: The plan says whitespace or empty values are rejected by existing fail_usage machinery, but the current parser pattern only checks argument count; an empty or whitespace value can silently produce /main or split words and then fall back to HEAD~1, generating a diagram for the wrong diff
- **Proposed resolution**: Add explicit BASE_REMOTE and BASE_REF validation matching rebase-push.sh and ci-status.sh, require non-empty safe ref characters, build BASE_TARGET="${BASE_REMOTE}/${BASE_REF}", and quote "$BASE_TARGET" in git merge-base

### FINDING_7:
- **Reviewer(s)**: Codex-Edge
- **Severity**: nit
- **Focus area**: code-quality
- **Location**: skills/implement/scripts/generate-code-flow-diagram.sh:14-16
- **Concern**: The script usage string is not included in the plan update. Scenario: The markdown Usage fence will list --base-remote and --base-ref, but --help and fail_usage output from the script would still omit the new supported flags
- **Proposed resolution**: Update the usage() string in generate-code-flow-diagram.sh to include [--base-remote NAME] [--base-ref BRANCH] alongside the markdown doc

### FINDING_8:
- **Reviewer(s)**: Cursor-Innovation, Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/scripts/test-step-7a.sh:464-470
- **Concern**: Fork-mode generator argv still untested when generation runs. Scenario: `diagram-skip-forked` only covers the skip path; existing `forked-target` invokes the generator stub on a non-git `CASE_DIR` and never asserts `--base-remote upstream --base-ref main` on `generate-code-flow-diagram.sh`. A regression that fixes the classifier but omits upstream flags on the generator call (the #2844 second callsite) would pass this PR’s new tests.
- **Proposed resolution**: Add a forked generation case (extend `forked-target` with `make_forked_skip_repo`-style upstream fixture plus a runtime diff, or a dedicated `diagram-green-forked`) that asserts `calls.log` contains `generate-code-flow-diagram.sh` with `--base-remote upstream --base-ref main`.

### FINDING_9:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/scripts/test-generate-code-flow-diagram.sh:45-62
- **Concern**: Plan skips the existing real generator harness while changing generate-code-flow-diagram.sh argv parsing and prompt base selection. Scenario: step-7a tests stub the generator, so a broken --base-remote parser or a prompt that still diffs origin/main can pass all proposed tests
- **Proposed resolution**: Update test-generate-code-flow-diagram.sh to invoke the real helper with default and upstream/main flags, have the launch stub capture/read --prompt-file, and assert the Changed files section reflects the selected base; update test-generate-code-flow-diagram.md

### FINDING_10:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/implement/scripts/test-step-7a.sh:464-470
- **Concern**: Fork-mode generator argv propagation is not asserted. Scenario: The new diagram-skip-forked case intentionally skips generation, and the green assertion only proves non-fork origin/main; an implementation that always passes origin/main to the generator in fork mode would not be caught
- **Proposed resolution**: Add an assertion to the existing forked-target case, or a non-skipping fork fixture, that calls.log contains generate-code-flow-diagram.sh --base-remote upstream --base-ref main

### FINDING_11:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: latent
- **Focus area**: correctness
- **Location**: skills/implement/scripts/generate-code-flow-diagram.sh:28-35,58
- **Concern**: New base flags are planned as loose strings with only arg-count validation. Scenario: The plan says empty/whitespace values are rejected, but the existing fail_usage pattern only checks that a following argv token exists; malformed values can produce /main or split refs and silently fall back to HEAD~1
- **Proposed resolution**: Validate non-empty base remote/ref with the same supported-character regex used by rebase-push.sh, build a BASE_TARGET variable, and quote it in git merge-base

### FINDING_12:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: latent
- **Focus area**: security
- **Location**: skills/implement/scripts/generate-code-flow-diagram.sh:28-58
- **Concern**: The proposed --base-remote and --base-ref flags are only presence-checked, not value-validated, while sibling base-ref consumers reject unsupported characters.. Scenario: An external/manual caller can pass an empty, whitespace, or option-looking base value; the generator then builds a misleading git revision or falls back to HEAD~1, despite the plan claiming those values are rejected.
- **Proposed resolution**: Add the same non-empty regex validation used by ci-status.sh and rebase-push.sh for BASE_REMOTE and BASE_REF before constructing the prompt, and add a small generator harness assertion for invalid values.

### FINDING_13:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/test-implement-rebase-macro.sh:98-104; skills/implement/scripts/step-7a.sh:396-399
- **Concern**: Plan removes the guarded BASE_ARGS literal but does not update the structural rebase-macro harness. Scenario: The harness greps step-7a.sh for `if [ "${forked_target:-false}" = "true" ]` and `BASE_ARGS=(--base-remote upstream --base-ref main)` within 10 lines of the 7a.r probe call; unconditional `BASE_ARGS=(--base-remote "$base_remote" --base-ref "$base_ref")` fails assertion (C') and breaks `make lint` despite the plan's lint step
- **Proposed resolution**: Add a plan step to update `scripts/test-implement-rebase-macro.sh` (and its `.md` if needed) to assert module-level `base_remote`/`base_ref` resolution plus derived `BASE_ARGS` near the wrapper instead of the old guarded literal

### FINDING_14:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/implement/scripts/test-step-7a.sh:464-470
- **Concern**: Fork-mode generator invocation is not covered. Scenario: The plan requires the generator call to use upstream/main when forked_target=true, but the new diagram-skip-forked case skips the generator and the augmented green case only proves origin/main for non-fork mode. A regression could keep passing origin/main to generate-code-flow-diagram.sh in fork mode whenever the classifier falls through to generation.
- **Proposed resolution**: Augment the existing forked-target case or add a forked non-skip fixture that forces generation and asserts calls.log contains generate-code-flow-diagram.sh --implement-tmpdir ... --base-remote upstream --base-ref main.

### FINDING_15:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/scripts/test-generate-code-flow-diagram.sh:42-53
- **Concern**: Real generator flag parsing and prompt base selection are untested. Scenario: The plan adds --base-remote/--base-ref and changes generate-code-flow-diagram.sh:58, but explicitly skips updating the existing direct generator harness. The step-7a harness uses a stub generator, so it cannot catch a typo in the real parser or a prompt diff still using origin/main.
- **Proposed resolution**: Extend test-generate-code-flow-diagram.sh to capture the prompt file from the launch stub and assert a run with --base-remote upstream --base-ref main lists files relative to upstream/main; also assert defaults still preserve origin/main behavior.

### FINDING_16:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: nit
- **Focus area**: code-quality
- **Location**: skills/implement/scripts/test-step-7a.md:5-25
- **Concern**: The plan changes harness cases but omits sibling harness documentation. Scenario: .claude/rules/script-md-siblings.md requires updating a script sibling .md when behavior changes. Adding diagram-skip-forked and new call-log assertions leaves the Cases list stale, and docs/linting.md:263 will also understate coverage/counts.
- **Proposed resolution**: Add updates for skills/implement/scripts/test-step-7a.md and docs/linting.md alongside the test-step-7a.sh changes.

### FINDING_17:
- **Reviewer(s)**: Cursor-dyn-shell-scope-ordering
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/test-implement-rebase-macro.sh:98-105
- **Concern**: Plan refactors step-7a BASE_ARGS but omits (C') harness update. Scenario: (C') greps a 10-line window above the 7a.r probe for `if [ "${forked_target:-false}" = "true" ]` and the literal `BASE_ARGS=(--base-remote upstream --base-ref main)`; plan moves `base_remote`/`base_ref` before token-ledger (~332) and replaces the conditional block (~396-399) with `BASE_ARGS=(--base-remote "$base_remote" --base-ref "$base_ref")`, so both greps fail and `make lint` / `test-implement-rebase-macro` breaks
- **Proposed resolution**: Add `scripts/test-implement-rebase-macro.sh` to the plan file list; relax (C') for step-7a to accept derived `BASE_ARGS=(--base-remote "$base_remote" --base-ref "$base_ref")` and fork selection via early `base_remote`/`base_ref` assignment (or document an intentional 10-line-local duplicate if policy requires proximity)

### FINDING_18:
- **Reviewer(s)**: Codex-dyn-shell-scope-ordering
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/test-implement-rebase-macro.sh:98-104; skills/implement/scripts/step-7a.sh:396-403
- **Concern**: Plan replaces the guarded BASE_ARGS literal in step-7a.sh but does not update the structural harness that greps for that exact guard and literal near the 7a.r wrapper call. Scenario: make lint runs test-implement-rebase-macro and will fail after BASE_ARGS becomes unconditionally derived from base_remote/base_ref
- **Proposed resolution**: Update the harness to assert the new module-level base_remote/base_ref resolution plus BASE_ARGS=(--base-remote "$base_remote" --base-ref "$base_ref") near the wrapper, or keep the old literal shape and derive only the generator/classifier refs

### FINDING_19:
- **Reviewer(s)**: Cursor-dyn-env-argv-doc-parity
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:45 / skills/implement/scripts/step-7a.sh:329-331
- **Concern**: Proposed step-7a.md documents fork activation via `LARCH_FORKED_TARGET=true`, but step-7a.sh never reads that name from the shell environment; it is resolved only after the argv loop via `read_session_key` against `session-env.sh`. Scenario: Operators who `export LARCH_FORKED_TARGET=true` (or rely on an env-var mental model) still get `forked_target=false` and `origin/main` classifier/generator behavior
- **Proposed resolution**: Reword step-7a.md to state session-file rehydration only (when `--forked-target` is omitted), or add an explicit `${LARCH_FORKED_TARGET:-}` fallback before/alongside `read_session_key` if env configuration is intended

### FINDING_20:
- **Reviewer(s)**: Codex-dyn-env-argv-doc-parity
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:43-55; skills/implement/scripts/step-7a.sh:241-330; scripts/read-session-env-key.sh:96-104; skills/implement/scripts/generate-code-flow-diagram.md:10-14
- **Concern**: Plan documents LARCH_FORKED_TARGET as an activation path, but step-7a.sh only accepts --forked-target or reads a key from session-env.sh via read_session_key; the companion generator doc update only surfaces argv propagation.. Scenario: An operator who configures LARCH_FORKED_TARGET=true in the process environment and omits --forked-target still falls through to the session-env/default false path, so the classifier and generator use origin/main while step-7a.md would imply upstream/main.
- **Proposed resolution**: Update the plan to either implement and test direct environment fallback for LARCH_FORKED_TARGET before/defaulting the session-key read, or narrow the docs to session-env fallback wording. Mirror the same resolved fork-mode wording in generate-code-flow-diagram.md so argv and environment/session configuration are not documented asymmetrically.

### FINDING_21:
- **Reviewer(s)**: Cursor-dyn-fork-generator-callsite-test
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/scripts/test-step-7a.sh:464-470 (existing); plan test-step-7a.sh §29-41 (proposed)
- **Concern**: No harness case runs forked_target=true with a real upstream git fixture, diff >2 non-runtime files, and asserts generate-code-flow-diagram.sh is invoked with --base-remote upstream. Scenario: Proposed diagram-skip-forked only asserts the generator is absent from calls.log; augmented green only checks --base-remote origin when --forked-target false. Existing forked-target (lines 464-470) asserts upstream argv on rebase-checkpoint-probe.sh only. A regression that still passes upstream to rebase but omits --base-remote/--base-ref on the step-7a.sh:346 generator call (or passes origin) would not fail CI
- **Proposed resolution**: Add make_forked_generate_repo() (upstream remote, no origin; >2 docs-only paths vs upstream/main) plus new_case diagram-generate-forked (or extend forked-target to cd into that repo) mirroring green success assertions and assert_file_contains on calls.log for generate-code-flow-diagram.sh … --base-remote upstream --base-ref main; keep diagram-skip-forked for the skip path

### FINDING_22:
- **Reviewer(s)**: Codex-dyn-fork-generator-callsite-test
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:32-41,89-91; skills/implement/scripts/test-step-7a.sh:363-374,464-470
- **Concern**: No forked generator-invocation harness case covers the upstream base args path. Scenario: The proposed diagram-skip-forked case intentionally asserts generate-code-flow-diagram.sh is absent from calls.log, and the proposed green assertion only proves --base-remote origin for non-fork mode. Current test-step-7a.sh has diagram-skip as non-fork skip and forked-target only checks rebase-checkpoint-probe upstream argv, so the forked_target=true path where the diff exceeds the two-file cap and the generator is called with --base-remote upstream is absent from the harness entirely.
- **Proposed resolution**: Add a forked generation case, for example make_forked_large_repo with upstream/main, no origin, and three docs-only changed files on the feature branch, run step-7a with --forked-target true, assert DIAGRAM_STATUS=ok and calls.log contains generate-code-flow-diagram.sh --implement-tmpdir ... --base-remote upstream --base-ref main.
