# scripts/test-plan-block.sh contract

Regression harness for `scripts/plan-block-read.sh` and `scripts/plan-block-write.sh` using a `PATH`-prepended `gh` stub (`$BODY_FILE` fixture, `$EDIT_CAPTURE` for edited bodies).

## Wiring

```
bash scripts/test-plan-block.sh
```

`make test-plan-block` (shard `test-harnesses-15`).

## Edit-in-sync

Update when plan-block stdout contracts or marker rules change.
