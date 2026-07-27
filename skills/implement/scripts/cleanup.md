# cleanup.sh

Thin Step 19 wrapper around `python/cli.py session cleanup-tmpdir`.

Usage:

```bash
cleanup.sh --implement-tmpdir PATH
```

Output:

- `CLEANED=true|false`
- `ERROR=<message>` on failure
