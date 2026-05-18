# commit-review-fixes.sh

Thin Step 7 wrapper around `scripts/git-commit.sh`.

Usage:

```bash
commit-review-fixes.sh [--message "Address code review feedback"] [files...]
```

Output:

- `COMMITTED=true|false`
- `SHA=<head-sha-or-empty>`
- `ERROR=<message>` on failure
