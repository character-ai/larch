# Discussion Round 1 — scope boundaries & hard constraints

Context: issue #4972 is framed as "port `slack-issue-announce.sh` to a new `cli.py` verb,"
but that port already shipped in #3685. `slack issue-announce` already exists in
`python/pr_body.py` (stdlib `json` + `urllib`) and `python/closeout.py` Step 16a already
invokes `python/cli.py slack issue-announce --best-effort`. The real remaining work is to
finish #3685's half-done migration.

## Decision 1: Plan scope
- **Question**: The Python verb already exists and is wired in. How should the plan be scoped?
- **Resolution**: Finish the migration. In-scope: (a) verify parity of the existing
  `pr_body.py` function and refactor its test seam; (b) add colocated pytest; (c) delete the
  orphaned `slack-issue-announce.sh`, `slack-issue-announce.md`, `test-slack-issue-announce.sh`,
  `test-slack-issue-announce.md`; (d) remove `test-slack-issue-announce.sh` from
  `scripts/residual-bash-paths.txt`; (e) append deleted paths to `python/migrated-scripts.tsv`
  (`#4972`); (f) drop the `slack-issue-announce.md`/`.sh` row from the `skills/implement/SKILL.md`
  Extracted Script Registry; (g) run `make lint-retired-scripts` / `make lint` / `make py-test`.
  Out-of-scope: re-porting to a dedicated module, or bookkeeping-only with no tests.
- **Source**: user

## Decision 2: Test seam
- **Question**: The shipped function still uses the `__LARCH_FAKE_CURL` env seam (shells out to a
  fake curl binary for tests). The issue asks to replace it with an injectable transport.
- **Resolution**: Replace `__LARCH_FAKE_CURL` with a urllib monkeypatch transport. Drop the
  `__LARCH_FAKE_CURL` subprocess branch from `slack_issue_announce`; pytest monkeypatches
  `urllib.request.urlopen`. Collapses the function to a single real code path.
- **Source**: user

## Decision 3: Hard constraints (must not break)
- **Question**: What existing behavior must the plan preserve?
- **Resolution**: Preserve the `slack issue-announce` verb name and registry entry; keep
  `closeout.py` Step 16a working unchanged. Preserve the output grammar: `STATUS=posted|skipped|failed`,
  `REASON=webhook-not-set|issue-not-set` on skip, `ERROR=<msg>` on failure, and the `--best-effort`
  exit-0 path. Keep changes to the shipped function minimal beyond the seam refactor (the added
  webhook http/https scheme guard stays). Stdlib-only, Python ≥ 3.11.
- **Source**: codebase + user
