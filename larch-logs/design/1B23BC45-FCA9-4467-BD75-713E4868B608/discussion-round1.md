## Decision 1: Protection approach
- **Question**: Which protection approach for the pre-coder snapshot integrity fix (relocate / chmod / recompute)?
- **Resolution**: Relocate the pre-coder snapshots to a coder-unreachable location outside the Codex `--add-dir "$round_dir"` reach. The carryover predicate reads from the trusted location. chmod-in-place rejected (coder retains directory write access via `--add-dir`); recompute rejected (pre-coder uncommitted working-tree dirt cannot be reconstructed after the coder edits those paths).
- **Source**: user

## Decision 2: Artifact scope (which artifacts to protect)
- **Question**: Protect only `pre-coder-path-diffs/*.patch`, or the full pre-coder artifact set?
- **Resolution**: Full pre-coder set — `pre-coder-head.txt`, `pre-coder-tracked-paths.txt`, AND `pre-coder-path-diffs/`. All three are trusted by `path_is_pre_coder_carryover` / `path_matches_pre_coder_snapshot`; tampering `pre-coder-head.txt` alone is an equivalent bypass.
- **Source**: user

## Decision 3: Preserve #3272 carryover semantics (hard constraint)
- **Question**: Must the fix preserve the #3272 fail-closed carryover behavior exactly?
- **Resolution**: Yes. After relocation, `path_is_pre_coder_carryover`, `path_matches_pre_coder_snapshot`, `round_coder_delta_paths`, `collect_round_stage_paths`, `round_tracked_dirty_outside_manifest`, and `round_has_non_carryover_tracked_residue` must classify carryover vs. genuinely-new dirt identically — only the storage location of the trusted snapshots changes.
- **Source**: codebase

## Decision 4: Do not break the step5-loop telemetry consumer (hard constraint)
- **Question**: Does anything outside review-and-fix.sh consume the pre-coder artifacts?
- **Resolution**: Yes — `skills/review-and-fix/scripts/review-implement-step5-loop.sh:339-341` reads `${post_round_dir}/pre-coder-head.txt` (with `post-coder-head.txt`) to compute structural diff-size telemetry. The relocation must keep this telemetry working (either keep a round_dir copy of `pre-coder-head.txt`, or update this consumer to read the trusted copy). This is telemetry, not a security gate.
- **Source**: codebase

## Decision 5: Update the carryover test harness (in-scope)
- **Question**: Does relocating change test expectations?
- **Resolution**: Yes — `skills/review-and-fix/scripts/test-review-and-fix.sh` (carryover + index-carryover cases ~lines 503-555) builds the snapshot artifacts under `round_dir/pre-coder-path-diffs/` and `eval`s the predicate functions. These tests must be updated to construct artifacts at the new trusted location (or to pass the snapshot dir the functions now use). Test changes are in-scope for this fix.
- **Source**: codebase

## Decision 6: Threat surface is the Codex coder path (scope clarification)
- **Question**: Which coder dispatch path exposes the snapshots?
- **Resolution**: The Codex path (`review-and-fix.sh:273`) passes `--add-dir "$round_dir"`, granting the coder write access to the snapshot subdir. The Cursor path (`:292-297`) uses `--workspace "$PWD"` (repo root); `$round_dir` lives under `$IMPLEMENT_TMPDIR` (outside the repo), so Cursor cannot reach it. Relocating outside `--add-dir "$round_dir"` fully closes the Codex exposure and is complete.
- **Source**: codebase

## Decision 7: Non-goal — do not narrow the coder's round_dir grant (scope boundary)
- **Question**: Should this change also remove/narrow `--add-dir "$round_dir"` from the Codex dispatch?
- **Resolution**: No. The coder is told "Session directory for logs/artifacts: $round_dir" and may write artifacts there; narrowing that grant is a separate concern with its own regression risk. Out of scope for this fix (candidate OOS follow-up). Minimum change = relocate the trusted snapshots only.
- **Source**: codebase + minimum-change bias

## Decision 8: Audit-log artifacts (scope clarification)
- **Question**: Does relocating snapshots out of round_dir break run-log auditability?
- **Resolution**: No consumer reads `round_dir/pre-coder-path-diffs/` from published `larch-logs/`; the only readers are inside review-and-fix.sh. Relocating means the raw transient patches won't appear in the committed round-N dir, which is acceptable (they are integrity-internal, not audited artifacts).
- **Source**: codebase
