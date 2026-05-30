# scripts/launch-claude-review.sh — contract

Launches a Claude read-only reviewer subprocess with the same output-file contract used by external reviewer launchers:

- writes reviewer text to `--output`
- writes `<output>.done` with the subprocess exit code
- writes Claude metadata via `launch-claude-subprocess.sh`

Input may be exactly one of `--agent-file`, `--prompt-file`, or `--prompt`. `--agent-file` prompts are rendered through `scripts/render-specialist-prompt.sh` and are supported only for `--role reviewer`; voter launches must use prompt-file or prompt-text so ballot-only prompts are passed through without re-rendering diff/plan/scope context.

The launcher accepts the same review context flags as `launch-review.sh` (`--mode`, `--diff-file`, `--commit-count`, `--plan-file`, `--feature-file`, `--scope-files`, `--description-text`) and forwards readable context files to the Claude subprocess.

`--context-files <path>` is a public repeatable single-value flag; each occurrence appends one operator-supplied context path. Explicit context paths hard-error with exit 2 when the value is missing, empty, non-existent, or unreadable, while implicit context flags still silently skip absent files because upstream phase callers may pass empty optional paths. The flag is role-orthogonal across `--role reviewer` and `--role voter`, deduplicates by canonical path against the implicit context flags and repeated explicit paths, and authorizes each forwarded context file's parent directory through `--allow-root`, matching implicit context behavior. `scripts/launch-claude-subprocess.sh` remains authoritative for symlink rejection, control-character and `..` rejection, the 1 MB per-file cap, and the 20-file global cap.

`--role reviewer|voter` (default `reviewer`) controls prompt rendering, not whether context is forwarded. Both roles receive any provided `DIFF_FILE`, `SCOPE_FILES`, `PLAN_FILE`, and `FEATURE_FILE` as subprocess context files so vote verification can stay grounded in the reviewed diff. `--agent-file` is still rejected for voters so `scripts/render-specialist-prompt.sh` cannot rewrite a ballot-only voter prompt into a reviewer-style specialist prompt.

`launch-claude-subprocess.sh`'s stderr is captured to a temp file and each line is re-emitted via this script's `larch_err`, so subprocess validation failures (`invalid --prompt-file`, `--prompt-file outside allowed roots`, `context file exceeds 1 MB`, etc.) propagate to the caller's stderr. Without this, the subprocess's own `larch_quiet_init` clobbers its inherited FD 4 with its own log file and the validation message is lost in a nested invocation (#2292).

**Timeout clamp:** when `--timeout` exceeds **1800**, this launcher clamps to **1800** and warns once (`launch-claude-subprocess.sh` rejects larger values with exit 2 before work starts).

**Failed-agent stderr tail:** agent failures write `${output}.stderr-tail` in `launch-claude-subprocess.sh` before `${output}.done`. When the subprocess exits non-zero and no sidecar exists yet, this launcher writes the tail from the captured subprocess stderr file (additive to the full stderr re-emit above).

Regression harness: `scripts/test-launch-claude-review.sh`.
