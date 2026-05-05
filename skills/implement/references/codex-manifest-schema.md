# Codex Implementer Manifest Schema

**Consumer**: `/implement` Step 2 — `skills/implement/scripts/step2-implement.sh` dispatcher (validation), `agents/codex-implementer.md` (production), and downstream Steps 4 / 8a / 9a / 9a.1 (consumption).

**Contract**: Single normative source for the JSON manifest Codex writes at `$IMPLEMENT_TMPDIR/manifest.json` after each implementation attempt. The dispatcher validates the manifest with `jq -e` per the rules below, then — on `status=complete` — uses `manifest.commit_message` to commit Codex's working-tree edits (`git add -A && git commit -F …`). Codex itself does NOT commit (it runs under `workspace-write` sandbox semantics that forbid `.git/` writes). Downstream SKILL.md steps consume only the validated, sanitized manifest — they never read Codex's transcript or run `git diff` to figure out what changed.

**Tool scope**: this schema applies to every external `--coder` (today: `codex`, `cursor`, and `gemini`). The filename retains the `codex-` prefix for historical reasons; the manifest contract itself is tool-neutral. `agents/cursor-implementer.md` and `agents/gemini-implementer.md` produce the same JSON shape and bail with the same enum, plus dispatcher-emitted `${TOOL_TAG}-modified-history` tokens for unsandboxed tools (`cursor-modified-history`, `gemini-modified-history`) that do not have Codex's `workspace-write` sandbox.

**When to load**: at Step 2 entry (via the MANDATORY directive at the top of Step 2 in SKILL.md) and whenever editing the dispatcher's validation logic, the Codex implementer prompt's manifest-writing instructions, or any of Steps 4 / 8a / 9a / 9a.1 manifest-consumption blocks.

---

## Schema

```json
{
  "schema_version": "1",
  "status": "complete|needs_qa|bailed",
  "files_touched": [
    {"path": "<repo-relative path>", "lines_added": <int>, "lines_removed": <int>}
  ],
  "tests_added_or_modified": ["<repo-relative path>", ...],
  "summary_bullets": ["<bullet 1>", "<bullet 2>", "<bullet 3>"],
  "commit_message": "<subject line>\n\n<optional body paragraphs>",
  "todos_left": ["<actionable todo>", ...],
  "oos_observations": [
    {"title": "<short title>", "description": "<full description>", "phase": "implement"}
  ],
  "bail_reason": "<token>",
  "needs_qa": {
    "questions": [{"id": "<stable id>", "text": "<full question text>"}, ...]
  }
}
```

## Required keys per status

| Field | `complete` | `needs_qa` | `bailed` |
|-------|------------|------------|----------|
| `schema_version` (string `"1"`) | required | required | required |
| `status` (enum) | required | required | required |
| `files_touched` (array of `{path, lines_added, lines_removed}`) | required, non-empty | optional | optional |
| `tests_added_or_modified` (array of strings) | required (may be empty) | optional | optional |
| `summary_bullets` (array of strings, length 1–5) | required | optional | optional |
| `commit_message` (string) | required, non-empty | optional | optional |
| `todos_left` (array of strings) | required (may be empty) | optional | optional |
| `oos_observations` (array of `{title, description, phase}`) | required (may be empty) | optional | optional |
| `bail_reason` (string) | absent or empty | absent or empty | required, non-empty |
| `needs_qa.questions` (non-empty array) | absent | required, non-empty | absent |

Optional fields MAY be present in the non-`complete` statuses but are not required and are not consumed by downstream SKILL.md steps.

## Validation rules (dispatcher applies via `jq -e`)

