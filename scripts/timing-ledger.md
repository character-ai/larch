# timing-ledger.sh

`scripts/timing-ledger.sh` writes session-scoped timing rows for `/implement`, nested `/design`, nested `/review`, and external vendor wrapper invocations. It mirrors `scripts/token-ledger.sh` operationally but uses a fixed 13-column TSV schema so shell-only renderers can parse it without `jq`.

Every row has the same tab-separated shape:

```text
v	type	ts_epoch	skill	step	vendor	task_kind	start_s	end_s	duration_s	output	exit_code	extra
```

`type` is `mark`, `vendor`, or `workflow`. `extra` is `-` for mark rows, `complete|signal|unknown` for vendor rows, and `HARD|SIMPLE` for workflow rows. Vendor rows store only `basename(output)`, never absolute output paths, so rendered timing reports do not expose workspace layout.

Subcommands:

- `mark <step-name>` writes a per-step mark for `${LARCH_TIMING_SKILL:-implement}`.
- `record-vendor-task --vendor codex|cursor|gemini --task-kind <kind> --start-s <epoch> --end-s <epoch> --output <path> [--exit-code <n>] [--status complete|signal|unknown]` writes one wrapper timing row. Negative durations are clamped to `0` and force `status=unknown`.
- `workflow-path HARD|SIMPLE` records the selected `/implement` workflow path. Reporters use the latest workflow row.
- `dump` prints the resolved ledger path on line 1, followed by the ledger contents when present.

Path resolution:

1. `--ledger PATH` test override, validated under `${TMPDIR:-/tmp}`.
2. `$LARCH_TIMING_LEDGER`, validated under one of `${TMPDIR:-/tmp}`, `$IMPLEMENT_TMPDIR`, `$DESIGN_TMPDIR`, `$REVIEW_TMPDIR`, or `dirname("$SESSION_ENV_PATH")`. Invalid env paths warn and fall through.
3. `$IMPLEMENT_TMPDIR/timing-ledger.tsv` when set and existing.
4. `dirname("$SESSION_ENV_PATH")/timing-ledger.tsv` when set and existing.
5. `$DESIGN_TMPDIR/timing-ledger.tsv` when set.
6. `$REVIEW_TMPDIR/timing-ledger.tsv` when set.
7. `${TMPDIR:-/tmp}/larch-timing-<sha256(cwd)>.tsv`.

Appends use `flock -w 5` when available. If `flock` is missing or lock acquisition fails, the script warns once per process and falls back to a plain append. The ledger is `chmod 600` after each successful append. All failures warn to stderr and exit 0 so observability never interrupts the workflow.

Task-kind validation sources `scripts/lib-timing-kinds.sh`. Unknown but syntactically valid kebab-case kinds are written with a warning to avoid data loss. Malformed kinds are rejected.

Known v1 limitation: direct `scripts/run-external-agent.sh` call sites do not emit vendor timing rows; only the six launch wrappers call `record-vendor-task`.
