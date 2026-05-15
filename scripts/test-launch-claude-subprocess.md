# test-launch-claude-subprocess.sh Contract

Regression harness for `scripts/launch-claude-subprocess.sh`.

It uses a stub `claude` binary on `PATH` to verify the read-only preamble reaches stdin, output promotion happens before `.done`, and `.meta` / `.dirty-tree` sidecars are written. It also pins symlink rejection for prompt files: the rejection must appear on caller stderr and must not be buried in the quiet log.

Run directly with `bash scripts/test-launch-claude-subprocess.sh` or through `make test-launch-claude-subprocess`.

Edit in sync with `scripts/launch-claude-subprocess.sh` whenever argv grammar, read-only prompt text, or sidecar names change.
