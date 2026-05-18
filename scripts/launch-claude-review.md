# scripts/launch-claude-review.sh — contract

Launches a Claude read-only reviewer subprocess with the same output-file contract used by external reviewer launchers:

- writes reviewer text to `--output`
- writes `<output>.done` with the subprocess exit code
- writes Claude metadata via `launch-claude-subprocess.sh`

Input may be exactly one of `--agent-file`, `--prompt-file`, or `--prompt`. `--agent-file` prompts are rendered through `scripts/render-specialist-prompt.sh`; prompt-file and prompt-text modes are used by voting dispatchers.

The launcher accepts the same review context flags as `launch-review.sh` (`--mode`, `--diff-file`, `--commit-count`, `--plan-file`, `--feature-file`, `--scope-files`, `--description-text`) and forwards readable context files to the Claude subprocess.

`launch-claude-subprocess.sh`'s stderr is captured to a temp file and each line is re-emitted via this script's `larch_err`, so subprocess validation failures (`invalid --prompt-file`, `--prompt-file outside allowed roots`, `context file exceeds 1 MB`, etc.) propagate to the caller's stderr. Without this, the subprocess's own `larch_quiet_init` clobbers its inherited FD 4 with its own log file and the validation message is lost in a nested invocation (#2292).

Regression harness: `scripts/test-launch-claude-review.sh`.
