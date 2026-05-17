# scripts/launch-claude-review.sh — contract

Launches a Claude read-only reviewer subprocess with the same output-file contract used by external reviewer launchers:

- writes reviewer text to `--output`
- writes `<output>.done` with the subprocess exit code
- writes Claude metadata via `launch-claude-subprocess.sh`

Input may be exactly one of `--agent-file`, `--prompt-file`, or `--prompt`. `--agent-file` prompts are rendered through `scripts/render-specialist-prompt.sh`; prompt-file and prompt-text modes are used by voting dispatchers.

The launcher accepts the same review context flags as `launch-review.sh` (`--mode`, `--diff-file`, `--commit-count`, `--plan-file`, `--feature-file`, `--scope-files`, `--description-text`) and forwards readable context files to the Claude subprocess.

Regression harness: `scripts/test-launch-claude-review.sh`.
