# scout-dynamic-archetypes.sh Contract

`scripts/scout-dynamic-archetypes.sh` asks external models to propose optional, ephemeral specialist reviewer archetypes for `/review`.

Primary caller: `skills/review/scripts/dispatch-panel.sh`. Plan-review callers use `skills/design/scripts/scout-plan-archetypes-wrapper.sh`, which forwards `--codex-present` / `--cursor-present`.

Accepted flags: `--mode diff|description`, `--diff-file` for diff mode, `--scope-files` for description mode, and exactly one of `--description-text` or `--description-file` (file paths are validated like other context inputs; prefer `--description-file` for large descriptions), optional `--plan-file`, required `--max-archetypes 0..8`, required `--output`, optional `--session-env-path`, optional `--timeout` (default `180` seconds), optional `--prompt-override-file PATH` (regular non-symlink file **under `CLAUDE_PLUGIN_ROOT` only**, max 256 KB), optional `--codex-present true|false` (default `false`), optional `--cursor-present true|false` (default `false`; accepted for API parity — scout does not invoke a Cursor tier).

Invariants:

- Dynamic archetypes are opt-in and capped at 8.
- Bulk context inputs are copied into `$SESSION_ROOT/staged-context/` (`diff.txt`, `scope-files.txt`, `plan.txt`, `description.txt`) before prompt assembly. The prompt references staged paths and instructs agents to Read them; bulk file bytes are not embedded (inline `--description-text` remains embedded when used).
- `validate_context_input_file` enforces canonical path, symlink rejection, allowed roots, and control-character rules; the former 256 KB per-file cap is removed for file inputs. Inline `--description-text` remains capped at 256 KB.
- Tier waterfall when `--codex-present true`: `launch-review.sh --tool codex` (override `SCOUT_DYNAMIC_ARCHETYPES_LAUNCH_REVIEW_SH`; forwards staged `--description-file` as bounded `--description-text`), then Claude via `launch-claude-subprocess.sh --read-tools --read-tools-add-dir "$SESSION_ROOT/staged-context"` (override `SCOUT_DYNAMIC_ARCHETYPES_LAUNCH_SH` only). Parse-gated winner selection (`tier_raw_is_scout_json`); `${raw}.cap-hit` sidecars are cleared before each tier launch. Multi-tier probe exhaustion with a failed final-tier launch emits that tier's launcher status (`claude-failed`, `codex-failed`, `timeout`); probe-only exhaustion emits `SCOUT_STATUS=empty`. Single-tier Claude-only probe/validation failures still emit `SCOUT_STATUS=parse-failed` with `SCOUT_FAIL_REASON` tokens `json_parse`, `invalid_archetypes_shape`, `validation_jq_error`, and `fence_strip_io`. Staged bulk files are capped at 1 MB; `--max-archetypes 0` skips staging.
- The output JSON is validated before publication (unchanged post-winner block).

Harness: `scripts/test-scout-dynamic-archetypes.sh`.

Edit in sync: update this file, the harness, `skills/review/scripts/dispatch-panel.sh`, `skills/design/scripts/scout-plan-archetypes-wrapper.sh`, `scripts/launch-claude-subprocess.sh`, and `SECURITY.md` when changing scout invocation, staging, waterfall semantics, or status tokens.
