# launch-gemini-review.sh

**Purpose**: Launch Gemini as a generic-only code reviewer and normalize the Gemini CLI JSON envelope into the plain-text reviewer output consumed by `collect-agent-results.sh`.

**Invocation**: `gemini -m "$GEMINI_MODEL" -p "$PROMPT" -o json --skip-trust --approval-mode yolo`, where `$GEMINI_MODEL` resolves as `${LARCH_GEMINI_MODEL:-${CLAUDE_PLUGIN_OPTION_GEMINI_MODEL:-gemini-2.5-pro}}`. The same `$GEMINI_MODEL` precedence is applied by `scripts/check-reviewers.sh` for the Gemini health probe so probe and reviewer use the same model. The probe deliberately stays at `--approval-mode plan` (least privilege) — it sends a fixed `"Respond with OK"` prompt and never invokes a tool. Reviewer launches append `--admin-policy "$SCRIPT_DIR/gemini-reviewer-policy.toml"` to load the plugin-shipped reviewer write-deny policy.

## Invariants

- Generic-only v1: accepts `--output`, `--timeout`, and `--prompt`; rejects specialist flags.
- `--timeout` must be a positive integer; `0`, empty, non-digit strings, and zero-valued multi-digit strings (`00`, `000`, ...) are rejected at argv-validation time with exit 2 (parallel to `scripts/run-external-agent.sh` and the `launch-*-implement.sh` family — closes #1115, #1167). Valid leading-zero positive values like `010` are accepted and interpreted as base-10 (`010` → 10s).
- Timeout is clamped to 600 seconds before launching Gemini.
- Uses `run-external-agent.sh --capture-stdout-only` so Gemini stdout JSON is written to `<output>.raw` while stderr remains diagnostic-only.
- Requires `jq`; missing `jq` fails closed with `MISSING_JQ`, empty output, non-zero `.done`, and a diagnostic.
- Parses `.response` as the only successful output field. `.error`, missing `.response`, or empty `.response` fail closed.
- Writes normalized plain text to `--output` atomically, then writes `<output>.done` last.
- Writes `<output>.meta` with `TOOL=gemini` and `CMD_JSON=` pointing at the redacted launcher invocation, so retry paths replay JSON normalization rather than raw `gemini`. Only the on-disk encoding changed: the retry replay model remains "launcher argv with the prompt body replaced by a sha256 prefix + byte length."
- Loads `scripts/gemini-reviewer-policy.toml` via `--admin-policy` so an admin-tier priority 5999 rule denies `write_file`, `replace`, `edit`, `edit_file`, and `delete_file` in reviewer mode while `--approval-mode yolo` continues to allow shell. This is an off-label reliance on gemini-cli honoring `--admin-policy` from arbitrary file paths, and the guarantee depends on gemini-cli keeping these write-tool names stable.
- On the missing-`jq` fail-closed path, `write_meta()` deliberately omits `CMD_JSON` instead of failing before `write_done()`. The collector treats missing `CMD_JSON` as invalid retry metadata, skips retry, and marks the result/tool unhealthy.
- Rejects empty `--output` values and paths containing bytes outside `[A-Za-z0-9._/-]` before stale-file cleanup or raw wrapper launch. The same byte string is used on disk, in `OUTPUT_FILE=`, and as a standalone argv element in `CMD_JSON` that collector retry substitution rewrites, so unsafe paths fail fast instead of being transformed.
- Output filenames must carry a `gemini-` prefix when consumed by `collect-agent-results.sh` unless `.meta` is guaranteed present.

## Policy contract

`scripts/gemini-reviewer-policy.toml` lives beside this launcher and is passed as an absolute path derived from `SCRIPT_DIR`. Its single `[[rule]]` denies the five known Gemini file-writing tool names at admin priority 5999, which overrides `--approval-mode yolo`'s default-allow posture while leaving read tools and shell available for live-repo review. The policy is intentionally reviewer-only; `scripts/launch-gemini-implement.sh` keeps yolo with write tools for the implementer slot.

The policy contract is narrower than a general sandbox. If gemini-cli removes arbitrary-path support for `--admin-policy`, the launcher should fail closed on Gemini argv parsing. If gemini-cli renames write tools or adds a new write-capable tool outside the deny list, the policy can silently stop covering that write surface until the deny list is updated.

## Prompt contract

Gemini runs with live repository access, matching the Cursor and Codex reviewer posture. Callers pass the same review prompt shape used for those reviewers: ask Gemini to run `git diff main...HEAD`, `git log main...HEAD --oneline`, and read changed files for context in diff mode, or read the description-mode scope file before inspecting files. Reviewer prompts must explicitly say: `Do NOT modify files. Do NOT commit. Do NOT push.`

## Test harness

`scripts/test-launch-gemini-review.sh` stubs `gemini` and exercises the real `run-external-agent.sh` path to cover timeout clamping, JSON normalization, fail-closed `.error`, `MISSING_JQ`, launcher-specific `--output` rejection before side effects, `CMD_JSON` sidecar emission, and `--timeout 0` rejection at argv-validation time.

## Edit-in-sync

Update `scripts/gemini-reviewer-policy.toml`, `scripts/run-external-agent.sh`, `scripts/lib-validate-meta-path.sh`, `scripts/collect-agent-results.sh`, `scripts/check-reviewers.sh`, `skills/review/SKILL.md`, `skills/implement/SKILL.md`, `docs/external-reviewers.md`, and `SECURITY.md` when changing Gemini CLI flags, output schema, or output-path invariants. Update `.claude-plugin/plugin.json` (`gemini_model` userConfig) and `docs/configuration-and-permissions.md` (`LARCH_GEMINI_MODEL` section) when changing the model-resolution precedence or default.
