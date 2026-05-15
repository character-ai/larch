# test-local-cleanup.sh contract

Regression harness for `scripts/local-cleanup.sh`. The primary contract lives in `scripts/local-cleanup.md`; this harness covers the pre-pull orphan cleanup path, the no-op path when local `main` has no ahead commits, and the safety path that preserves non-flush ahead work.

Run with:

```bash
scripts/test-local-cleanup.sh
```
