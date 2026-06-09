# cleanup.sh

Thin Step 18 wrapper around `python/cli.py session cleanup-tmpdir`.

Usage:

```bash
cleanup.sh --implement-tmpdir PATH
```

Output:

- `CLEANED=true|false`
- `ERROR=<message>` on failure
