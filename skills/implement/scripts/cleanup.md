# cleanup.sh

Thin Step 19 wrapper around `scripts/larch.sh session cleanup-tmpdir`.

Usage:

```bash
cleanup.sh --implement-tmpdir PATH
```

Output:

- `CLEANED=true|false`
- `ERROR=<message>` on failure
