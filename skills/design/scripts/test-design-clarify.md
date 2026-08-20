# test-design-clarify.sh

Offline harness for `design-clarify.sh`.

## Coverage

- Valid wrapper argv delegates to `scripts/larch.sh design clarify`.
- Delegation rebuilds `_delegate_args` with `--session-env-path`,
  `--claude-pid`, `--phase`, and `--issue` instead of forwarding consumed
  `"$@"`.
- Invalid `--phase`, `--issue`, and `--claude-pid` are rejected before
  delegation with exit 2.

Python phase behavior, result env trust boundaries, fetch failure tokens,
pause-save termination, publish redaction, and publish failure routing are
covered by `python/test_clarify.py`.

## Invocation

```bash
bash skills/design/scripts/test-design-clarify.sh
```

Wired through `make test-design-clarify`.