1. `schema_version == "1"`. Future schema bumps will add new accepted values.
2. `status` is one of the three enum literals above. No other value is accepted.
3. Per-status required keys per the table; the dispatcher rejects (`STATUS=bailed reason=manifest-schema-invalid`) any manifest that fails this check.
4. **Path normalization** (applied to every `path` in `files_touched` and every entry in `tests_added_or_modified`): the path MUST be repo-relative. Reject if it contains `..` or starts with `/`. NUL bytes are rejected implicitly: bash variables cannot hold a NUL, so the dispatcher's `read -r` over the jq output terminates the field at any NUL in upstream JSON, and the iterator never sees a path-with-NUL. Also reject any path equal to `.claude-plugin/plugin.json` (reserved for `/bump-version`) and any path equal to OR under a submodule root (per `git submodule status --recursive`). Symlink-aware containment (rejecting paths that resolve outside the repo via a symlink chain) is **not** mechanically enforced today — external implementers are trusted not to commit symlink-escape paths under the same trust model documented in `SECURITY.md`.
5. **Dispatcher commit** (status=`complete` only, after path normalization): the dispatcher pipes `manifest.commit_message` through `scripts/redact-secrets.sh` (so any secret accidentally embedded by Codex never lands in git history), writes the redacted output to a tmpfile, then runs `git add -A && git commit -F <tmpfile>` against the consumer repo. There is no diff cross-check, commit-subject cross-check, working-tree-clean check, or commits-since-baseline check — `commit_message` is consumed verbatim modulo the redactor. The same redactor is also applied to the canonical on-disk manifest below (validation rule 6 — "Sanitization"); applying it here in addition closes the split-brain risk where git history could otherwise be unredacted while `manifest.json` was redacted. `git add -A` stages every working-tree change (tracked + untracked) — under the new trust model the working tree IS the source of truth, `manifest.files_touched` is advisory documentation, and operator review / `/review` / pre-commit hooks are the downstream backstops. If `git commit` fails (empty working tree, pre-commit hook rejection, transient git error), the dispatcher removes the un-sanitized `manifest.json` (and its raw copy) from `$IMPLEMENT_TMPDIR`, captures `git commit` stderr to `$IMPLEMENT_TMPDIR/<tool>-commit-stderr.txt` (`<tool>` is `codex`, `cursor`, or `gemini`), leaves the staged index in place, and emits `STATUS=bailed reason=commit-failed`.
6. **Sanitization** (applied AFTER schema validation, BEFORE the canonical manifest is written to `$IMPLEMENT_TMPDIR/manifest.json`): `summary_bullets[*]`, `commit_message`, `oos_observations[*].title`, `oos_observations[*].description`, and `todos_left[*]` are piped through `scripts/redact-secrets.sh`, which redacts the secrets family (API keys, tokens, OAuth, JWT, passwords, certificates) → `<REDACTED-TOKEN>`. Internal hostnames/URLs and PII redaction are NOT mechanically applied by the dispatcher — external implementers are instructed to pre-redact those patterns before manifest emission, and downstream consumers (`/issue` outbound shell scrubber, `tracking-issue-write.sh`) provide a second-line backstop for the secrets family only. Operators handling internal-URL- or PII-rich content should review the manifest before allowing PR / issue / CHANGELOG publication. `bail_reason` is NOT piped through `redact-secrets.sh`; it is sanitized only for KV-grammar safety (whitespace and control characters collapsed; capped at ~200 chars) so the bail token cannot break the orchestrator's KV stdout parser. `needs_qa.questions[*].text` is NOT mechanically sanitized — the orchestrator surfaces questions verbatim via `AskUserQuestion`; external implementers are instructed to phrase questions without sensitive content.

## Atomic write rule

Codex MUST write `manifest.json` and `qa-pending.json` atomically: write to `<path>.tmp`, then `mv <path>.tmp <path>`. The dispatcher reads `manifest.json` only — never `manifest.json.tmp`. A crashed Codex that left only `manifest.json.tmp` looks identical to "no manifest written" and trips the `STATUS=bailed reason=manifest-missing` path.

## Bail-reason tokens

When `status=bailed`, `bail_reason` MUST be one of these stable tokens (downstream tooling pattern-matches on them):

