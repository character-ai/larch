### FINDING_1: SESSION_ID not parsed in Step 0
- **Concern**: Step 0 only parses `SESSION_TMPDIR` and reviewer flags; plan's Step 5 used `--run-id "$SESSION_ID"` but the variable was never bound.
- **Resolution**: Add `SESSION_ID` to Step 0b parse list from `session-setup.sh` output; guard `design-log-publish.sh` call on `[ -n "${SESSION_ID:-}" ]`.

### FINDING_2: Current branch PR can merge unrelated commits
- **Concern**: `create-pr.sh` + `gh pr merge --squash --admin` on the current feature branch merges all branch commits, not just logs; `--delete-branch` removes the feature branch.
- **Resolution**: Use a git worktree on a dedicated `larch-log-design-$RUN_ID` branch forked from `origin/HEAD`; the original working tree branch is never touched; use `gh pr create --head larch-log-design-$RUN_ID` instead of `create-pr.sh`.

### FINDING_3: Sidecar trimming missing
- **Concern**: Copying all DESIGN_TMPDIR files without `.meta` `CMD_JSON` / `.result` sidecar trimming publishes raw internal envelopes.
- **Resolution**: Strip `CMD_JSON=...` from `.meta` files and remove top-level `.result` from `*-output*.json` sidecars before redaction; fail closed on trim errors.

### FINDING_4: $REPO undefined in /design
- **Concern**: `/design` uses `--skip-repo-check`, so `$REPO` is never derived; Step 5 helpers receive empty `--repo`.
- **Resolution**: Add `REPO=$(gh repo view --json nameWithOwner --jq '.nameWithOwner' 2>/dev/null || true)` in Step 5b before any helper calls.

### FINDING_5: Missing ${CLAUDE_PLUGIN_ROOT} prefix on script invocations
- **Concern**: `scripts/design-log-publish.sh` called without `${CLAUDE_PLUGIN_ROOT}/` prefix breaks in installed-plugin mode.
- **Resolution**: Use `"${CLAUDE_PLUGIN_ROOT}/scripts/design-log-publish.sh"` and `"${CLAUDE_PLUGIN_ROOT}/scripts/tracking-issue-write.sh"`.

### FINDING_7: tracking-issue-write.md and .sh header comments not in file list
- **Concern**: Adding `planned` without updating sibling contract and header comments leaves stale documentation.
- **Resolution**: Add `scripts/tracking-issue-write.md` to file list; update usage line, "Rename semantics" comment, and error text.

### FINDING_8: scripts/test-design-log-publish.md sibling stub missing
- **Concern**: `scripts/test-design-log-publish.sh` needs a sibling `.md` stub per `.claude/rules/script-md-siblings.md`.
- **Resolution**: Add `scripts/test-design-log-publish.md` to file list.

### FINDING_9: Clarify-loop success path skips [PLANNED] rename and log flush
- **Concern**: Clarify-loop exit path ran `plan-block-write.sh` and exited without rename/log flush.
- **Resolution**: Add the Step 5b rename + publish snippet to the clarify-loop success exit path in Step 0b.

### FINDING_10: find-lock-issue.sh has_managed_lifecycle_prefix doesn't include [PLANNED]
- **Concern**: [PLANNED] issues may remain /fix-issue-eligible contrary to other machine-owned prefixes.
- **Resolution**: Add `[PLANNED]` to `has_managed_lifecycle_prefix` in `skills/fix-issue/scripts/find-lock-issue.sh`; add harness coverage; add file to modify list.

### FINDING_11: Partial manifest.json schema diverges from larch-log.sh init
- **Concern**: Hand-written minimal manifest would advertise schema_version=2 but omit operator_cwd, larch_version, steps_ran, etc.
- **Resolution**: Use `larch-log.sh init` for manifest creation; do git commit separately (directly in script) to control the commit message with `[skip ci]`.

### FINDING_12: `print` is not a Bash 3.2 builtin in SKILL.md snippet
- **Concern**: `print "**⚠ ...**"` is zsh-only; in Bash 3.2 this is command-not-found.
- **Resolution**: Replace with `printf '%s\n' "**⚠ ...**"` in all SKILL.md bash snippets.

### FINDING_13: RUN_ID slug validation missing
- **Concern**: Malformed `--run-id` (e.g., `../x`) could write outside `larch-logs/design/`.
- **Resolution**: Call `larch_log_validate_slug run-id "$RUN_ID"` early in `design-log-publish.sh` before any path construction.
