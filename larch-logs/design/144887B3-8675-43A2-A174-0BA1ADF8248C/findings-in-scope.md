### FINDING_1: Pin missing-sidecar dirty probe to elif plus baseline st_size guard
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: `_detect_step2b_drafter_dirty_block` must preserve production's missing-sidecar baseline-delta behavior: only in an `elif` after the sidecar file check, requiring `step2b-drafter-baseline.porcelain` to exist with `st_size > 0` before comparing git porcelain (3798-3802). A literal extract can drop the size guard or turn the baseline probe into a second independent `if`, re-running baseline comparison when a sidecar file exists but is not dirty, or treating a zero-byte baseline as a positive delta and routing a clean-tree Codex skip into dirty-tree recovery.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add an explicit contract: when `step2b-drafter-status.txt.dirty-tree` is absent, run the baseline-delta probe only in an `elif` branch; require baseline file exists and `stat().st_size > 0`; compare with `git -C Path.cwd() status --porcelain`; set `dirty_reason=missing-sidecar-positive-baseline-delta` only on mismatch.

### FINDING_2: Pin immediate abort when `_prepare_step2b_drafter_run` fails
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic
- **Severity**: important
- **Concern**: Orchestration must abort before steps 2-10 when step 1 prepare fails. Production returns immediately at parse rc 2, missing tmpdir rc 1, invalid tmpdir rc 2, folded Step 2a rc 1, and plugin-root failure before pause seeding, artifact reset, or launch (3644-3664). The plan pins handler `return` propagation at step 10 but not this immediate exit; a thin main that always continues can seed `.step2b-postplan-fallback-used`, unlink artifacts, or launch after a failed prepare, breaking `test_step2a_rejects_missing_design_tmpdir`, `test_step2a_rejects_relative_design_tmpdir`, conflicting-sentinel refusal, and pause-before-seed tests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add orchestration rule: if prepare returns a non-success int, `step2b_drafter_main` must return that code immediately and must not run steps 2-10; pin the existing rc mapping for parse, tmpdir, Step 2a, and plugin-root failures.
  - From Cursor-Innovation: Add an orchestration contract: `prep = _prepare_step2b_drafter_run(argv); if isinstance(prep, int): return prep` (or equivalent explicit early-int union). Enumerate preserved rc values per gate in the prepare helper spec.
  - From Cursor-Pragmatic: Add an explicit orchestration contract: `_prepare_step2b_drafter_run` returns either an `int` exit code or a prepared tuple, and `step2b_drafter_main` must `return` that `int` immediately before step 2. Pin the rc mapping to production lines 3648-3664 (including rc 1 vs 2 distinctions and no `DRAFTER_NEXT_ACTION` on prepare failures).

### FINDING_3: Pin resolved DESIGN_TMPDIR env sync and Ctx overrides in prepare
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: `_prepare_step2b_drafter_run` must preserve production's post-resolve mutations after rehydrating env and building `Ctx`: `design_tmpdir = Path(env["DESIGN_TMPDIR"]).resolve()`, `os.environ["DESIGN_TMPDIR"] = str(design_tmpdir)`, `normalized_overrides = {config.ENV_DESIGN_TMPDIR: str(design_tmpdir)}`, and `Ctx.from_mapping({**env, **os.environ, **normalized_overrides})` (3658-3666). Dropping them during extraction can leave pause-save/postplan with a relative or stale tmpdir while subprocess launch uses the resolved path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Pin those four lines verbatim in `_prepare_step2b_drafter_run` before returning the prepare tuple.

### FINDING_4: Pin git-status baseline probe to decoded captured stdout
- **Reviewer(s)**: Codex-Innovation
- **Severity**: blocking
- **Concern**: If the extraction drops `capture_output=True, text=True`, `status.stdout` is empty or bytes, so writing `step2b-drafter-baseline.porcelain` and building the `--baseline-porcelain` branch no longer matches current behavior (3727-3730).
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Explicitly require `subprocess.run([...], capture_output=True, text=True, check=False)` for the baseline probe and keep the current write-or-unlink branch unchanged.

### FINDING_5: Pin plan-review preview subprocess text=True
- **Reviewer(s)**: Codex-Innovation
- **Severity**: blocking
- **Concern**: Without `text=True` on the plan-review preview call, `preview.stdout.splitlines()` yields bytes and the `[plan-preview]` relay prints byte reprs instead of the current text lines, changing wrapper-visible success output (3833-3841).
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Pin `text=True` together with `capture_output=True, env=env, check=False` on the preview call.

### FINDING_6: Pin dirty-recovery sidecar and warning literals
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: `_handle_step2b_drafter_dirty_recovery` must preserve exact production literals for the sidecar and warning text. The dirty-recovery helper says preserve `dirty-tree-detected.env` and warning text without quoting production literals; inline-fallback pins its warning verbatim, but dirty recovery does not. Mechanical extraction can typo keys or drop `STATUS=dirty` / `STAGE=step-2b-drafter` / `RECOVERY_REQUIRED=true` / `REASON={dirty_reason}`, breaking `skills/design/SKILL.md` dirty-tree recovery gating that keys off `STAGE=step-2b-drafter` and `RECOVERY_REQUIRED=true` (3888-3893).
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Pin the exact write and print sequence from lines 3889-3892: sidecar `STATUS=dirty\nSTAGE=step-2b-drafter\nRECOVERY_REQUIRED=true\nREASON={dirty_reason}\n`, warning `**⚠ 2b: drafter subprocess may have introduced working-tree mutations; dirty-tree recovery is required before fallback.**`, then `DRAFTER_VENDOR={vendor}`, then `_emit_drafter_next_action("dirty-tree-recovery")`.
