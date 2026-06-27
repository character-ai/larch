### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/design/design_lifecycle.py:3793-3802
- **Concern**: Pin missing-sidecar dirty probe to sidecar-absent elif plus baseline st_size > 0. Scenario: `_detect_step2b_drafter_dirty_block` only summarizes missing-sidecar baseline-delta behavior. Production uses `elif` after the sidecar file check and requires `step2b-drafter-baseline.porcelain` to exist with `st_size > 0` before comparing git porcelain (3798-3802). A literal extract can drop the size guard or turn the baseline probe into a second independent `if`, re-running baseline comparison when a sidecar file exists but is not dirty, or treating a zero-byte baseline as a positive delta and routing a clean-tree Codex skip into dirty-tree recovery.
- **Proposed resolution**: Add an explicit contract: when `step2b-drafter-status.txt.dirty-tree` is absent, run the baseline-delta probe only in an `elif` branch; require baseline file exists and `stat().st_size > 0`; compare with `git -C Path.cwd() status --porcelain`; set `dirty_reason=missing-sidecar-positive-baseline-delta` only on mismatch.



### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/larch/design/design_lifecycle.py:3644-3678
- **Concern**: Pin immediate abort after `_prepare_step2b_drafter_run` before steps 2-10. Scenario: Orchestration steps 2 and 6 say return immediately on failure, but step 1 only says run `_prepare_step2b_drafter_run` and the helper note is vague about early exits. Production returns at parse rc 2, missing tmpdir rc 1, invalid tmpdir rc 2, folded Step 2a rc 1, and plugin-root rc before pause seeding, artifact reset, or launch (3644-3664). A thin main that always continues can seed `.step2b-postplan-fallback-used`, unlink artifacts, or launch after a failed prepare.
- **Proposed resolution**: Add orchestration rule: if prepare returns a non-success int, `step2b_drafter_main` must return that code immediately and must not run steps 2-10; pin the existing rc mapping for parse, tmpdir, Step 2a, and plugin-root failures.



### FINDING_3:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/design/design_lifecycle.py:3644-3678
- **Concern**: Pin thin-main abort when `_prepare_step2b_drafter_run` fails. Scenario: The plan pins handler `return` propagation at orchestration step 10 but not immediate exit when step 1 fails. Production returns at each prepare gate (parse `ValueError` rc 2, missing `DESIGN_TMPDIR` rc 1, invalid tmpdir rc 2, folded Step 2a rc 1, plugin-root rc) before pause, fallback seed, artifact reset, or launch. A thin main that always runs steps 2-10 after a failed prepare can write `.step2b-postplan-fallback-used`, unlink stale artifacts, and reach launch on invalid state; `test_step2a_rejects_missing_design_tmpdir` and `test_step2a_rejects_relative_design_tmpdir` regress.
- **Proposed resolution**: Add an orchestration contract: `prep = _prepare_step2b_drafter_run(argv); if isinstance(prep, int): return prep` (or equivalent explicit early-int union). Enumerate preserved rc values per gate in the prepare helper spec.



### FINDING_4:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/design/design_lifecycle.py:3658-3666
- **Concern**: Pin resolved `DESIGN_TMPDIR` env sync and `Ctx` overrides in `_prepare_step2b_drafter_run`. Scenario: Prepare says rehydrate env and build `Ctx` but omits production's post-resolve mutations: `design_tmpdir = Path(env["DESIGN_TMPDIR"]).resolve()`, `os.environ["DESIGN_TMPDIR"] = str(design_tmpdir)`, `normalized_overrides = {config.ENV_DESIGN_TMPDIR: str(design_tmpdir)}`, and `Ctx.from_mapping({**env, **os.environ, **normalized_overrides})`. Dropping them during extraction can leave pause-save/postplan with a relative or stale tmpdir while subprocess launch uses the resolved path.
- **Proposed resolution**: Pin those four lines verbatim in `_prepare_step2b_drafter_run` before returning the prepare tuple.



### FINDING_5:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: python/larch/design/design_lifecycle.py:3727-3730
- **Concern**: Git-status baseline probe is not pinned to decoded captured stdout. Scenario: If the extraction drops `capture_output=True, text=True`, `status.stdout` is empty or bytes, so writing `step2b-drafter-baseline.porcelain` and building the `--baseline-porcelain` branch no longer matches current behavior.
- **Proposed resolution**: Explicitly require `subprocess.run([...], capture_output=True, text=True, check=False)` for the baseline probe and keep the current write-or-unlink branch unchanged.



### FINDING_6:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: python/larch/design/design_lifecycle.py:3833-3841
- **Concern**: Plan-review preview omits `text=True`. Scenario: Without decoded stdout, `preview.stdout.splitlines()` yields bytes and the `[plan-preview]` relay prints byte reprs instead of the current text lines, changing wrapper-visible success output.
- **Proposed resolution**: Pin `text=True` together with `capture_output=True, env=env, check=False` on the preview call.



### FINDING_7:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/design/design_lifecycle.py:3644-3678
- **Concern**: Pin thin-main abort when `_prepare_step2b_drafter_run` fails. Scenario: The plan pins handler returns at step 10 but `_prepare_step2b_drafter_run` only says return a tuple or use an unspecified early-exit pattern. Production returns immediately on parse `ValueError` (rc 2), missing `DESIGN_TMPDIR` (rc 1), invalid tmpdir (rc 2), folded Step 2a failure (rc 1), and plugin-root failure before pause, fallback seed, artifact reset, or launch. A thin main that always runs steps 2-10 after a failed prepare can seed `.step2b-postplan-fallback-used`, reset artifacts, or launch the drafter under a partial `Ctx`, breaking conflicting-sentinel refusal and pause-before-seed tests.
- **Proposed resolution**: Add an explicit orchestration contract: `_prepare_step2b_drafter_run` returns either an `int` exit code or a prepared tuple, and `step2b_drafter_main` must `return` that `int` immediately before step 2. Pin the rc mapping to production lines 3648-3664 (including rc 1 vs 2 distinctions and no `DRAFTER_NEXT_ACTION` on prepare failures).



### FINDING_8:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/larch/design/design_lifecycle.py:3888-3893
- **Concern**: Pin exact dirty-recovery sidecar and warning literals in `_handle_step2b_drafter_dirty_recovery`. Scenario: The dirty-recovery helper says preserve `dirty-tree-detected.env` and warning text without quoting production literals. Inline-fallback pins its warning verbatim, but dirty recovery does not. Mechanical extraction can typo keys or drop `STATUS=dirty` / `STAGE=step-2b-drafter` / `RECOVERY_REQUIRED=true` / `REASON={dirty_reason}`, breaking `skills/design/SKILL.md` dirty-tree recovery gating that keys off `STAGE=step-2b-drafter` and `RECOVERY_REQUIRED=true`.
- **Proposed resolution**: Pin the exact write and print sequence from lines 3889-3892: sidecar `STATUS=dirty\nSTAGE=step-2b-drafter\nRECOVERY_REQUIRED=true\nREASON={dirty_reason}\n`, warning `**⚠ 2b: drafter subprocess may have introduced working-tree mutations; dirty-tree recovery is required before fallback.**`, then `DRAFTER_VENDOR={vendor}`, then `_emit_drafter_next_action("dirty-tree-recovery")`.



