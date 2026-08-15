# skills/design/scripts/dedup-plan-lines.py

Post-apply plan-line dedup: whitespace-key collapse with section-aware Constraints protection.

## CLI

`python3 dedup-plan-lines.py <src> <dest>`

- Reads `<src>` (`plan.txt`), writes deduped output to `<dest>`.
- Prints the integer count of removed duplicate lines to stdout.

## Primary caller

The Rust plan-review post-apply pipeline through `scripts/larch.sh plan-review gate-b-dedup`.

## Invariants

- Byte-identical dedup semantics to the historical inline heredoc in `plan-review-loop.sh`.
- Duplicate-line collapse applies inside fenced blocks as well as outside.
- Constraints-section duplicate lines are protected only when outside fences.
- Heading and Constraints-section state use a two-pass balanced opener/closer fence model: only lines strictly between a matched fence pair are in-fence for that state; a failed closer leaves the stack unchanged (plain-text semantics).

## Fence-model divergence (intentional)

`parse-plan-commands.awk` uses a simple `bash` / `sh` fence toggle to extract command bodies for validation. This helper uses a two-pass balanced-pair model over any fenced region so headings inside matched fences do not change Constraints state, while still collapsing duplicate lines inside fences. The two are not unified because they serve different concerns.

## Harness

`crates/larch-cli/tests/plan_review_loop_commands.rs` (`make test-plan-review-loop`).