- `resume-incompatible` — Codex inspected branch state on resume and could not reconcile prior partial work with the new operator answers. The branch is left as-is for operator inspection.
- `qa-loop-exceeded` — dispatcher's resume cap (5) tripped on the 6th invocation. Set by the dispatcher, not by Codex itself.
- `manifest-schema-invalid` — manifest failed JSON or schema validation, OR the resume counter file was corrupt (non-numeric content). Set by the dispatcher.
- `protected-path-modified` — Codex's working tree touched `.claude-plugin/plugin.json` or a submodule, or `manifest.files_touched` listed a forbidden path. Set by the dispatcher.
- `submodule-dirty` — `git submodule status --recursive` reported any non-clean entry. Set by the dispatcher.
- `branch-changed` — current branch differs from spawn-time branch. Set by the dispatcher.
- `commit-failed` — `status=complete` declared, but `git add -A && git commit -F …` failed (e.g., empty working tree, pre-commit hook rejection, transient git error). Set by the dispatcher. The `git add -A` runs before the failed `git commit`, so on bail the index is left staged; operators inspect `git status` and `$IMPLEMENT_TMPDIR/<tool>-commit-stderr.txt` (`<tool>` is `codex`, `cursor`, or `gemini`) before deciding whether to `git reset` or amend.
- `dirty-state-after-timeout` — Codex timed out and the dispatcher refused to retry because the working tree / index was dirty. Set by the dispatcher.
- `qa-pending-missing` — Codex emitted `status=needs_qa` but `qa-pending.json` is missing, empty, or its `questions` array is missing/empty. Set by the dispatcher.
- `redactor-not-executable` — `scripts/redact-secrets.sh` is missing or not executable; dispatcher fails closed rather than emit unsanitized text (covers both the pre-`git commit` redactor probe in Step 7b and the post-validation redactor probe in Step 8). Set by the dispatcher.
- `codex-runtime-failure` — launcher returned non-zero exit code or no manifest written, and the bounded retry also failed.
- `cursor-runtime-failure` — Cursor launcher returned non-zero exit code or no manifest written, and the bounded retry also failed.
- `cursor-bailed-no-reason` — Cursor-authored `status=bailed` manifest did not provide a usable `bail_reason`, so the dispatcher substituted the Cursor-specific fallback token.
- `cursor-modified-history` — Cursor moved `HEAD` before the dispatcher could commit on Cursor's behalf. Set by the dispatcher, not by Cursor itself.
- `gemini-runtime-failure` — Gemini launcher returned non-zero exit code or no manifest written, and the bounded retry also failed.
- `gemini-bailed-no-reason` — Gemini-authored `status=bailed` manifest did not provide a usable `bail_reason`, so the dispatcher substituted the Gemini-specific fallback token.
- `gemini-modified-history` — Gemini moved `HEAD` before the dispatcher could commit on Gemini's behalf. Set by the dispatcher, not by Gemini itself.
- `coder-mismatch-tmpdir-reuse` — the dispatcher's `step2-spawn-coder.txt` sentinel recorded a different `--coder` value on a prior invocation against the same `$IMPLEMENT_TMPDIR` (e.g., a partial `--coder=codex` run followed by `--coder=cursor` or `--coder=gemini` reusing the same tmpdir). The dispatcher fails closed before touching the shared baseline files or the per-tool resume counter. Set by the dispatcher.
- `manifest-missing` — manifest file is absent or empty after Codex returned. Set by the dispatcher (defense-in-depth on top of `codex-runtime-failure`'s `MANIFEST_WRITTEN=false` path).
- Free-form Codex-authored token — Codex MAY emit any string in `manifest.bail_reason`; the dispatcher preserves it verbatim in the canonical `manifest.json`. The orchestrator's `REASON=` stdout line is sanitized for KV-grammar safety only (whitespace and ASCII control characters collapsed to single spaces; capped at ~200 characters) so an adversarial or malformed bail token cannot break the orchestrator's stdout parser. Use this for genuine fatal errors Codex itself diagnoses (e.g., `unable-to-resolve-import-cycle`, `external-api-down`).

## Example: `complete` manifest

```json
{
  "schema_version": "1",
  "status": "complete",
  "files_touched": [
    {"path": "skills/foo/SKILL.md", "lines_added": 14, "lines_removed": 3},
    {"path": "scripts/foo-helper.sh", "lines_added": 42, "lines_removed": 0}
  ],
  "tests_added_or_modified": ["scripts/test-foo-helper.sh"],
  "summary_bullets": [
    "Add foo-helper.sh with deterministic stdout contract",
    "Wire helper into skills/foo/SKILL.md Step 3",
    "Cover helper with offline harness"
  ],
  "commit_message": "Add foo-helper.sh and wire it into /foo Step 3\n\nReplaces the inline awk block previously inlined in SKILL.md.",
  "todos_left": [],
  "oos_observations": [],
  "bail_reason": "",
  "needs_qa": {"questions": []}
}
```

## Example: `needs_qa` manifest

```json
{
  "schema_version": "1",
  "status": "needs_qa",
  "files_touched": [],
  "tests_added_or_modified": [],
  "summary_bullets": [],
  "commit_message": "",
  "todos_left": [],
  "oos_observations": [],
  "bail_reason": "",
  "needs_qa": {
    "questions": [
      {"id": "q1", "text": "Should the helper use jq -e or jq --exit-status (older jq versions)?"}
    ]
  }
}
```

The `qa-pending.json` companion file (also atomic-written) carries the same `questions` array in a flat shape:

```json
{"questions": [{"id": "q1", "text": "..."}]}
```

`qa-pending.json` is what the orchestrator reads to drive `AskUserQuestion`; the manifest's `needs_qa.questions` is informational redundancy for tooling that prefers a single file.

## Edit-in-sync

Any change to this schema MUST be paired with edits in:

- `skills/implement/scripts/step2-implement.sh` — dispatcher validation (`jq -e` filters).
- `agents/codex-implementer.md` — Codex prompt's manifest-writing instructions.
- `agents/cursor-implementer.md` — Cursor prompt's manifest-writing instructions.
- `agents/gemini-implementer.md` — Gemini prompt's manifest-writing instructions.
- `skills/implement/SKILL.md` — Step 4 (commit verification), Step 8a (CHANGELOG), Step 9a (PR `## Summary`), Step 9a.1 (OOS pipeline) consumption blocks.
- `skills/implement/scripts/test-step2-dispatch.sh` — golden manifest fixtures.
