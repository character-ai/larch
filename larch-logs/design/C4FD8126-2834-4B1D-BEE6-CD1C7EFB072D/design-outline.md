## Proposed Design Outline

### Goals
- Narrow the Codex Step-2 `--add-dir` grant from all of `$IMPLEMENT_TMPDIR` to a dedicated `codex-step2-out/` subdir.
- Move the three Codex-written outputs (manifest.json, qa-pending.json, transcript) into that subdir.
- Update all readers of those paths (step-7a.sh, test harnesses).

### Non-goals
- No parallel change to the Cursor launcher (uses `--workspace`, not `--add-dir`; intentional asymmetry).
- No changes to `MANIFEST_RAW_PATH` or `SIDECAR_LOG` (not Codex-written; stay at `$IMPLEMENT_TMPDIR`).
- No broader refactor of the implement workflow beyond the narrowed grant.

### Approach sketch
- In `step2-implement.sh`: add `STEP2_OUT_DIR="$TMPDIR_ARG/codex-step2-out"`, `mkdir -p` it, and repoint `MANIFEST_PATH`, `QA_PENDING_PATH`, `TRANSCRIPT_PATH` there.
- `launch-codex-implement.sh`: derives `SESSION_TMPDIR=$(cd "$MANIFEST_DIR" && pwd -P)` automatically; `--add-dir "$SESSION_TMPDIR"` narrows to the subdir with no other changes to the launcher logic.
- `step-7a.sh`: update three hardcoded `$IMPLEMENT_TMPDIR/codex-impl-transcript.txt*` paths to use the subdir.
- Document the `--add-dir` vs `--workspace` asymmetry in `.claude/rules/external-tool-launcher-parity.md`.
- Add/update assertions in `test-codex-implementer.sh` and `test-step2-dispatch.sh`.

### Surfaces in scope
- `skills/implement/scripts/step2-implement.sh`
- `scripts/launch-codex-implement.sh` (comment update + auto-narrowing; no argv changes)
- `skills/implement/scripts/step-7a.sh`
- `.claude/rules/external-tool-launcher-parity.md`
- `skills/implement/scripts/test-codex-implementer.sh`
- `skills/implement/scripts/test-step2-dispatch.sh`
- `.md` siblings for changed scripts (per `.claude/rules/script-md-siblings.md`)

### Open questions
- None.
