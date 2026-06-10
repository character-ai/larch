# lib-untrusted-block.sh

Sourced-only helper library (no shebang) for literal-redacted untrusted
block emission in reviewer prompt renderers.

- **API**: `larch_untrusted_redact_stream` (redact-secrets + `<>&` HTML-entity
  escaping) and `larch_emit_untrusted_file_block` (emits the opening
  `encoding="literal-redacted"` tag, redacted/escaped body, and closing tag).
  Untrusted framing prose is caller-owned immediately before the block (or, for
  subprocess context blocks, immediately after the opening tag and before the
  body); see `python/cli.py render plan-review`.
- **Primary callers**: `scripts/launch-claude-subprocess.sh`,
  `python/cli.py render plan-review`,
  `skills/design/scripts/revise-plan-with-waterfall.sh`,
  `python/cli.py render voter`.
- **Invariants**: redaction runs before escaping; block content is data, not
  instructions (see `SECURITY.md` "Plan-review scope-anchor pipeline" —
  inline-renderer surface). Idempotent load guard
  (`LARCH_LIB_UNTRUSTED_BLOCK_LOADED`).
- **Harness**: covered indirectly through caller harnesses
  (`scripts/test-launch-claude-subprocess.sh`,
  `scripts/test-revise-plan-with-waterfall.sh`).
