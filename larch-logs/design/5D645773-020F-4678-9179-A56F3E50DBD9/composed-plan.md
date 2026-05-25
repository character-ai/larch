## Plan

Surgical 4-section edit to `scripts/test-launch-review.sh`. Each edit prepends one line —

```
PATH="$STUB_BIN:$PATH" USER="larch-test-<section-key>-$$" \
```

— in front of the existing `"$LAUNCHER"` invocation, and re-indents the existing `"$LAUNCHER"` line by four spaces underneath the continuation. The PATH stub prevents the launcher from invoking the real `codex` / `cursor` CLI on dev Macs; the USER override gives each test a private serial-lock path so concurrent clones on the same Mac do not contend on the global `/tmp/larch-${tool}-serial-${USER}.lock`.

**Files to modify** (single file, four sections — identified by comment header; line numbers drift):

| # | Tool   | Flag                | Section comment header                                                          | Section key (USER suffix)    |
|---|--------|---------------------|---------------------------------------------------------------------------------|------------------------------|
| 1 | codex  | `--token-budget-cap`| `# --token-budget-cap accept path: flag recognized (not "unknown flag"), binary`| `budget-accept-codex`        |
| 2 | codex  | `--diff-file`       | `# --diff-file accept path: flag recognized (not "unknown flag").`              | `diff-file-accept-codex`     |
| 3 | cursor | `--token-budget-cap`| `# Accept path: flag recognized (not "unknown flag"), binary absence or other`  | `budget-accept-cursor`       |
| 4 | cursor | `--diff-file`       | `# --diff-file accept path: flag recognized (not "unknown flag").`              | `diff-file-accept-cursor`    |

**Edit shape** (no functional change; only the launcher invocation line):

```
set +e
PATH="$STUB_BIN:$PATH" USER="larch-test-<section-key>-$$" \
    "$LAUNCHER" --output "$TMPDIR/<artifact>.txt" --timeout 5 --prompt "x" \
    --<flag> <value> >/dev/null 2>"$TMPDIR/<artifact>.stderr"
set -e
```

`<section-key>` is one of the four keys in the table above. `<flag>`/`<artifact>` come from the existing line and are not changed.

**`STUB_BIN`**: defined twice in the file (codex section ~line 137, cursor section ~line 1144), both as `"$TMPDIR/bin"`. Each edit uses the in-scope `STUB_BIN` — no new definitions.

**Pattern parity**: the file already uses this `PATH="$STUB_BIN:$PATH"` + `USER="larch-test-*-$$"` shape at multiple sites — see line 313 (`CODEX_LOCK_USER`), lines 714–722 (cap-hit block), lines 1916–1924 (cursor `--diff-file` specialist block). The fix copies that established shape.

**Failure mode safeguards**:

- *Forgotten section*: every `"$LAUNCHER"` accept-path call must be preceded by a `PATH="$STUB_BIN:$PATH"` prefix line after the edit. Sweep with `grep -nE '^("\$LAUNCHER"|.*"\$LAUNCHER" )' scripts/test-launch-review.sh` and inspect each match.
- *Wrong `STUB_BIN` scope*: both definitions expand to `"$TMPDIR/bin"` so this is silently harmless; the in-scope reference is correct by construction.
- *`$$` collision*: PID space is large on macOS; effectively never collides in practice. No mitigation needed.

**Out of scope** (carried forward from the issue):

- Top-of-file global fake-binary `PATH` injection.
- Updating `.claude/rules/launcher-argv-test-coverage.md` to require this prefix on every accept-path assertion.
- Broader rule that every launcher-touching test uses a per-test `USER` override.

## Acceptance

1. `bash scripts/test-launch-review.sh` continues to pass on macOS **and** on CI Linux.
2. While `scripts/test-launch-review.sh` is running on macOS, `pgrep -f '/opt/homebrew/bin/codex|node /opt/homebrew/bin/codex'` returns no matches; same probe for cursor `pgrep -f '/Applications/Cursor.app|cursor-agent'` returns no matches.
3. While `scripts/test-launch-review.sh` is running on macOS, the global serial-lock paths `/tmp/larch-codex-serial-${USER}.lock` and `/tmp/larch-cursor-serial-${USER}.lock` (where `${USER}` is the OS user, e.g. the developer's login) do NOT exist at any moment. Only per-test variants matching `/tmp/larch-(codex|cursor)-serial-larch-test-*-[0-9]*.lock` may exist briefly.
4. Two concurrent invocations of `bash scripts/test-launch-review.sh` from two different clones of this repo on the same Mac do not block each other on lock acquisition — each completes in roughly the wall-clock of a single solo invocation.
5. With the fix in place, the four affected sections each shave roughly `--timeout 5` (~5 s) — total ~20 s — off the wall-clock of `scripts/test-launch-review.sh` on dev Macs that have brew-installed codex/cursor.
6. `bash scripts/relevant-checks.sh` passes.

diff_lines: 12
