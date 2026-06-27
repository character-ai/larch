---
paths: ["python/larch/agents/agents.py", "python/test_launch_review.py", "python/cli.py", "python/cli.py checks lint-fix", "agents/codex-implementer.md", "agents/cursor-implementer.md", "python/larch/agents/collect_results.py", "python/cli.py implement step2-dispatch", "docs/external-reviewers.md", "docs/configuration-and-permissions.md"]
---

# External-Tool Launcher Parity

Codex and Cursor share most launcher surfaces; changes in one
usually apply to the other. This rule covers shared argv grammar,
sanitization, startup-lock spawn guards, retry, health, and cross-doc
supported-tool lists.
Intentional asymmetries exist; classify each one instead of forcing symmetry
blindly.

When changing `python/cli.py agent launch-review`,
`python/cli.py agent run-negotiation-round`, `python/cli.py implement step2-dispatch`,
or `python/cli.py checks lint-fix`,
audit:

- **Argv validation** — `--timeout`, `--api-key`, `--model`, `--output`, `--prompt`, `--agent-file`; accepted in one launcher and rejected by another is a parity bug unless documented.
- **Startup-lock spawn site** — Darwin `external_startup_lock_acquire` / `external_startup_lock_release_after` coverage and relative ordering versus the actual Codex/Cursor spawn must stay aligned across the launcher family; dedicated harnesses pin the concrete lock behavior. Concrete behavior includes shared Codex/Cursor path parity across Python and Bash. Python uses `os.environ.get("USER") or "larch"` to match Bash `${USER:-larch}` for unset and empty `USER`. Bash acquire takes `<out_var> <tool>` while Python acquire returns a `StartupLockState`. Cross-lane contention is regression-tested in `python/test_agents.py`.
- **Sibling agent prompt** — `agents/codex-implementer.md` / `agents/cursor-implementer.md`; schema/wording changes usually apply to both.
- **Sibling `.md` contracts** — every launcher has `<basename>.md` (per `.claude/rules/script-md-siblings.md`); update both together.
- **Common collectors** — `python/cli.py agent run-external-agent` and `python/cli.py agent collect-results`; sanitization, retry, and `.meta` parser changes affect all lanes.
- **Health probe** — `python/cli.py agent check-reviewers`; healthy/unhealthy semantics must stay aligned.
- **Codex env-key auth** — `python/cli.py agent launch-review --tool codex`, `agent launch-codex-implement`, `launch-codex-ci.sh`, `agent check-reviewers`, `python/cli.py review-and-fix apply-findings`, `launch-codex-exec.sh`, `/research` Codex research and validation lanes, shared Codex voter/judge fences, `python/cli.py checks lint-fix`, and `agent run-negotiation-round` must share the same `OPENAI_API_KEY` contract: non-whitespace env-key mode, fixed `openai-larch-env` `-c` overrides containing only the variable name, copied temp-config stripping before launch, and login fallback only when the env key is unset/empty/whitespace-only.
- **Cross-doc surface** — `docs/external-reviewers.md`, `docs/configuration-and-permissions.md`, and SKILL.md prose enumerating supported tools must list both identically.
- **Write-sandbox grant (`--add-dir` vs `--workspace`)** — Codex uses `--add-dir "$SESSION_TMPDIR"` to grant write access to `codex-step2-out/` only (the dedicated output subdir). Cursor uses `--workspace "$PWD"` and has no equivalent `--add-dir` grant; this is intentional (different sandbox models). Do not add a symmetric `--add-dir` grant to the Cursor launcher.
- **Codex Step 2 grant hardening** — `agent launch-codex-implement` rejects symlink parents for manifest/qa/transcript paths and refuses `SESSION_TMPDIR` canonical-equal to `IMPLEMENT_TMPDIR` when the env var is set (defense against symlink widening and caller regressions). Mirror the symlink posture of `python/cli.py agent launch-review` the former extra Codex add-dir flag validation.

Missing any surface is a common OOS-issue generator after an external-tool
integration sweep.
