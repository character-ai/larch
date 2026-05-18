# commit-implementation.sh

Thin Step 4 wrapper around `scripts/git-commit.sh`.

Usage:

```bash
commit-implementation.sh --message "Implement feature" [files...]
```

Output:

- `COMMITTED=true|false`
- `SHA=<head-sha-or-empty>`
- `ERROR=<message>` on failure
